# Install Ollama Shell (oshell) and make it part of the machine (Windows / PowerShell).
#
# Usage:
#   .\install.ps1                  # core + tui + presence (the default)
#   .\install.ps1 all              # everything: tui, rag, docs, vision, finetune
#   .\install.ps1 rag              # a custom subset of extras (web search is built in)
#   .\install.ps1 -NoShell         # don't touch $PROFILE (no Ctrl+G / `oshell fix`)
#   .\install.ps1 -NoJobs          # don't register the once-a-minute job tick (Task Scheduler)
#   .\install.ps1 -NoOrders        # don't create the standing-orders job
#   .\install.ps1 -NoSetup         # don't run the first-run model wizard at the end
#   .\install.ps1 -DryRun          # print what would happen, change nothing
#
# Steps (each idempotent, each skippable): the `oshell` command; PowerShell
# integration in $PROFILE (Ctrl+G, '#…'→command, last-command capture); theme
# exports in ~/.oshell/current/ (incl. a Windows Terminal color scheme); the
# job tick registered with Task Scheduler + the standing-orders job; the
# first-run wizard. The Mechanic × Drift machine-memory pair needs launchd or
# systemd and is not installed on Windows.
param(
    [string]$Extras = "tui",
    [switch]$NoShell,
    [switch]$NoJobs,
    [switch]$NoOrders,
    [switch]$NoSetup,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$Spec = ".[$Extras]"

function Invoke-Step {
    param([string[]]$Cmd)
    if ($DryRun) { Write-Host "    `$ $($Cmd -join ' ')"; return }
    & $Cmd[0] @($Cmd[1..($Cmd.Length - 1)])
}

function Test-OnPath([string]$Dir) {
    return (($env:PATH -split ';') -contains $Dir)
}

function Add-UserPath([string]$Dir) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (($userPath -split ';') -notcontains $Dir) {
        if (-not $DryRun) { [Environment]::SetEnvironmentVariable("Path", "$userPath;$Dir", "User") }
        Write-Host "    Added $Dir to your user PATH (restart your terminal)."
    }
    $env:PATH = "$env:PATH;$Dir"
}

# ── 1. the command ────────────────────────────────────────────────────────────
Write-Host "==> Installing oshell with extras: [$Extras]"
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "==> Using uv tool install (editable)"
    Invoke-Step @("uv", "tool", "install", "--editable", $Spec, "--force")
    try { Invoke-Step @("uv", "tool", "update-shell") } catch {}
    $Bin = (uv tool dir --bin) 2>$null
    if (-not $Bin) { $Bin = "$env:USERPROFILE\.local\bin" }
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    Write-Host "==> uv not found; falling back to python venv + pip"
    Invoke-Step @("py", "-m", "venv", ".venv")
    Invoke-Step @(".\.venv\Scripts\python.exe", "-m", "pip", "install", "--upgrade", "pip")
    Invoke-Step @(".\.venv\Scripts\python.exe", "-m", "pip", "install", "-e", $Spec)
    $Bin = (Resolve-Path ".\.venv\Scripts" -ErrorAction SilentlyContinue).Path
    if (-not $Bin) { $Bin = "$PSScriptRoot\.venv\Scripts" }
    Add-UserPath $Bin
}
else {
    Write-Error "Need either 'uv' (https://astral.sh/uv) or Python (py launcher) installed."
    exit 1
}
$Oshell = Join-Path $Bin "oshell.exe"
if (-not (Test-Path $Oshell)) { $Oshell = "oshell" }

# ── 2. PowerShell integration in $PROFILE ─────────────────────────────────────
$Marker = "# oshell shell integration"
if (-not $NoShell) {
    Write-Host ""
    $profilePath = $PROFILE.CurrentUserAllHosts
    $line = 'if (Get-Command oshell -ErrorAction SilentlyContinue) { oshell init powershell | Out-String | Invoke-Expression }'
    if ((Test-Path $profilePath) -and (Select-String -Path $profilePath -SimpleMatch $Marker -Quiet)) {
        Write-Host "==> Shell integration already in $profilePath"
    }
    else {
        Write-Host "==> Adding shell integration to $profilePath"
        Write-Host "    $line"
        if (-not $DryRun) {
            New-Item -ItemType Directory -Force -Path (Split-Path $profilePath) | Out-Null
            Add-Content -Path $profilePath -Value "`n$Marker — Ctrl+G asks · '#…' + Ctrl+G becomes the command · oshell fix knows your last command`n$line"
        }
    }
}
else { Write-Host "==> Skipping shell integration (-NoShell)" }

# ── 3. theme exports (incl. a Windows Terminal scheme) ────────────────────────
Write-Host ""
Write-Host "==> Writing theme exports to ~/.oshell/current/ (windows-terminal.json · alacritty · wezterm · …)"
try { Invoke-Step @($Oshell, "theme", "set", "tokyo-night") | Out-Null } catch {}

# ── 4. presence: the job tick + standing orders ───────────────────────────────
if (-not $NoJobs) {
    Write-Host ""
    Write-Host "==> Registering the once-a-minute job tick with Task Scheduler (skip with -NoJobs)"
    Write-Host "    It runs whatever is due and exits otherwise; nothing sensitive runs unattended."
    try { Invoke-Step @($Oshell, "jobs", "install") } catch { Write-Host "NOTE: scheduler registration failed — later: oshell jobs install" }
    if (-not $NoOrders) {
        Write-Host "==> Creating the standing-orders job (edit orders in-app: menu → Standing orders)"
        try { Invoke-Step @($Oshell, "orders", "install") | Out-Null } catch { Write-Host "NOTE: see: oshell orders" }
    }
    else { Write-Host "==> Skipping the standing-orders job (-NoOrders)" }
}
else { Write-Host "==> Skipping the job scheduler (-NoJobs)" }

# Friendly heads-up if Ollama isn't reachable (not fatal).
$Host_ = if ($env:OLLAMA_HOST) { $env:OLLAMA_HOST } else { "http://localhost:11434" }
$OllamaUp = $true
try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "$Host_/api/tags" | Out-Null }
catch {
    $OllamaUp = $false
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

==> Try it (in a new terminal so the shell integration loads):
      oshell tui             # the workspace — bar, tiles, fastfetch, vitals
      oshell                 # interactive agent chat
      oshell do "…"          # propose a command → run / edit / describe / chat / no
      oshell fix             # why did the last command fail, and what fixes it
      oshell theme list      # 22 Omarchy palettes; paste ~/.oshell/current/windows-terminal.json into settings.json
      oshell orders          # standing orders (the agent keeps these true)
      oshell inbox           # what scheduled runs left for you
      oshell doctor          # health-check the whole rig
"@

# ── 5. first-run wizard ───────────────────────────────────────────────────────
if (-not $NoSetup -and -not $DryRun -and $OllamaUp -and [Environment]::UserInteractive) {
    Write-Host ""
    Write-Host "==> First-run wizard (skip with -NoSetup; rerun any time with: oshell setup)"
    try { & $Oshell setup } catch {}
}
elseif (-not $NoSetup -and -not $DryRun) {
    Write-Host ""
    Write-Host "==> Next: run 'oshell setup' to size models to this machine."
}
