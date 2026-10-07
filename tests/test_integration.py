"""End-to-end integration test: build a tiny fake package, convert it back.

Requires the engine tool (engine/bin/ffpfsc-pkg-tool.exe) and only runs when
FPKGC_INTEGRATION=1 is set, because building the fixture takes a few seconds
and needs the .NET tool that scripts/build-engine.ps1 produces.

In CI (ci.yml / release.yml) the tool is always built, so the variable can be
set there to keep the full pipeline covered on every push.
"""

import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from app import cli, engine

REPO = Path(__file__).resolve().parent.parent


def _png_1px(path: Path) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00\xff")
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    )


def _minimal_elf(path: Path) -> None:
    # ELF64 x86-64, ET_EXEC, one PT_LOAD header right after the ELF header:
    # the minimum the packager accepts to fake-sign an eboot.
    header = bytearray(64)
    header[0:4] = b"\x7fELF"
    header[4] = 2  # 64-bit
    header[5] = 1  # little endian
    header[6] = 1  # version
    header[7] = 0x5A  # OSABI: FreeBSD 9, the one PS tools expect
    struct.pack_into("<HHI", header, 16, 2, 0x3E, 1)  # ET_EXEC, x86-64, v1
    struct.pack_into("<QQQ", header, 24, 0x400000, 64, 0)  # entry, phoff=0x40, shoff=0
    struct.pack_into("<I", header, 48, 0)  # flags
    struct.pack_into("<HHHHHH", header, 52, 64, 56, 1, 0, 0, 0)  # ehsize, phentsize, phnum, shentsize, shnum, shstrndx
    phdr = struct.pack("<IIQQQQQQ", 1, 5, 0, 0x400000, 0x400000, 120, 120, 0x1000)
    path.write_bytes(bytes(header) + phdr)


def _fixture_game(root: Path) -> Path:
    game = root / "FixtureApp"
    sce_sys = game / "sce_sys"
    sce_sys.mkdir(parents=True)
    (sce_sys / "param.json").write_text(
        json.dumps(
            {
                "contentId": "EP0001-PPSA00001_00-FIXTUREAPP000000",
                "contentVersion": "01.000.000",
                "masterVersion": "01.00",
                "titleId": "PPSA00001",
                "applicationDrmType": "upgradable",
                "localizedParameters": {"defaultLanguage": "en-US", "en-US": {"titleName": "Fixture App"}},
                "requiredSystemSoftwareVersion": "0x0250000000000000",
                "sdkVersion": "0x0200000000000000",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _png_1px(sce_sys / "icon0.png")
    _minimal_elf(game / "eboot.bin")
    (game / "data.txt").write_text("fixture payload\n", encoding="utf-8")
    return game


def _backend() -> Path:
    return REPO / "engine" / "backend" / "cli.py"


@pytest.fixture()
def integration_enabled() -> None:
    import os

    if os.environ.get("FPKGC_INTEGRATION") != "1":
        pytest.skip("set FPKGC_INTEGRATION=1 to run the end-to-end test")
    if engine.locate_tool() is None:
        pytest.skip("engine tool not built (run scripts/build-engine.ps1)")


def test_build_pkg_then_convert_to_folder(tmp_path, integration_enabled, monkeypatch, capsys):
    game = _fixture_game(tmp_path)
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()

    # Step 1: fixture folder -> fake package (engine chain, pkg output).
    build = subprocess.run(
        [sys.executable, str(_backend()), str(game), str(pkg_dir), "--to", "pkg"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env={**__import__("os").environ, "FFPFSC_PKG_TOOL": str(engine.locate_tool())},
    )
    assert build.returncode == 0, build.stdout + build.stderr
    built = sorted(pkg_dir.glob("*.pkg"))
    assert built, f"no package produced: {build.stdout}"
    fixture_pkg = built[0]

    # Step 2: our CLI converts the fake package back to a folder dump.
    out_dir = tmp_path / "converted"
    out_dir.mkdir()
    code = cli.main([str(fixture_pkg), "-o", str(out_dir), "--to", "folder", "--overwrite"])
    assert code == 0, capsys.readouterr().out
    dump = out_dir / f"{fixture_pkg.stem}_extracted"
    assert (dump / "eboot.bin").is_file()
    assert (dump / "sce_sys" / "param.json").is_file()
