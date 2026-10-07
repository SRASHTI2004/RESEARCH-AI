# Runs the daily job (fetch -> score -> digest) using the project's venv.
# Called by the scheduled task that register_daily_task.ps1 creates; safe to
# run by hand too:  powershell -ExecutionPolicy Bypass -File scripts\run_daily.ps1
#
# Output is appended to logs\daily-YYYY-MM.log (git-ignored). Tokens and
# passwords are never written there — the app redacts them before logging.

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$python = Join-Path $repo "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "venv not found at $python - create it first (see README)."
}

New-Item -ItemType Directory -Force (Join-Path $repo "logs") | Out-Null
$log = Join-Path $repo ("logs\daily-{0:yyyy-MM}.log" -f (Get-Date))

"===== run-daily {0:yyyy-MM-dd HH:mm:ss} =====" -f (Get-Date) | Out-File -Append -Encoding utf8 $log
# PYTHONIOENCODING: job titles contain non-ASCII characters; keep the log readable.
$env:PYTHONIOENCODING = "utf-8"
# Redirect through cmd, not PowerShell: Windows PowerShell 5.1 turns every
# stderr line (Python logging, warnings) into an error record that stops the
# script under ErrorActionPreference=Stop, and its *>> writes UTF-16.
cmd.exe /d /s /c "`"`"$python`" -m app.cli run-daily >> `"$log`" 2>&1`""
$code = $LASTEXITCODE
"exit code: $code" | Out-File -Append -Encoding utf8 $log
exit $code
