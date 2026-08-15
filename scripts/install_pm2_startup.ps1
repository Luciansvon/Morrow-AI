param(
    [Parameter(Mandatory = $true)]
    [string]$Pm2Path
)

$ErrorActionPreference = "Stop"
$TaskName = "Morrow PM2 Startup"
$ResolvedPm2 = (Get-Command $Pm2Path -ErrorAction Stop).Source
$CurrentUser = "$env:USERDOMAIN\$env:USERNAME"
$CommandLine = "/d /c `"`"$ResolvedPm2`" resurrect`""

$Action = New-ScheduledTaskAction -Execute $env:ComSpec -Argument $CommandLine
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Restore the saved PM2 process list for Morrow after Windows sign-in." `
    -Force | Out-Null

Write-Host "Morrow PM2 startup task installed for $CurrentUser."
Write-Host "PM2 will run 'resurrect' after this user signs in."
