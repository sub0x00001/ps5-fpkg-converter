# Rebuilds the portable executable the same way the release workflow does.
# Engine dependencies (stdlib set + cryptography, psutil and the optional
# zlib-ng/isal accelerators) are discovered by scripts/gen-hidden-imports.py.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$py = 'C:\Users\Tiago\AppData\Local\Programs\Python\Python312\python.exe'

$flags = @()
foreach ($m in (& $py scripts\gen-hidden-imports.py)) {
    $flags += @('--hidden-import', $m)
}

& $py -m PyInstaller --onefile --console --name PS5-FPKG-Converter `
    --add-data 'engine;engine' @flags main.py --noconfirm
if ($LASTEXITCODE -ne 0) { throw 'pyinstaller failed' }
Copy-Item engine\bin\ffpfsc-pkg-tool.exe dist\ -Force
Write-Host 'BUILD OK'
