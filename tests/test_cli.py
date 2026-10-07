"""Tests for the command line interface (no engine required)."""

import pytest

from app import __version__, cli


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_missing_input_is_a_usage_error():
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2


def test_missing_output_format_is_a_usage_error(tmp_path):
    pkg = tmp_path / "game.pkg"
    pkg.write_bytes(b"x")
    with pytest.raises(SystemExit) as exc:
        cli.main([str(pkg), "-o", str(tmp_path)])
    assert exc.value.code == 2


def test_nonexistent_input_fails_cleanly(tmp_path, capsys):
    code = cli.main([str(tmp_path / "nope.pkg"), "-o", str(tmp_path), "--to", "folder"])
    assert code == 1
    assert "not found" in capsys.readouterr().err


def test_missing_tool_fails_cleanly(tmp_path, capsys, monkeypatch):
    pkg = tmp_path / "game.pkg"
    pkg.write_bytes(b"x")
    monkeypatch.setattr(cli.engine, "locate_tool", lambda: None)
    code = cli.main([str(pkg), "-o", str(tmp_path), "--to", "folder"])
    assert code == 1
    assert "ffpkgsc-pkg-tool" in capsys.readouterr().err
