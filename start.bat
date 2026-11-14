@echo off
rem Kuto - bam dup de mo giao dien
cd /d "%~dp0"
start "" http://localhost:4173
".runtime\node\node.exe" "app\server.mjs"
pause
