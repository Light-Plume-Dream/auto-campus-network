@echo off
chcp 65001 >nul
title 自动校园网连接 - 安装程序
color 0A

echo ========================================
echo   自动校园网连接 - 一键安装
echo ========================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\自动校园网连接"
set "EXE_NAME=自动校园网连接.exe"

if exist "%INSTALL_DIR%\%EXE_NAME%" (
    echo 检测到已安装版本，正在更新...
    taskkill /IM "%EXE_NAME%" /F >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo 正在安装到: %INSTALL_DIR%
echo.

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo 复制文件...
copy /Y "%~dp0%EXE_NAME%" "%INSTALL_DIR%\" >nul
if errorlevel 1 (
    echo 错误: 文件复制失败
    pause
    exit /b 1
)

echo 创建快捷方式...
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\自动校园网连接.lnk'); ^
     $sc.TargetPath = '%INSTALL_DIR%\%EXE_NAME%'; ^
     $sc.WorkingDirectory = '%INSTALL_DIR%'; ^
     $sc.Description = '自动校园网连接'; ^
     $sc.Save()"

powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $sc = $ws.CreateShortcut([Environment]::GetFolderPath('StartMenu') + '\Programs\自动校园网连接.lnk'); ^
     $sc.TargetPath = '%INSTALL_DIR%\%EXE_NAME%'; ^
     $sc.WorkingDirectory = '%INSTALL_DIR%'; ^
     $sc.Description = '自动校园网连接'; ^
     $sc.Save()"

echo.
echo ========================================
echo   安装完成!
echo.
echo   安装位置: %INSTALL_DIR%
echo   桌面快捷方式已创建
echo   开始菜单快捷方式已创建
echo.
echo   您可以通过以下方式启动:
echo   1. 双击桌面上的"自动校园网连接"
echo   2. 开始菜单中找到"自动校园网连接"
echo ========================================
echo.

set /p LAUNCH="是否立即启动? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    start "" "%INSTALL_DIR%\%EXE_NAME%"
)

exit /b 0
