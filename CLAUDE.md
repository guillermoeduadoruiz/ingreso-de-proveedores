# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run main app from source
.venv\Scripts\python.exe ingresos_proveedores\main.py

# Run configurator
.venv\Scripts\python.exe configurador\main.py

# Syntax check a file
.venv\Scripts\python.exe -m py_compile ingresos_proveedores\ui\mateti.py

# Build standalone .exe (clears build/ and dist/ first)
build_exe.bat

# Build portable source distribution
build_dist.bat
```

Both entry points insert `ingresos_proveedores/` into `sys.path`, so all imports are flat (`from config.config_manager import ...`). Never run modules from inside `ingresos_proveedores/` directly — it breaks imports.

## Architecture

Layered desktop app (PyQt5, Windows-only):

```
config/    → ConfigManager: loads/saves config_setup.json, manages encrypted DB credentials
database/  → conexiones.py (dataclasses), sqlserver.py (pyodbc), mysql.py (pymysql)
modelos/   → dataclasses: Ingreso, Remito, RecepcionPrevista, Proveedor
servicios/ → business logic: ingreso_svc, recepcion_svc, impresion_svc, pdf_generator, dp_generator
ui/        → PyQt5 widgets (VentanaPrincipal + stacked pages + dialogs)
```

### Main window navigation

`VentanaPrincipal` (`ui/ventana_principal.py`) uses a `QStackedWidget` with indexed pages. Pages are created in `_crear_paginas()` and connected via callbacks (`set_on_confirmar`, `set_on_volver`, etc.). To add a new module: create a `QWidget` subclass in `ui/`, add a `PAG_*` constant, instantiate in `_crear_paginas()`, wire callbacks, and register the new file in both `build_dist.bat` (copy list) and `IngresosProveedores.spec` (`hiddenimports`).

### Two-database strategy

- **SQL Server** (pyodbc, read-only): source of planned receipts, materials, suppliers, customers. Requires ODBC Driver 17/18.
- **MySQL** (pymysql, write): audit log of completed ingresos, remitos, generated shipment numbers. Auto-creates schema on first connect.

Credentials are encrypted with a machine-specific key (PBKDF2 → Fernet). Passwords in `config_setup.json` are prefixed `$ENC$`. Never edit them manually; use `utils.crypto.encrypt_password`.

### Print subsystem

`ImpresionService` groups remitos by `sucursal_destino`, skipping destinations in `impresion.sucursales_excluidas`. For each destination it generates a PDF remito and label sheet. Printing uses `ShellExecute("printto", pdf, printer)`. For Honeywell PC42t printers (name contains "honeywell"/"pc42"), labels are sent as Direct Protocol (DP) via `WritePrinter` RAW. The remito PDF overlays text on a pre-printed form — margin coordinates are in mm measured at 300 dpi and should not be changed without re-measuring.

### Configuration

`ConfigManager` reads `config_setup.json` (resolved via `utils/paths.py`, which handles frozen/unfrozen PyInstaller context). Multiple printer profiles are supported; active profile is `impresoras.activa`. Config password hash lives in `%APPDATA%\IngresosProveedores\.config_pass`.

## Key constraints

- **No tests, no CI, no linter configured.** Syntax-check with `py_compile` as a quick sanity check.
- **No `.gitignore`**: `build/`, `dist/`, `pdfs/`, and `__pycache__/` are tracked. Stage only intentional files before committing.
- When adding a new Python module used at runtime, register it in both `build_dist.bat` AND `IngresosProveedores.spec` (`hiddenimports`), or it will be missing from the built `.exe`.
- The `CONTEXTO_DESARROLLO.md` file contains extensive notes on print calibration, known bugs, and decisions that are hard to derive from code alone — read it before touching the print subsystem.
