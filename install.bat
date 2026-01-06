@echo off
chcp 65001 >nul
title Forelka Userbot Installer

setlocal enabledelayedexpansion

net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell Start-Process -FilePath "%~f0" -Verb RunAs
    exit /b
)

cls
echo ========================================
echo      Forelka Userbot - Установщик
echo ========================================
echo.
echo Нажмите любую клавишу для начала установки...
pause >nul
cls

cd /d "%~dp0"

echo ========================================
echo      Forelka Userbot - Установщик
echo ========================================
echo.
echo Шаг 1/3: Проверяю Python...
python --version 2>nul
if errorlevel 1 (
    echo Python не найден. Скачиваю и устанавливаю...
    echo.
    
    echo Скачиваю Python 3.11.4...
    powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.4/python-3.11.4-amd64.exe', 'python_installer.exe')"
    
    if exist python_installer.exe (
        echo Устанавливаю Python...
        echo НЕ ЗАКРЫВАЙТЕ ОКНО УСТАНОВКИ!
        echo Дождитесь завершения установки...
        echo.
        start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
        del python_installer.exe
        
        echo Python установлен ✓
        echo.
        echo Перезапускаю для обновления PATH...
        timeout /t 2 /nobreak >nul
        
        start "" cmd /c "cd /d "%~dp0" && python -m pip install --upgrade pip >nul && pip install kurigram aiohttp aiogram colorama requests >nul && if exist main.py (python main.py) else (echo main.py не найден && pause)"
        exit /b
    ) else (
        echo Ошибка скачивания Python
        pause
        exit /b
    )
) else (
    python --version
    echo Python уже установлен ✓
)
echo.

echo Шаг 2/3: Обновляю pip...
python -m pip install --upgrade pip >nul 2>&1
echo pip обновлен ✓
echo.

echo Шаг 3/3: Устанавливаю зависимости...
echo Пожалуйста, подождите...
pip install kurigram aiohttp aiogram colorama requests >nul 2>&1
if errorlevel 1 (
    echo Ошибка установки зависимостей
    pause
    exit /b
)
echo Зависимости установлены ✓
echo.

echo ========================================
echo    Установка завершена!
echo ========================================
echo.

if exist main.py (
    python main.py
) else (
    echo main.py не найден
    echo Поместите main.py в эту папку и запустите заново
    pause
)

exit /b