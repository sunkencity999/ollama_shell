# Install Ollama Shell (oshell) and put it on your PATH (Windows / PowerShell).
#
# Usage:
#   .\install.ps1              # core + tui (interactive default)
#   .\install.ps1 all          # everything: tui, web, rag, docs, vision, finetune
#   .\install.ps1 web,rag      # a custom subset of extras
#
# Prefers `uv tool install` (manages a PATH-linked bin dir, editable from this
# repo). Falls back to a local .venv + adding its Scripts dir to the user PATH.
param([string]$Extras = "tui")

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$Spec = ".[$Extras]"
Write-Host "==> Installing oshell with extras: [$Extras]"

function Test-OnPath([string]$Dir) {
    return (($env:PATH -split ';') -contains $Dir)
}

function Add-UserPath([string]$Dir) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (($userPath -split ';') -notcontains $Dir) {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$Dir", "User")
        Write-Host "    Added $Dir to your user PATH (restart your terminal)."
    }
    $env:PATH = "$env:PATH;$Dir"
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "==> Using uv tool install (editable)"
    uv tool install --editable $Spec --force
    uv tool update-shell 2>$null
    $Bin = (uv tool dir --bin) 2>$null
    if (-not $Bin) { $Bin = "$env:USERPROFILE\.local\bin" }
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    Write-Host "==> uv not found; falling back to python venv + pip"
    py -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
    .\.venv\Scripts\python.exe -m pip install -e $Spec
    $Bin = (Resolve-Path ".\.venv\Scripts").Path
    Add-UserPath $Bin
}
else {
    Write-Error "Need either 'uv' (https://astral.sh/uv) or Python (py launcher) installed."
    exit 1
}

# Friendly heads-up if Ollama isn't reachable (not fatal).
$Host_ = if ($env:OLLAMA_HOST) { $env:OLLAMA_HOST } else { "http://localhost:11434" }
try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "$Host_/api/tags" | Out-Null }
catch {
    Write-Host ""
    Write-Host "NOTE: Ollama doesn't appear to be running at $Host_."
    Write-Host "      Install it from https://ollama.com and start it."
}

Write-Host ""
Write-Host "==> Installed 'oshell' to $Bin"
if (-not (Test-OnPath $Bin)) {
    Write-Host "    Open a NEW terminal so the updated PATH takes effect."
}
Write-Host @"

==> Try it (in a new terminal):
      oshell                 # interactive agent chat
      oshell tui             # Textual workspace
      oshell finetune detect
      oshell config          # resolved config + capabilities
"@
