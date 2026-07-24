@echo off
set ROOT=%~dp0

echo === Limpiando builds anteriores ===
if exist "%ROOT%build" rmdir /S /Q "%ROOT%build"
if exist "%ROOT%dist" rmdir /S /Q "%ROOT%dist"

echo === Generando EXE principal (IngresosProveedores) ===
cd /d "%ROOT%"
pyinstaller --noconfirm IngresosProveedores.spec
if errorlevel 1 (
    echo === ERROR en compilacion de IngresosProveedores ===
    pause
    exit /b 1
)

echo === Generando EXE configurador ===
pyinstaller --noconfirm Configurador.spec
if errorlevel 1 (
    echo === ERROR en compilacion de Configurador ===
    pause
    exit /b 1
)

echo === Copiando configurador a carpeta de IngresosProveedores ===
set DIST=%ROOT%dist\IngresosProveedores
set DISTCONF=%ROOT%dist\Configurador

if not exist "%DIST%\Configurador" mkdir "%DIST%\Configurador"
xcopy /E /I /Q "%DISTCONF%\_internal" "%DIST%\Configurador\_internal" >nul
copy "%DISTCONF%\Configurador.exe" "%DIST%\Configurador\" >nul

echo === Copiando archivos externos ===
copy "%ROOT%config_setup.json" "%DIST%\" >nul
copy "%ROOT%requirements.txt" "%DIST%\" >nul

echo === Creando Lanzador.bat ===
(
echo @echo off
echo cd /d "%%~dp0"
echo start "" IngresosProveedores.exe
) > "%DIST%\IngresosProveedores.bat"

echo === Creando Lanzador Configurador.bat ===
(
echo @echo off
echo cd /d "%%~dp0"
echo start "" Configurador\Configurador.exe
) > "%DIST%\Configurador.bat"

echo === Creando LEEME.txt ===
(
echo ============================================
echo  REGISTRO DE INGRESOS DE PROVEEDORES
echo  Instrucciones de instalacion
echo ============================================
echo.
echo 1. REQUISITOS PREVIOS:
echo    - ODBC Driver 17 for SQL Server
echo      (descargar desde Microsoft)
echo.
echo 2. INSTALACION:
echo    - Copiar toda esta carpeta a la PC destino
echo    - No se requiere Python instalado
echo.
echo 3. CONFIGURACION:
echo    - Editar "config_setup.json" con un editor de texto
echo    - O ejecutar "Configurador.bat" para configuracion visual
echo    - Configurar servidores SQL Server y MySQL
echo    - Configurar impresoras
echo.
echo 4. USO DIARIO:
echo    - Ejecutar "IngresosProveedores.bat"
echo    - Login con credenciales de Cygnus
echo    - Seguir los pasos del wizard
echo.
echo 5. ARCHIVOS:
echo    - config_setup.json  : Configuracion de la app
echo    - pdfs/              : Remitos y etiquetas generados
echo    - assets/            : Logo y manual de ayuda
echo    - Configurador/      : Herramienta de configuracion
echo.
echo ============================================
) > "%DIST%\LEEME.txt"

echo.
echo === Build completado ===
echo Carpeta: %DIST%
echo.
dir /B "%DIST%"
echo.
pause
