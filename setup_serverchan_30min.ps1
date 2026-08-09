$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$TaskName = "CQC Official New Content Monitor"
$RunScript = Join-Path $ScriptDir "run_once.ps1"

if (-not (Test-Path $RunScript)) {
  throw "run_once.ps1 was not found in this folder."
}

$SendKey = Read-Host "Paste your ServerChan SendKey"
if ([string]::IsNullOrWhiteSpace($SendKey)) {
  throw "ServerChan SendKey cannot be empty."
}

[Environment]::SetEnvironmentVariable("SERVERCHAN_SENDKEY", $SendKey.Trim(), "User")
$env:SERVERCHAN_SENDKEY = $SendKey.Trim()

$Action = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$RunScript`""
schtasks /Create /SC MINUTE /MO 30 /TN $TaskName /TR $Action /F | Out-Host

Write-Host ""
Write-Host "Done. The monitor will run every 30 minutes."
Write-Host "It only sends a WeChat message when new content is found."
Write-Host "Logs: $ScriptDir\logs\monitor.log"
