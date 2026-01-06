@echo off
chcp 65001 >nul
title Forelka Userbot - Деинсталлятор

setlocal enabledelayedexpansion

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Требуются права администратора...
    powershell Start-Process -FilePath "%~f0" -Verb RunAs
    exit /b
)

cls
echo ========================================
echo    Forelka Userbot - Деинсталлятор
echo ========================================
echo.

set /p "del_deps=Удалить зависимости? (y/n): "
if /i "!del_deps!"=="y" (
    echo Удаляю зависимости...
    python -m pip uninstall kurigram aiohttp aiogram colorama -y >nul 2>&1
    echo Зависимости удалены
    echo.
)

set /p "del_python=Удалить Python? (y/n): "
if /i "!del_python!"=="y" (
    echo Удаляю Python...
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        wmic product where "name like 'Python%%'" call uninstall /nointeractive >nul
        echo Python удален
    ) else (
        echo Python не найден
    )
    echo.
)

echo Удаляю папку со скриптом...
set "script_dir=%~dp0"
cd /d "%USERPROFILE%"
timeout /t 2 /nobreak >nul
rmdir /s /q "%script_dir%"
if !errorlevel! equ 0 (
    echo Папка удалена: !script_dir!
) else (
    echo Не удалось удалить папку
    pause
)

cls
echo.
echo.
echo.
echo           ██████╗ ██╗   ██╗███████╗
echo           ██╔══██╗╚██╗ ██╔╝██╔════╝
echo           ██████╔╝ ╚████╔╝ █████╗
echo           ██╔══██╗  ╚██╔╝  ██╔══╝
echo           ██████╔╝   ██║   ███████╗
echo           ╚═════╝    ╚═╝   ╚══════╝
echo.
echo.
echo.
timeout /t 3 /nobreak >nul

exit