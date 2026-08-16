<#
.SYNOPSIS
    Cross-platform media staging launcher for DaVinci Resolve on Windows 11.
.DESCRIPTION
    Launches stage_stampf_media.py with --clean and --open by default,
    or forwards custom arguments to the Python script.
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "stage_stampf_media.py"

# Locate Python
$PythonExe = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $PythonExe) {
    $PythonExe = Get-Command "py" -ErrorAction SilentlyContinue
}

if (-not $PythonExe) {
    Write-Error "[ERROR] Python was not found in PATH. Please ensure Python 3 is installed."
    exit 1
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " DaVinci Resolve Media Staging Launcher (Windows 11)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if ($ScriptArgs.Count -eq 0) {
    Write-Host "[INFO] Running default staging with --clean and --open..." -ForegroundColor Green
    & $PythonExe.Source $PythonScript --clean --open
} else {
    Write-Host "[INFO] Running staging with custom arguments: $($ScriptArgs -join ' ')" -ForegroundColor Yellow
    & $PythonExe.Source $PythonScript @ScriptArgs
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] Staging script exited with error code $LASTEXITCODE"
}
