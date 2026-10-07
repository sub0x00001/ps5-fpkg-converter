# Builds ffpkgsc-pkg-tool (the .NET 9 conversion engine) into engine\bin\.
# Requires the .NET SDK 9 or newer: https://dotnet.microsoft.com/download
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$project = Join-Path $root 'engine\backend\native\src\ffpfsc-pkg-tool\PkgTool.csproj'
$outDir = Join-Path $root 'engine\bin'

$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet) {
    $fallback = Join-Path $env:ProgramFiles 'dotnet\dotnet.exe'
    if (Test-Path $fallback) {
        $env:PATH = "$env:ProgramFiles\dotnet;$env:PATH"
    } else {
        Write-Error 'dotnet not found. Install the .NET 9 SDK first.'
    }
}

Write-Host "Building $project -> $outDir"
dotnet publish $project -c Release -r win-x64 --self-contained true -o $outDir
if ($LASTEXITCODE -ne 0) { Write-Error 'dotnet publish failed' }

& (Join-Path $outDir 'ffpfsc-pkg-tool.exe') version
Write-Host 'Engine tool built successfully.'
