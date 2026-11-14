# Create the 9:16 version of a 16:9 HyperFrames project (one root per project).
# Usage:  & tools\fork_vertical.ps1 "projects\<id>\edit"
# Output: projects\<id>\edit-vertical  (assets shared through a junction, size switched to 1080x1920)
# The agent MUST then re-layout every scene for the vertical frame.
# (ASCII only: Windows PowerShell 5.1 misreads UTF-8 scripts without BOM.)
param([Parameter(Mandatory = $true)][string]$Src)
$ErrorActionPreference = "Stop"
$src = (Resolve-Path $Src).Path
$dst = "$src-vertical"
if (Test-Path $dst) { throw "Already exists: $dst (delete it or edit it in place)" }
New-Item -ItemType Directory $dst | Out-Null
Get-ChildItem $src -Force | Where-Object { $_.Name -notin @("assets", "renders", "node_modules", ".hyperframes", "snapshots") } |
    ForEach-Object { Copy-Item $_.FullName -Destination $dst -Recurse -Force }
if (Test-Path "$src\assets") { cmd /c mklink /J "$dst\assets" "$src\assets" | Out-Null }
Get-ChildItem $dst -Recurse -Include *.html -File | Where-Object { $_.FullName.Substring($dst.Length) -notlike "*assets*" } | ForEach-Object {
    $t = [IO.File]::ReadAllText($_.FullName)
    $t = $t -replace 'data-width="1920"', 'data-width="1080"' -replace 'data-height="1080"', 'data-height="1920"'
    $t = $t -replace 'width=1920, height=1080', 'width=1080, height=1920'
    $t = $t -replace 'width:\s*1920px;(\s*)height:\s*1080px', 'width: 1080px;$1height: 1920px'
    [IO.File]::WriteAllText($_.FullName, $t, (New-Object Text.UTF8Encoding($false)))
}
Write-Output "Vertical project created: $dst"
