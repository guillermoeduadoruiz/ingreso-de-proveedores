@echo off
setlocal
set ROOT=%~dp0
set DIST=%ROOT%dist\IngresosProveedores

echo === Limpiando dist anterior ===
if exist "%ROOT%dist" rmdir /S /Q "%ROOT%dist"

echo === Creando estructura ===
mkdir "%DIST%"
mkdir "%DIST%\assets"
mkdir "%DIST%\pdfs\remitos"
mkdir "%DIST%\pdfs\etiquetas"
mkdir "%DIST%\ingresos_proveedores"
mkdir "%DIST%\ingresos_proveedores\config"
mkdir "%DIST%\ingresos_proveedores\database"
mkdir "%DIST%\ingresos_proveedores\modelos"
mkdir "%DIST%\ingresos_proveedores\servicios"
mkdir "%DIST%\ingresos_proveedores\ui"
mkdir "%DIST%\ingresos_proveedores\utils"
mkdir "%DIST%\configurador"

echo === Copiando archivos raiz ===
copy "%ROOT%requirements.txt" "%DIST%\" >nul

echo === Copiando assets ===
copy "%ROOT%ingresos_proveedores\assets\logo-cuspide.jpg" "%DIST%\assets\" >nul
copy "%ROOT%ingresos_proveedores\assets\manual.html" "%DIST%\assets\" >nul

echo === Copiando package principal ===
copy "%ROOT%ingresos_proveedores\__init__.py" "%DIST%\ingresos_proveedores\" >nul
copy "%ROOT%ingresos_proveedores\main.py" "%DIST%\ingresos_proveedores\" >nul

copy "%ROOT%ingresos_proveedores\config\__init__.py" "%DIST%\ingresos_proveedores\config\" >nul
copy "%ROOT%ingresos_proveedores\config\config_manager.py" "%DIST%\ingresos_proveedores\config\" >nul

copy "%ROOT%ingresos_proveedores\database\__init__.py" "%DIST%\ingresos_proveedores\database\" >nul
copy "%ROOT%ingresos_proveedores\database\conexiones.py" "%DIST%\ingresos_proveedores\database\" >nul
copy "%ROOT%ingresos_proveedores\database\sqlserver.py" "%DIST%\ingresos_proveedores\database\" >nul
copy "%ROOT%ingresos_proveedores\database\mysql.py" "%DIST%\ingresos_proveedores\database\" >nul

copy "%ROOT%ingresos_proveedores\modelos\__init__.py" "%DIST%\ingresos_proveedores\modelos\" >nul
copy "%ROOT%ingresos_proveedores\modelos\proveedor.py" "%DIST%\ingresos_proveedores\modelos\" >nul
copy "%ROOT%ingresos_proveedores\modelos\recepcion.py" "%DIST%\ingresos_proveedores\modelos\" >nul
copy "%ROOT%ingresos_proveedores\modelos\remito.py" "%DIST%\ingresos_proveedores\modelos\" >nul
copy "%ROOT%ingresos_proveedores\modelos\ingreso.py" "%DIST%\ingresos_proveedores\modelos\" >nul

copy "%ROOT%ingresos_proveedores\servicios\__init__.py" "%DIST%\ingresos_proveedores\servicios\" >nul
copy "%ROOT%ingresos_proveedores\servicios\generador_id.py" "%DIST%\ingresos_proveedores\servicios\" >nul
copy "%ROOT%ingresos_proveedores\servicios\recepcion_svc.py" "%DIST%\ingresos_proveedores\servicios\" >nul
copy "%ROOT%ingresos_proveedores\servicios\ingreso_svc.py" "%DIST%\ingresos_proveedores\servicios\" >nul
copy "%ROOT%ingresos_proveedores\servicios\impresion_svc.py" "%DIST%\ingresos_proveedores\servicios\" >nul
copy "%ROOT%ingresos_proveedores\servicios\pdf_generator.py" "%DIST%\ingresos_proveedores\servicios\" >nul
copy "%ROOT%ingresos_proveedores\servicios\dp_generator.py" "%DIST%\ingresos_proveedores\servicios\" >nul

copy "%ROOT%ingresos_proveedores\ui\__init__.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\estilos.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\login_dialog.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\seleccion_proveedor.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\ingreso_remitos.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\registro_ingreso.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\consulta_ingresos.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\ui_config.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\config_impresion_dialog.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\dialogo_materiales.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\dialogo_ayuda.py" "%DIST%\ingresos_proveedores\ui\" >nul
copy "%ROOT%ingresos_proveedores\ui\ventana_principal.py" "%DIST%\ingresos_proveedores\ui\" >nul

copy "%ROOT%ingresos_proveedores\utils\__init__.py" "%DIST%\ingresos_proveedores\utils\" >nul
copy "%ROOT%ingresos_proveedores\utils\system_info.py" "%DIST%\ingresos_proveedores\utils\" >nul
copy "%ROOT%ingresos_proveedores\utils\crypto.py" "%DIST%\ingresos_proveedores\utils\" >nul
copy "%ROOT%ingresos_proveedores\utils\paths.py" "%DIST%\ingresos_proveedores\utils\" >nul

echo === Copiando configurador ===
copy "%ROOT%configurador\main.py" "%DIST%\configurador\" >nul

echo === Creando Lanzador.bat ===
(
echo @echo off
echo cd /d "%%~dp0"
echo python ingresos_proveedores\main.py
echo if errorlevel 1 (
echo     echo.
echo     echo Error al iniciar la aplicacion.
echo     echo Verifique que Python y las dependencias esten instaladas.
echo     pause
echo )
) > "%DIST%\IngresosProveedores.bat"

echo === Creando Lanzador Configurador.bat ===
(
echo @echo off
echo cd /d "%%~dp0"
echo python configurador\main.py
echo if errorlevel 1 (
echo     echo.
echo     echo Error al iniciar el configurador.
echo     pause
echo )
) > "%DIST%\Configurador.bat"

echo === Creando Instalar Dependencias.bat ===
(
echo @echo off
echo echo Instalando dependencias...
echo echo.
echo pip install -r requirements.txt
echo echo.
echo echo === Dependencias instaladas ===
echo echo.
echo echo IMPORTANTE: Verifique que ODBC Driver 17 para SQL Server este instalado.
echo echo Descargue desde: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
echo echo.
echo pause
) > "%DIST%\Instalar Dependencias.bat"

echo === Creando README para el Key User ===
(
echo ============================================
echo  REGISTRO DE INGRESOS DE PROVEEDORES
echo  Instrucciones de instalacion
echo ============================================
echo.
echo 1. REQUISITOS PREVIOS:
echo    - Python 3.10 o superior instalado
echo    - ODBC Driver 17 for SQL Server
echo      (descargar desde Microsoft)
echo    - MySQL Connector (se instala con pip)
echo.
echo 2. INSTALACION:
echo    - Ejecutar "Instalar Dependencias.bat"
echo    - Copiar la carpeta a la PC destino
echo.
echo 3. CONFIGURACION:
echo    - Editar "config_setup.json" con un editor de texto
echo    - Configurar servidores SQL Server y MySQL
echo    - Configurar impresoras
echo    - Ejecutar "Configurador.bat" para configuracion visual
echo.
echo 4. USO DIARIO:
echo    - Ejecutar "IngresosProveedores.bat"
echo    - Login con credenciales de Cygnus
echo    - Seguir los pasos del wizard
echo.
echo 5. ARCHIVOS:
echo    - config_setup.json : Configuracion de la app
echo    - pdfs/             : Remitos y etiquetas generados
echo    - assets/           : Logo y manual de ayuda
echo.
echo ============================================
) > "%DIST%\LEEME.txt"

echo.
echo === Build completado ===
echo Carpeta: %DIST%
echo.
echo Contenido:
dir /B "%DIST%"
echo.
pause
