# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
