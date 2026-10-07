# NOTICE

This project distributes and builds upon code from several open-source
projects. Their licenses and notices are reproduced or referenced below.

## ps5-ultrapack (MIT)

Large parts of `engine/backend/` are vendored verbatim from
[ps5-ultrapack](https://github.com/knutwurst/ps5-ultrapack) by knutwurst
(MIT license, see `engine/LICENSE-ps5-ultrapack` and
`engine/NOTICES-ps5-ultrapack.md`). Its backend implements the conversion
chain used here: PS5 fake package decoding, PFS/`.ffpfs`/`.ffpfsc` image
building, exFAT image writing, executable fake-signing and backporting.
Vendored as of upstream `main` on 2026-10-07.

## LibProsperoPkg (GPL-3.0-or-later)

`engine/backend/native/src/ffpfsc-pkg-tool/` is a .NET 9 CLI tool by the
ps5-ultrapack project that links [LibProsperoPkg](https://github.com/SvenGDK/LibProsperoPKG)
1.2.0 (`lib/LibProsperoPkg.dll`, GPL-3.0-or-later), which performs the actual
PS5 package inspection, extraction and building. The tool is built from
source by `scripts/build-engine.ps1` and by the CI/release workflows.

## LibOrbisPkg (LGPL-3.0)

`engine/backend/native/src/LibOrbisPkg/` is vendored source of
[LibOrbisPkg](https://github.com/maxton/LibOrbisPkg) (LGPL-3.0), used by the
tool for PS4 package reading. See `engine/backend/native/LICENSE.LibOrbisPkg`.

## mkpfs

`engine/backend/mkpfs/` (from ps5-ultrapack, MIT) implements the PFS image
engine, exFAT writer and game metadata reading.

## Trademarks

"PlayStation" and "PS5" are trademarks of Sony Interactive Entertainment.
This project is not affiliated with or endorsed by Sony. Use it only with
content you are legally entitled to.
