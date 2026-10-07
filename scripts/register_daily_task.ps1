# Registers a Windows Task Scheduler task that runs the daily job.
#
#   powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1            # 09:00 daily
#   powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1 -At 08:30
#   powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1 -Remove
#
# Runs as the current user, only when logged on (no stored password needed).
# -StartWhenAvailable means that if the laptop was asleep/off at the
# scheduled time, the task runs as soon as it's back on (on battery too).

param(
    [string]$At = "09:00",
    [string]$TaskName = "JobSearchAssistantDaily",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task '$TaskName'."
    exit 0
}

$script = Join-Path $PSScriptRoot "run_daily.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At $At
# Battery flags: Windows' defaults skip the run on a laptop that's unplugged.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Job Search Assistant: fetch new jobs, score them, send the Telegram/email digest." `
    -Force | Out-Null

Write-Host "Registered '$TaskName' to run daily at $At."
Write-Host "Run it now to test:  Start-ScheduledTask -TaskName $TaskName"
Write-Host "Logs: $(Split-Path -Parent $PSScriptRoot)\logs\"
