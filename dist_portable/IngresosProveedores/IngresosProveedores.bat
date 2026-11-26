@echo off
cd /d "%~dp0"
python ingresos_proveedores\main.py
if errorlevel 1 (
    echo.
    echo Error al iniciar la aplicacion.
    echo Verifique que Python y las dependencias esten instaladas.
    pause
)
