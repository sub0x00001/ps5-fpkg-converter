"""Command line interface for PS5 FPKG Converter.

Normal mode converts a PS5 fake package (.pkg) into a launchable format
(folder, .ffpfs or .ffpfsc) using the vendored ps5-ultrapack engine.

The hidden ``--internal-engine`` mode is what the GUI and the frozen
executable use to run the backend chain in a child process: it imports the
vendored backend, points it at ffpkgsc-pkg-tool and hands over argv.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from . import engine


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fpkg-convert",
        description=(
            "Convert a PS5 fake package (.pkg) into a format that runs on "
            "jailbroken consoles via folder/ShadowMount-style loading."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "input",
        nargs="?",
        help="input PS5 fake package (.pkg)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=".",
        help="output directory (default: current directory)",
    )
    parser.add_argument(
        "--to",
        dest="output_format",
        choices=engine.OUTPUT_FORMATS,
        required=False,
        help="output format",
    )
    parser.add_argument("--sign", action="store_true", help="fake-sign eboot/prx/sprx during conversion")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing output")
    parser.add_argument("--fpkg-passcode", default=None, help="package passcode (32 hex chars; fake packages use zeros)")
    parser.add_argument("--temp-dir", default=None, help="scratch directory for the engine")
    return parser


def _run_engine_bridge(argv: Sequence[str]) -> int:
    """Run the vendored backend chain in-process (hidden internal-engine mode)."""
    backend_dir = engine.engine_dir() / "backend"
    backend_cli = backend_dir / "cli.py"
    if not backend_cli.is_file():
        print(f"[ERROR] engine backend not found: {backend_cli}", file=sys.stderr)
        return 1

    # The backend is shipped as data (not frozen imports): its own sibling
    # modules (backport, mkpfs, ...) resolve through the backend directory.
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    spec = importlib.util.spec_from_file_location("ultrapack_backend_cli", backend_cli)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    saved_argv = sys.argv
    sys.argv = ["ultrapack-backend-cli", *argv]
    try:
        module.main()
        return 0
    except SystemExit as exc:  # the backend exits via sys.exit on failure
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else 1)
    finally:
        sys.argv = saved_argv


def main(argv: Optional[Sequence[str]] = None) -> int:
    # Engine output contains Unicode; never die on a cp1252 console.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] in ("--internal-engine", "_engine"):
        return _run_engine_bridge(args[1:])

    parser = _build_parser()
    opts = parser.parse_args(args)

    if not opts.input:
        parser.error("an input package is required")
    if not opts.output_format:
        parser.error("--to is required (folder, ffpfs or ffpfsc)")

    input_path = Path(opts.input)
    if not input_path.is_file():
        print(f"[ERROR] input file not found: {input_path}", file=sys.stderr)
        return 1
    if input_path.suffix.lower() != ".pkg":
        print("[WARN] input does not end in .pkg; trying anyway", file=sys.stderr)

    output_dir = Path(opts.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    tool = engine.locate_tool()
    if tool is None:
        print(
            "[ERROR] ffpkgsc-pkg-tool executable not found. "
            "Build it with scripts/build-engine.ps1 (requires the .NET 9 SDK) "
            "or set FFPFSC_PKG_TOOL.",
            file=sys.stderr,
        )
        return 1
    print(f"[INFO] engine tool: {tool}")

    def show(line: str) -> None:
        print(line, flush=True)
        progress = engine.parse_progress(line)
        if progress:
            percent, message = progress
            print(f"[PROGRESS {percent}%] {message}", flush=True)

    return engine.run_conversion(
        input_path,
        output_dir,
        opts.output_format,
        sign=opts.sign,
        overwrite=opts.overwrite,
        passcode=opts.fpkg_passcode,
        temp_dir=opts.temp_dir,
        on_line=show,
    )


if __name__ == "__main__":
    sys.exit(main())
