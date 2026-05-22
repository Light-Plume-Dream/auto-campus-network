@echo off
chcp 65001 >nul
title 自动校园网连接 - 卸载程序
color 0C

echo ========================================
echo   自动校园网连接 - 卸载
echo ========================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\自动校园网连接"
set "EXE_NAME=自动校园网连接.exe"

if not exist "%INSTALL_DIR%\%EXE_NAME%" (
    echo 未检测到已安装的程序
    pause
    exit /b 0
)

echo 正在关闭程序...
taskkill /IM "%EXE_NAME%" /F >nul 2>&1
timeout /t 2 /nobreak >nul

echo 正在删除文件...
rd /s /q "%INSTALL_DIR%" 2>nul

echo 正在删除快捷方式...
del /f /q "%USERPROFILE%\Desktop\自动校园网连接.lnk" 2>nul
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\自动校园网连接.lnk" 2>nul

echo 正在删除开机自启注册表...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "自动校园网连接" /f >nul 2>&1

echo.
echo ========================================
echo   卸载完成!
echo ========================================
echo.
pause
exit /b 0
