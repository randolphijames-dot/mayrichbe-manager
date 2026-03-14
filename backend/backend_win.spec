# -*- mode: python ; coding: utf-8 -*-
# Windows 后端打包：在 Windows 上执行 pyinstaller backend_win.spec
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'sqlalchemy.dialects.sqlite', 'pydantic', 'pydantic_settings', 'apscheduler', 'apscheduler.schedulers.background', 'apscheduler.triggers.date', 'apscheduler.triggers.interval', 'apscheduler.triggers.cron', 'apscheduler.jobstores.memory', 'apscheduler.executors.pool', 'instagrapi', 'cryptography', 'multipart', 'starlette.responses', 'starlette.routing', 'starlette.middleware', 'starlette.middleware.cors', 'starlette.staticfiles', 'googleapiclient', 'googleapiclient.discovery', 'google_auth_oauthlib', 'google.auth']
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('starlette')
hiddenimports += collect_submodules('fastapi')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('pydantic_core')
hiddenimports += collect_submodules('sqlalchemy')
hiddenimports += collect_submodules('instagrapi')
hiddenimports += collect_submodules('googleapiclient')

a = Analysis(
    ['run_server.py'],
    pathex=[],
    binaries=[],
    datas=[('static', 'static'), ('app', 'app')],
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='backend_win',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
