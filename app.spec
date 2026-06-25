# -*- mode: python ; coding: utf-8 -*-
import os

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries = [
        ('.venv\\Lib\\site-packages\\pyzbar\\libiconv.dll', '.'),
        ('.venv\\Lib\\site-packages\\pyzbar\\libzbar-64.dll', '.'),
    ],
    datas=[('assets', 'assets'), ('controllers', 'controllers'), ('docs', 'docs'), ('flask_server', 'flask_server'), ('forms', 'forms'), ('html_forms', 'html_forms'), ('images', 'images'), ('templates', 'templates'), ('ui', 'ui'), ('utilities', 'utilities'), ('everify_server.log', '.'), ('requirements.txt', '.')],
    hiddenimports=['flask', 'requests', 'jwt', 'jwt.algorithms', 'opencv-python', 'pyzbar', 'numpy', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'sqlite3', 'matplotlib', 'matplotlib.backends.backend_qt5agg', 'matplotlib._c_internal_utils', 'matplotlib._version', 'matplotlib.font_manager', 'matplotlib.backends', 'matplotlib.backends._backend_agg', 'matplotlib.pyplot', 'reportlab', 'psycopg2', 'psycopg2._psycopg', 'psycopg2.extensions', 'psycopg2.extras', 'psycopg2.tz', 'psycopg2.pool', 'psycopg2.sql', 'psycopg2.types', 'psycopg2.errors', 'psycopg2.adapt'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OCCR RVS',
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
    icon=['assets\\icons\\RVS-icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='app',
)
