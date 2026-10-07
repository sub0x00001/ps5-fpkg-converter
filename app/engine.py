"""Locate and drive the vendored conversion engine (ps5-ultrapack backend).

The heavy lifting (PS5 package decoding, PFS image building) is done by two
parts vendored under ``engine/``:

* ``engine/backend`` - the pure-Python backend of knutwurst/ps5-ultrapack.
* ``ffpfsc-pkg-tool`` - a self-contained .NET 9 CLI (LibProsperoPkg) that the
  backend shells out to for PS5 package work. The wrapper builds it from
  ``engine/backend/native/src`` (see scripts/build-engine.ps1).

This module hides both behind :func:`run_conversion`, which spawns the backend
chain as a subprocess of the current interpreter (or of the frozen executable)
and streams its progress lines back to the caller.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Iterable, Optional

#: Progress lines look like ``[#####-----]  42% extract the .pkg ...``.
PROGRESS_RE = re.compile(r"^\[#+-*\]\s*(\d+)%\s*(.*)$")

#: Output formats supported by the conversion chain.
OUTPUT_FORMATS = ("folder", "ffpfs", "ffpfsc")

LineCallback = Callable[[str], None]

TOOL_NAME = "ffpfsc-pkg-tool"

# The one conversion job allowed at a time, so the UI can stop it.
_ACTIVE_LOCK = threading.Lock()
_ACTIVE_PROC: Optional[subprocess.Popen] = None


def stop_running_job() -> bool:
    """Terminate the active conversion subprocess tree. True if one existed."""
    global _ACTIVE_PROC
    with _ACTIVE_LOCK:
        proc = _ACTIVE_PROC
        _ACTIVE_PROC = None
    if proc is None:
        return False
    if proc.poll() is not None:
        return False
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    else:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return True


def repo_root() -> Path:
    """Directory that contains ``app/`` and ``engine/``."""
    if getattr(sys, "frozen", False):  # PyInstaller onefile
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def engine_dir() -> Path:
    return repo_root() / "engine"


def tool_candidates() -> Iterable[Path]:
    """Search order for the ffpkgsc-pkg-tool executable."""
    env = os.environ.get("FFPFSC_PKG_TOOL")
    if env:
        yield Path(env)
    yield Path(sys.executable).parent / f"{TOOL_NAME}.exe"
    yield repo_root() / f"{TOOL_NAME}.exe"
    yield engine_dir() / "bin" / f"{TOOL_NAME}.exe"
    yield engine_dir() / "backend" / "native" / "src" / TOOL_NAME / "out" / f"{TOOL_NAME}.exe"
    yield engine_dir() / "backend" / "native" / TOOL_NAME


def locate_tool() -> Optional[Path]:
    """Return the first existing ffpkgsc-pkg-tool executable, or None."""
    for candidate in tool_candidates():
        if candidate.is_file():
            return candidate
    return None


def build_command(chain_args: list[str]) -> list[str]:
    """Command that re-enters this program in internal-engine mode."""
    if getattr(sys, "frozen", False):
        # Bare word: the PyInstaller bootloader mangles leading-'--' markers.
        return [sys.executable, "_engine", *chain_args]
    return [sys.executable, "-m", "app.cli", "--internal-engine", *chain_args]


def chain_arguments(
    input_path: str | Path,
    output_dir: str | Path,
    output_format: str,
    *,
    sign: bool = False,
    overwrite: bool = False,
    passcode: Optional[str] = None,
    temp_dir: Optional[str | Path] = None,
) -> list[str]:
    """Translate wrapper options into the backend chain argument list."""
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"unsupported output format: {output_format!r}")
    args = [str(input_path), str(output_dir), "--to", output_format]
    if sign:
        args.append("--sign")
    if overwrite:
        args.append("--overwrite")
    if passcode:
        args += ["--fpkg-passcode", passcode]
    if temp_dir:
        args += ["--temp-dir", str(temp_dir)]
    return args


def _unique_target(path: Path) -> Path:
    """Return a free path like ``name (1).ext``, ``name (2).ext``, ... if taken."""
    if not path.exists():
        return path
    for n in range(1, 1000):
        candidate = path.parent / f"{path.stem} ({n}){path.suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not find a free name for {path}")


def _replace(target: Path) -> None:
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    elif target.exists():
        target.unlink()


def run_conversion(
    input_path: str | Path,
    output_dir: str | Path,
    output_format: str,
    *,
    sign: bool = False,
    overwrite: bool = False,
    passcode: Optional[str] = None,
    temp_dir: Optional[str | Path] = None,
    on_line: Optional[LineCallback] = None,
) -> int:
    """Run one conversion job; return the backend exit code (0 = success).

    The engine writes into a staging folder inside the destination and the
    result is then moved into place: renamed with a copy number (``name
    (1).ext``) when the target exists, or replaced when ``overwrite`` is set.
    This keeps the engine from ever prompting (and stalling) about an
    existing output. ``on_line`` receives every backend output line.
    """
    tool = locate_tool()
    if tool is None:
        raise RuntimeError(
            f"{TOOL_NAME} executable not found. Build it with "
            "scripts/build-engine.ps1 (requires the .NET 9 SDK) or set the "
            "FFPFSC_PKG_TOOL environment variable."
        )

    final_dir = Path(output_dir)
    final_dir.mkdir(parents=True, exist_ok=True)
    staging = final_dir / f".fpkgc-staging-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    # The engine writes "<stem>_extracted" INTO an existing output dir but
    # REPLACES a non-existing one, so staging must exist before it starts.
    staging.mkdir(parents=True, exist_ok=True)

    argv = chain_arguments(
        input_path,
        staging,
        output_format,
        sign=sign,
        overwrite=True,  # staging is ours; collisions are handled on move
        passcode=passcode,
        temp_dir=temp_dir,
    )

    env = dict(os.environ, FFPFSC_PKG_TOOL=str(tool))
    # The backend prints Unicode (arrows, sizes); force UTF-8 so a cp1252
    # console cannot crash the child mid-conversion.
    env["PYTHONUTF8"] = "1"
    if not getattr(sys, "frozen", False):
        # The child resolves `python -m app.cli` from the repo root.
        env["PYTHONPATH"] = os.pathsep.join(
            p for p in (str(repo_root()), env.get("PYTHONPATH", "")) if p
        )
    proc = subprocess.Popen(
        build_command(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,  # the engine must never wait on a prompt
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    global _ACTIVE_PROC
    with _ACTIVE_LOCK:
        _ACTIVE_PROC = proc
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            if on_line is not None:
                on_line(line)
        proc.stdout.close()
        code = proc.wait()
        if code == 0:
            for item in sorted(staging.iterdir()) if staging.is_dir() else []:
                target = final_dir / item.name
                if overwrite:
                    _replace(target)
                    item.rename(target)
                else:
                    item.rename(_unique_target(target))
        return code
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        with _ACTIVE_LOCK:
            if _ACTIVE_PROC is proc:
                _ACTIVE_PROC = None


def parse_progress(line: str) -> Optional[tuple[int, str]]:
    """Return ``(percent, message)`` for a progress line, else None."""
    match = PROGRESS_RE.match(line)
    if not match:
        return None
    return int(match.group(1)), match.group(2).strip()
