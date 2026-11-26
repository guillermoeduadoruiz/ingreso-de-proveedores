@echo off
cd /d "%~dp0"
python configurador\main.py
if errorlevel 1 (
    echo.
    echo Error al iniciar el configurador.
    pause
)
