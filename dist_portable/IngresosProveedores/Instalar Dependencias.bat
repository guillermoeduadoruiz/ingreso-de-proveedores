@echo off
echo Instalando dependencias...
echo.
pip install -r requirements.txt
echo.
echo === Dependencias instaladas ===
echo.
echo IMPORTANTE: Verifique que ODBC Driver 17 para SQL Server este instalado.
echo Descargue desde: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
echo.
pause
