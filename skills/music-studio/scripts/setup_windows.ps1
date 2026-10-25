<#
 Music Studio - Windows setup (PowerShell 5.1+ / 7).
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 [-AceDir C:\path] [-SkipAce] [-Mock]

 Does: checks Python/git/ffmpeg/uv (offers winget installs), clones ACE-Step 1.5, runs `uv sync`,
 writes ace_step_dir into your workspace config, downloads the models your GPU tier needs
 (`engine.py models --download`), then runs `engine.py check`.
 -Mock : skip ACE-Step entirely and configure the synthetic test engine.
 Nothing is installed without a prompt. Untested on a real Windows box - read the output.
#>
param(
  [string]$AceDir = (Join-Path $env:USERPROFILE "ACE-Step-1.5"),
  [string]$AceRepo = "https://github.com/ace-step/ACE-Step-1.5",
  [switch]$SkipAce,
  [switch]$Mock
)
$ErrorActionPreference = "Stop"
$Skill = Split-Path -Parent $PSScriptRoot
$Scripts = Join-Path $Skill "scripts"

function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Ensure($cmd, $wingetId, $label) {
  if (Have $cmd) { Write-Host "[ok]  $label"; return }
  Write-Host "[missing] $label"
  if (-not (Have "winget")) { throw "$label is missing and winget is not available. Install it manually, then re-run." }
  $a = Read-Host "Install $label with winget ($wingetId)? [y/N]"
  if ($a -match '^[yY]') {
    winget install --id $wingetId -e --accept-package-agreements --accept-source-agreements
    Write-Host "Installed. PATH only refreshes in NEW terminals: open a new PowerShell and re-run this script."
    exit 0
  } else { throw "$label is required." }
}

Write-Host "== Music Studio setup =="
Ensure "python" "Python.Python.3.12" "Python 3"
Ensure "ffmpeg" "Gyan.FFmpeg" "ffmpeg"
python -c "import numpy" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "Installing numpy..."; python -m pip install --user numpy }

python (Join-Path $Scripts "msconfig.py") init | Out-Null

if ($Mock) {
  python (Join-Path $Scripts "msconfig.py") set engine mock | Out-Null
  Write-Host "Configured the mock engine (synthetic test audio, no GPU)."
} elseif (-not $SkipAce) {
  if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    Write-Warning "nvidia-smi not found: no NVIDIA driver/GPU detected. Continuing, but real generation needs one. (Use -Mock to test without.)"
  }
  Ensure "git" "Git.Git" "git"
  Ensure "uv" "astral-sh.uv" "uv (Python package manager)"
  if (Test-Path (Join-Path $AceDir "pyproject.toml")) {
    Write-Host "[ok]  ACE-Step already at $AceDir"
  } else {
    Write-Host "Cloning ACE-Step 1.5 into $AceDir ..."
    git clone $AceRepo $AceDir
  }
  Push-Location $AceDir
  try { Write-Host "Running uv sync (downloads PyTorch + deps; can take a while)..."; uv sync } finally { Pop-Location }
  $fwd = $AceDir -replace '\\','/'
  python (Join-Path $Scripts "msconfig.py") set ace_step_dir $fwd | Out-Null
  python (Join-Path $Scripts "msconfig.py") set engine ace | Out-Null
  Write-Host "Set ace_step_dir = $fwd"
  Write-Host "`n== Models ==  (several GB; safe to re-run, downloads resume)"
  python (Join-Path $Scripts "engine.py") models --download
  if ($LASTEXITCODE -ne 0) { Write-Warning "Model download did not finish. Re-run this script, or: python scripts\engine.py models --download" }
  $a = Read-Host "Also download the higher-quality 'sft' model (a few GB; used by quality 'high' and 'max')? [y/N]"
  if ($a -match '^[yY]') { python (Join-Path $Scripts "engine.py") models --download acestep-v15-sft }
}

Write-Host "`n== Environment check =="
python (Join-Path $Scripts "engine.py") check
Write-Host "`nDone. Double-click start_dashboard.bat (in the skill folder) to open the dashboard."
