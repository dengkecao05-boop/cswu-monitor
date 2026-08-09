$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$LogDir = Join-Path $ScriptDir "logs"
$LogFile = Join-Path $LogDir "monitor.log"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$BundledPython = "C:\Users\38956\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

try {
  "[$(Get-Date -Format s)] start" | Out-File -FilePath $LogFile -Append -Encoding utf8

  if ($PythonCommand) {
    & $PythonCommand.Source .\monitor.py --config .\config.json *>> $LogFile
  } elseif (Test-Path $BundledPython) {
    & $BundledPython .\monitor.py --config .\config.json *>> $LogFile
  } else {
    throw "Python was not found. Install Python or set the Python path in run_once.ps1."
  }

  "[$(Get-Date -Format s)] done" | Out-File -FilePath $LogFile -Append -Encoding utf8
} catch {
  "[$(Get-Date -Format s)] error: $($_.Exception.Message)" | Out-File -FilePath $LogFile -Append -Encoding utf8
  throw
}
