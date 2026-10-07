"""Tests for the engine wrapper (no real conversion needed)."""

import sys
from pathlib import Path

import pytest

from app import engine


def test_parse_progress_full_line():
    line = "[#######-------------------------]  22% extract the .pkg on the system drive (5.7 of 25.1 GB written) @ 343.34 MB/s ETA 58s"
    result = engine.parse_progress(line)
    assert result == (
        22,
        "extract the .pkg on the system drive (5.7 of 25.1 GB written) @ 343.34 MB/s ETA 58s",
    )


def test_parse_progress_100():
    result = engine.parse_progress("[################################] 100% writing files")
    assert result == (100, "writing files")


def test_parse_progress_ignores_other_lines():
    assert engine.parse_progress("[OK] extracted 5533 file(s)") is None
    assert engine.parse_progress("[INFO] CHAIN: game.pkg (pkg) -> folder") is None
    assert engine.parse_progress("random text 42%") is None


def test_chain_arguments_folder(tmp_path):
    args = engine.chain_arguments(tmp_path / "in.pkg", tmp_path / "out", "folder")
    assert args[:4] == [str(tmp_path / "in.pkg"), str(tmp_path / "out"), "--to", "folder"]


def test_chain_arguments_all_options(tmp_path):
    args = engine.chain_arguments(
        tmp_path / "in.pkg",
        tmp_path / "out",
        "ffpfsc",
        sign=True,
        overwrite=True,
        passcode="0" * 32,
        temp_dir=tmp_path,
    )
    assert "--to ffpfsc".split() == args[2:4]
    assert "--sign" in args
    assert "--overwrite" in args
    assert args[args.index("--fpkg-passcode") + 1] == "0" * 32
    assert args[args.index("--temp-dir") + 1] == str(tmp_path)


def test_chain_arguments_rejects_bad_format(tmp_path):
    with pytest.raises(ValueError):
        engine.chain_arguments(tmp_path / "in.pkg", tmp_path, "exfat")


def test_locate_tool_env_override(tmp_path, monkeypatch):
    fake = tmp_path / "ffpfsc-pkg-tool.exe"
    fake.write_bytes(b"MZ")
    monkeypatch.setenv("FFPFSC_PKG_TOOL", str(fake))
    assert engine.locate_tool() == fake


def test_locate_tool_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("FFPFSC_PKG_TOOL", "")
    monkeypatch.setattr(engine, "tool_candidates", lambda: iter([]))
    assert engine.locate_tool() is None


def test_build_command_dev(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    cmd = engine.build_command(["a.pkg", "out", "--to", "folder"])
    assert cmd[1:4] == ["-m", "app.cli", "--internal-engine"]
    assert cmd[4:] == ["a.pkg", "out", "--to", "folder"]


def test_output_formats_are_stable():
    assert engine.OUTPUT_FORMATS == ("folder", "ffpfs", "ffpfsc")
