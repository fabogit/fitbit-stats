# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['api.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 
        'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan', 'uvicorn.lifespan.on',
        'modules.briefing', 'modules.etl', 'modules.load_plan', 'modules.metrics', 'modules.parsers',
        'modules.pipeline', 'modules.run_config', 'modules.sources', 'jobs'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# One-directory build: the executable plus an _internal/ folder. Unlike a
# one-file build it does not unpack ~140 MB into a temporary folder on every
# launch, and it runs as a single process (no bootloader parent).
exe = EXE(
    pyz,
    a.scripts,
    [
        # Interpreter options. A frozen executable ignores PYTHON* environment
        # variables, so they are set here: unbuffered stdout/stderr (output
        # reaches a pipe immediately) and UTF-8 mode (printing a non-ASCII path
        # cannot raise UnicodeEncodeError on Windows).
        ('u', None, 'OPTION'),
        ('X utf8', None, 'OPTION'),
    ],
    exclude_binaries=True,
    name='fitstats-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity='-',
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='fitstats-server',
)
