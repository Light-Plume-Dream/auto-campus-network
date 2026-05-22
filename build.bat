@echo off
chcp 65001 >nul
set PY=C:\Users\31841\AppData\Local\Programs\Python\Python314\python.exe
echo ========================================
echo   自动校园网连接 - 打包工具
echo ========================================
echo.

echo [1/2] 安装依赖...
%PY% -m pip install Pillow pywin32 pyinstaller --user --quiet
echo.

echo [2/2] 开始打包 (单文件模式)...
%PY% -m PyInstaller --clean --onefile --windowed --name "自动校园网连接" --icon=app_icon.ico main.py

if errorlevel 1 (
    echo 错误: 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成!
echo   输出目录: dist\自动校园网连接.exe
echo ========================================
pause
