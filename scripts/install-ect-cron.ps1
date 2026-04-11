# ============================================================
#  ECT News Agent - Windows Task Scheduler Installer
# ============================================================
#  Registers 3 scheduled tasks to run the ECT news agent at:
#    - 07:00  (morning brief)
#    - 11:00  (midday update)
#    - 15:00  (afternoon update)
#
#  Usage (run as Administrator from PowerShell):
#    cd C:\Users\thund\thundthornthep-ai.github.io
#    powershell -ExecutionPolicy Bypass -File scripts\install-ect-cron.ps1
#
#  To uninstall:
#    powershell -ExecutionPolicy Bypass -File scripts\install-ect-cron.ps1 -Uninstall
# ============================================================

param(
  [switch]$Uninstall
)

$TaskPrefix = "LAS-ECT-News"
$BatPath = "C:\Users\thund\thundthornthep-ai.github.io\scripts\run-ect-news-local.bat"
$Times = @(
  @{Label="Morning"; Time="07:00"},
  @{Label="Midday";  Time="11:00"},
  @{Label="Afternoon"; Time="15:00"}
)

if ($Uninstall) {
  Write-Host "Uninstalling ECT News Agent scheduled tasks..." -ForegroundColor Yellow
  foreach ($t in $Times) {
    $name = "$TaskPrefix-$($t.Label)"
    $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($existing) {
      Unregister-ScheduledTask -TaskName $name -Confirm:$false
      Write-Host "  Removed: $name" -ForegroundColor Green
    } else {
      Write-Host "  Not found: $name" -ForegroundColor Gray
    }
  }
  Write-Host "Done." -ForegroundColor Green
  exit 0
}

Write-Host "Installing ECT News Agent scheduled tasks..." -ForegroundColor Cyan
Write-Host "Batch file: $BatPath" -ForegroundColor Gray

if (-not (Test-Path $BatPath)) {
  Write-Error "Batch file not found: $BatPath"
  exit 1
}

foreach ($t in $Times) {
  $name = "$TaskPrefix-$($t.Label)"
  $time = $t.Time

  # Remove if exists
  $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  if ($existing) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
  }

  $action = New-ScheduledTaskAction -Execute $BatPath
  $trigger = New-ScheduledTaskTrigger -Daily -At $time
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Limited
  $settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

  Register-ScheduledTask `
    -TaskName $name `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "ECT Daily News Agent - automated run at $time (CEO directive for BKK SK election 2569)"

  Write-Host "  Registered: $name at $time" -ForegroundColor Green
}

Write-Host "`nAll 3 tasks installed. Verify in Task Scheduler (taskschd.msc)." -ForegroundColor Cyan
Write-Host "They will appear under: Task Scheduler Library -> $TaskPrefix-*" -ForegroundColor Gray
Write-Host "`nTo test manually now, run:" -ForegroundColor Yellow
Write-Host "  $BatPath" -ForegroundColor White
