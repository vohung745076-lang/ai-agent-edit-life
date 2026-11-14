# Load the agent environment: portable Node 22 + FFmpeg from .runtime
# Usage:  . "d:\Ai agent edit video life\tools\env.ps1"
# (ASCII only: Windows PowerShell 5.1 misreads UTF-8 scripts without BOM.)
$global:KUTO_ROOT = Split-Path -Parent $PSScriptRoot
$rt = Join-Path $global:KUTO_ROOT ".runtime"
$env:PATH = "$rt\node;$rt\ffmpeg\bin;$env:PATH"
$env:HYPERFRAMES_FFMPEG_PATH  = "$rt\ffmpeg\bin\ffmpeg.exe"
$env:HYPERFRAMES_FFPROBE_PATH = "$rt\ffmpeg\bin\ffprobe.exe"
$env:FFMPEG_PATH  = $env:HYPERFRAMES_FFMPEG_PATH
$env:FFPROBE_PATH = $env:HYPERFRAMES_FFPROBE_PATH
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
