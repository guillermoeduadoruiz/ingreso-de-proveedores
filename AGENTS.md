# AGENTS.md

Windows-only PyQt5 desktop app (Spanish UI) that records warehouse goods receipts (ingresos de proveedores). No web framework, no tests, no CI, no linter configured. Python 3.13 in `.venv`.

**Al retomar el proyecto, leer primero `CONTEXTO_DESARROLLO.md`** para tener el snapshot completo de estado, arquitectura, decisiones recientes, pendientes y cómo ejecutar/verificar.

## Two apps, one package
- `ingresos_proveedores/` — main app. Entrypoint: `ingresos_proveedores/main.py` (login dialog, then `VentanaPrincipal`).
- `configurador/main.py` — standalone setup tool that reuses the `ingresos_proveedores` package (DB, printers, labels).

Layering: `config/` (settings) -> `database/` (SQL Server + MySQL clients) -> `modelos/` (dataclasses) -> `servicios/` (business logic, PDF generation) -> `ui/` (PyQt5 windows/dialogs).

## Run (from repo root)
```
.venv\Scripts\python.exe ingresos_proveedores\main.py
.venv\Scripts\python.exe configurador\main.py
```
Both entrypoints insert the package dir into `sys.path`, so modules import flatly (`from config.config_manager import ...`). Do NOT run modules directly from inside `ingresos_proveedores/` — relative imports break. `configurador/main.py` must be run from repo root (it computes `BASE_DIR` from its own location).

## Config & secrets
- App config lives in `config_setup.json` at repo root (path resolved by `utils/paths.py`, so also beside the exe when frozen). It contains real internal server credentials — do not commit changes that expose plaintext.
- DB passwords are stored `$ENC$`-prefixed. They are encrypted with a machine-derived key (PBKDF2 + salt at `%APPDATA%\IngresosProveedores\.salt`). Hand-editing a password in the JSON silently breaks config — re-encrypt via `utils.crypto.encrypt_password` instead.
- App unlock password hash: `%APPDATA%\IngresosProveedores\.config_pass` (set up by `ConfigManager`).
- The app needs BOTH databases reachable: SQL Server via pyodbc (ODBC Driver 17/18 must be installed; driver auto-resolved by `DRIVER_PRIORITY` in `database/conexiones.py`) and MySQL via pymysql.

## Distribution / builds
Two build scripts, both DELETE `build/` and `dist/` first:
- `build_dist.bat` — portable source-copy dist with launcher `.bat` files.
- `build_exe.bat` — PyInstaller from `IngresosProveedores.spec` + `Configurador.spec` (requires `pip install pyinstaller`).

If you add a new module, it must be registered in BOTH the `copy` list in `build_dist.bat` AND the `hiddenimports` list in the matching `.spec`, or it will be missing from the built app.

## Git notes
- Single commit (`Primer commit`); build artifacts (`build/`, `dist/`, `__pycache__/`) and generated PDFs under `pdfs/` are committed — there is no `.gitignore`. Only stage intentional changes.
