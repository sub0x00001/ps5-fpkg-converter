# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.2] - 2026-10-07

### Fixed

- Portable executable crashed on launch (`attempted relative import with no
  known parent package`): PyInstaller was pointed at `app/ui.py`, whose
  package-relative imports cannot resolve as an entry script. A dual-mode
  `main.py` entry point now opens the GUI with no arguments and routes
  `convert` to the CLI.
- Frozen builds re-executed themselves as GUI windows whenever the engine
  spawned Python subprocesses (`.ffpfs` / `.ffpfsc` builds, multiprocessing
  workers): the engine's `-m mkpfs` / `--mkpfs-internal` invocations and
  `multiprocessing.freeze_support()` are now handled by the entry point.
- `.ffpfs` / `.ffpfsc` conversions produced no output: the engine's `cryptography`
  dependency and a set of standard-library modules were missing from the
  bundle. Hidden imports are now generated from the vendored sources by
  `scripts/gen-hidden-imports.py`.
- Converting into a folder that already held the output stalled forever on the
  engine's interactive overwrite prompt. Conversions now run in a staging
  folder and the result is moved into place: replaced when `--overwrite` is
  set, otherwise renamed with a copy number (`name (1).ext`), like a browser
  download. The engine subprocess also runs with a closed stdin so no prompt
  can ever block it.
- Engine child processes inherit `PYTHONUTF8=1` and the CLI reconfigures its
  streams to UTF-8, so conversions no longer die with `UnicodeEncodeError` on
  cp1252 consoles.

### Added

- The portable executable now exposes the CLI: `PS5-FPKG-Converter.exe
  convert INPUT -o OUTPUT --to {folder,ffpfs,ffpfsc}`.
- GUI: "Open destination folder when finished" checkbox (disabled while a
  conversion runs), empty output-directory field by default, and the progress
  bar and log reset when a new input is selected or a new run starts.

## [0.0.1] - 2026-10-07

### Added

- CLI (`fpkg-convert`) that converts a PS5 fake package into a folder dump,
  a `.ffpfs` image or a `.ffpfsc` compressed image.
- Tkinter GUI with input/format/output selection, Start, Stop and Close
  controls, progress bar and scrolling log.
- Vendored conversion engine from [ps5-ultrapack](https://github.com/knutwurst/ps5-ultrapack)
  (Python backend) plus a build script for its `ffpfsc-pkg-tool` .NET binary.
- Unit tests and an end-to-end test that builds a fixture fake package and
  converts it back to a folder dump.
- CI workflow (build, tests, smoke) and release workflow that publishes a
  portable Windows zip on version tags.

[0.0.1]: https://github.com/sub0x00001/ps5-fpkg-converter/releases/tag/v0.0.1
