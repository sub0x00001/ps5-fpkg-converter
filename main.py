"""Executable entry point.

With no arguments it opens the GUI. ``convert ...`` behaves like the
``fpkg-convert`` CLI. The remaining routes serve the vendored engine, which
re-invokes the current executable as its Python interpreter:

* ``_engine ...`` / ``--internal-engine ...`` - the conversion chain bridge
* ``-m mkpfs ...`` / ``--mkpfs-internal ...`` - the PFS image builder

Without these routes a frozen build would fall through to the GUI for every
engine subprocess.
"""

import multiprocessing
import sys


def _run_mkpfs(args: list[str]) -> int:
    from app import engine

    backend = engine.engine_dir() / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    import runpy

    saved_argv = sys.argv
    sys.argv = ["mkpfs", *args]
    try:
        runpy.run_module("mkpfs", run_name="__main__", alter_sys=False)
        return 0
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else 1)
    finally:
        sys.argv = saved_argv


def main() -> int:
    # PyInstaller on Windows: multiprocessing workers re-run the executable;
    # freeze_support detects that and services the worker instead of the GUI.
    multiprocessing.freeze_support()

    argv = sys.argv[1:]
    if argv and argv[0] == "convert":
        from app.cli import main as cli_main

        return cli_main(argv[1:])
    if argv and argv[0] in ("--internal-engine", "_engine"):
        # Pass the marker through: app.cli strips it and runs the bridge.
        from app.cli import main as cli_main

        return cli_main(argv)
    if argv and argv[0] == "-m" and len(argv) > 1 and argv[1] == "mkpfs":
        return _run_mkpfs(argv[2:])
    if argv and argv[0] == "--mkpfs-internal":
        return _run_mkpfs(argv[1:])
    from app.ui import main as ui_main

    return ui_main()


if __name__ == "__main__":
    raise SystemExit(main())
