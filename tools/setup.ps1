# One-time setup on a new machine: portable Node 22 + FFmpeg into .runtime, Python libs, HyperFrames skills.
# Usage:  powershell -ExecutionPolicy Bypass -File tools\setup.ps1
# (ASCII only: Windows PowerShell 5.1 misreads UTF-8 scripts without BOM.)
$ErrorActionPreference = "Stop"; $ProgressPreference = "SilentlyContinue"
$root = Split-Path -Parent $PSScriptRoot
$rt = Join-Path $root ".runtime"
New-Item -ItemType Directory -Force $rt | Out-Null

if (-not (Test-Path "$rt\node\node.exe")) {
    $idx = Invoke-RestMethod "https://nodejs.org/dist/index.json"
    $v = ($idx | Where-Object { $_.version -like "v22.*" } | Select-Object -First 1).version
    Write-Output "Downloading Node $v ..."
    Invoke-WebRequest "https://nodejs.org/dist/$v/node-$v-win-x64.zip" -OutFile "$rt\node.zip"
    Expand-Archive "$rt\node.zip" $rt -Force
    Rename-Item "$rt\node-$v-win-x64" "node"; Remove-Item "$rt\node.zip"
}
if (-not (Test-Path "$rt\ffmpeg\bin\ffmpeg.exe")) {
    Write-Output "Downloading FFmpeg ..."
    Invoke-WebRequest "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "$rt\ff.zip"
    Expand-Archive "$rt\ff.zip" $rt -Force
    $d = (Get-ChildItem $rt -Directory -Filter "ffmpeg-*")[0]
    Rename-Item $d.FullName "ffmpeg"; Remove-Item "$rt\ff.zip"
}
. "$PSScriptRoot\env.ps1"
python -m pip install --quiet -r "$root\requirements.txt"
Set-Location $root
npx --yes hyperframes telemetry disable | Out-Null
npx --yes hyperframes skills update
Write-Output "Setup done. Run start.bat to open Kuto."
