# Registra il task pianificato del watch (default: ogni giorno alle 09:00).
#   .\register_watch_task.ps1                 -> daily 09:00
#   .\register_watch_task.ps1 -Time 18:30     -> daily 18:30
#   .\register_watch_task.ps1 -Remove         -> rimuove il task
param(
    [string]$Time = "09:00",
    [switch]$Remove
)

$root = $PSScriptRoot
$taskName = "MotorePrezzi-Watch"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Output "Task '$taskName' rimosso."
    return
}

$ps = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$action = New-ScheduledTaskAction -Execute $ps `
    -WorkingDirectory $root `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$root\run_watch.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "MOTORE_PREZZI_AI: watchlist prezzi AI-hardware" -Force | Out-Null
Write-Output "Task '$taskName' registrato (daily $Time)."
