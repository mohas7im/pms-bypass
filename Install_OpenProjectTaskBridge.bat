@echo off
title Installing OpenProject Task Bridge...
echo ======================================================
echo    INSTALLING OPENPROJECT TASK BRIDGE DESKTOP APP
echo ======================================================
echo.

set INSTALL_DIR=%LOCALAPPDATA%\OpenProjectTaskBridge
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo Copying application files to %INSTALL_DIR%...
xcopy /E /I /Y "%~dp0dist\*" "%INSTALL_DIR%\" >nul

echo Creating Desktop and Start Menu Shortcuts...
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\OpenProject Task Bridge.lnk');$s.TargetPath='%INSTALL_DIR%\OpenProjectTaskBridge.exe';$s.WorkingDirectory='%INSTALL_DIR%';$s.Save()"
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\OpenProject Task Bridge.lnk');$s.TargetPath='%INSTALL_DIR%\OpenProjectTaskBridge.exe';$s.WorkingDirectory='%INSTALL_DIR%';$s.Save()"

echo.
echo ======================================================
echo SUCCESS: OpenProject Task Bridge has been installed!
echo A shortcut "OpenProject Task Bridge" is on your Desktop.
echo ======================================================
echo.
pause
