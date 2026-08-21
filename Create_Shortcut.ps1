$TargetFile = Join-Path $PSScriptRoot "dist\OpenProjectTaskBridge.exe"
$WshShell = New-Object -ComObject WScript.Shell

# 1. Create Desktop Shortcut
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$DesktopShortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "OpenProject Task Bridge.lnk"))
$DesktopShortcut.TargetPath = $TargetFile
$DesktopShortcut.WorkingDirectory = (Join-Path $PSScriptRoot "dist")
$DesktopShortcut.Description = "OpenProject Task Bridge Desktop Utility"
$DesktopShortcut.Save()

# 2. Create Start Menu Shortcut
$StartMenuPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Programs)
$StartShortcut = $WshShell.CreateShortcut((Join-Path $StartMenuPath "OpenProject Task Bridge.lnk"))
$StartShortcut.TargetPath = $TargetFile
$StartShortcut.WorkingDirectory = (Join-Path $PSScriptRoot "dist")
$StartShortcut.Description = "OpenProject Task Bridge Desktop Utility"
$StartShortcut.Save()

Write-Host "Desktop and Start Menu shortcuts created successfully!"
