# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['configurador\\main.py'],
    pathex=['ingresos_proveedores'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'database',
        'database.conexiones',
        'database.mysql',
        'database.sqlserver',
        'config',
        'config.config_manager',
        'utils',
        'utils.paths',
        'utils.crypto',
        'utils.system_info',
        'pymysql',
        'pymysql.connections',
        'pymysql.cursors',
        'pyodbc',
        'win32print',
        'win32api',
        'win32com',
        'win32com.client',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Configurador',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Configurador',
)
