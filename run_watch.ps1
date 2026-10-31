# MOTORE_PREZZI_AI - esegue il watch della watchlist e logga/segnala gli alert.
# Chiamato da Task Scheduler (task "MotorePrezzi-Watch").
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$outDir = Join-Path $root "output"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$log = Join-Path $outDir "watch_last.log"
$alertsLog = Join-Path $root "output\alerts.log"
$before = if (Test-Path $alertsLog) { (Get-Item $alertsLog).Length } else { 0 }

$out = & python (Join-Path $root "cli.py") watch 2>&1
$out | Tee-Object -FilePath $log -Append

$after = if (Test-Path $alertsLog) { (Get-Item $alertsLog).Length } else { 0 }
if ($after -gt $before) {
    $msg = "Motore Prezzi: nuovi prodotti sotto target. Vedi output\watch_report.html"
    Write-Output $msg
    if (Get-Module -ListAvailable -Name BurntToast) {
        Import-Module BurntToast
        New-BurntToastNotification -Text "Motore Prezzi AI-hardware", $msg
    }
}
