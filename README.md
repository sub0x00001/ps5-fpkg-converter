# PS5 FPKG Converter

Convert **PS5 fake packages (`.pkg` / FPKG)** into formats that actually run on
jailbroken consoles: **folder dumps**, **`.ffpfs`** images and **`.ffpfsc`**
compressed images — the formats mounted by ShadowMount-style loaders.

On firmwares where FPKG installation is not supported (the FPKG-enabler kernel
patches are not ported yet, e.g. 12.xx–13.60), a fake package installs but
fails to launch with an error. Converting the same package to a folder dump or
a `.ffpfsc` container sidesteps that entirely: the game mounts as regular
content and runs.

Built as a thin Windows-first wrapper (CLI + GUI) around the proven engine of
[ps5-ultrapack](https://github.com/knutwurst/ps5-ultrapack) — all credit for
the heavy lifting goes to that project and to
[LibProsperoPkg](https://github.com/SvenGDK/LibProsperoPKG). See
[NOTICE.md](NOTICE.md).

## Features

- **FPKG → folder dump** (`<game>-app` folder with `eboot.bin`, `sce_sys`, ...),
  ready to drop into `/data/homebrew` on the console.
- **FPKG → `.ffpfs`** (uncompressed image, fastest to mount) and
  **FPKG → `.ffpfsc`** (compressed container).
- Optional **fake-signing** of executables and **overwrite** of existing
  output.
- Streaming progress with speed and ETA (a ~8.5 GB package extracts at
  ~350 MB/s on NVMe — measured on the reference machine).
- **CLI** (`fpkg-convert`) and **portable GUI** (input file, output format,
  output path, Start / Stop / Close, progress bar and log).
- No Python dependencies at runtime (stdlib only); the portable zip bundles
  everything.

## Supported conversions

| Input | Output |
| --- | --- |
| PS5 fake package (`.pkg`) | folder dump, `.ffpfs`, `.ffpfsc` |

The underlying engine also converts between folders, `.ffpfs`, `.ffpfsc`,
`.exfat` and `.pkg` in other directions; this tool focuses on the
FPKG-input path.

## Getting started (portable zip)

1. Download `PS5-FPKG-Converter-vX.Y.Z-portable-win64.zip` from
   [Releases](../../releases) and extract it anywhere.
2. Run `PS5-FPKG-Converter.exe`.
3. Pick the input `.pkg`, the output directory and the format, then
   **Start**.

The zip contains both `PS5-FPKG-Converter.exe` and `ffpfsc-pkg-tool.exe` —
keep them in the same folder.

## CLI usage

```
fpkg-convert INPUT.pkg -o OUTPUT_DIR --to {folder,ffpfs,ffpfsc} [options]
```

Options:

| Flag | Description |
| --- | --- |
| `-o, --output DIR` | Output directory (default: current directory) |
| `--to {folder,ffpfs,ffpfsc}` | Output format (required) |
| `--sign` | Fake-sign `eboot.bin` / `.prx` / `.sprx` during conversion |
| `--overwrite` | Replace an existing output |
| `--fpkg-passcode CODE` | Package passcode (fake packages use 32 zeros) |
| `--temp-dir DIR` | Scratch directory used by the engine |
| `--version` | Print the version |

Example:

```
fpkg-convert "Some Game (PSA00001).pkg" -o D:\dumps --to folder --sign
```

## Running from source

Requirements: Python 3.9+ and the .NET SDK 9 (only to build the engine tool).

```
git clone <this repo>
cd ps5-fpkg-converter
powershell scripts/build-engine.ps1   # builds engine\bin\ffpfsc-pkg-tool.exe
pip install -e .[dev]
pytest                                # unit tests
fpkg-convert --version                # CLI smoke test
fpkg-convert-ui                       # GUI
```

## Deploying to the console

- **Folder dump**: copy the resulting `<TitleID>-app` folder to
  `/data/homebrew/` on the console (any FTP/web file manager works).
- **`.ffpfsc` / `.ffpfs`**: copy the container wherever your ShadowMount
  loader expects images.

## How it works

A PS5 fake package stores the whole `/app0` tree as a block-coded inner PFS
image plus `sce_sys` metadata, without real encryption (debug-style package,
passcode of zeros). The engine decodes the container block by block and
rewrites the game as plain files (folder) or repacks it into a PFS image with
the 64 KiB block size the console requires. See the
[ps5-ultrapack README](https://github.com/knutwurst/ps5-ultrapack) for the
format details and known console quirks.

## Credits

- **[knutwurst/ps5-ultrapack](https://github.com/knutwurst/ps5-ultrapack)** —
  the conversion engine (MIT). This project vendors its Python backend and
  builds its `ffpfsc-pkg-tool`.
- **[SvenGDK/LibProsperoPKG](https://github.com/SvenGDK/LibProsperoPKG)** —
  PS5 PKG/PFS library (GPL-3) powering the tool.
- **[maxton/LibOrbisPkg](https://github.com/maxton/LibOrbisPkg)** — PS4
  package reading (LGPL-3), vendored by the tool.
- Everyone in the PS5 scene documenting fake packages, PFS and ShadowMount.

## License

[GPL-3.0-or-later](LICENSE). The distributed binaries combine GPL and LGPL
components; see [NOTICE.md](NOTICE.md) for the full attribution.
