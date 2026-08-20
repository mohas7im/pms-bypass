# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

BASE_DIR = Path(os.getcwd())

datas = [
    (str(BASE_DIR / 'app' / 'templates'), 'app/templates'),
    (str(BASE_DIR / 'app' / 'static'), 'app/static'),
]

hidden_imports = [
    'django',
    'django.core.management',
    'django.core.management.commands.runserver',
    'django.contrib.contenttypes',
    'django.contrib.contenttypes.models',
    'django.contrib.sessions',
    'django.contrib.sessions.serializers',
    'django.contrib.sessions.backends.signed_cookies',
    'django.contrib.messages',
    'django.contrib.messages.storage.fallback',
    'django.contrib.staticfiles',
    'django.template.loaders.filesystem',
    'django.template.loaders.app_directories',
    'requests',
    'urllib3',
    'dotenv',
    'core',
    'core.settings',
    'core.urls',
    'core.wsgi',
    'app',
    'app.urls',
    'app.views',
    'app.services',
    'app.services.openproject_client',
    'app.services.validator',
    'app.services.importer',
]

a = Analysis(
    ['launcher.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OpenProjectBulkUploader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to True so user can see startup log or close cleanly
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)
