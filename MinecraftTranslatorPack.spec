# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec to package the desktop GUI as a standalone Windows app
# that doesn't require Python installed. Build with:
#   pyinstaller MinecraftTranslatorPack.spec

a = Analysis(
    ['gui/app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gui/web', 'gui/web'),
        ('gui/assets', 'gui/assets'),
        ('localization/es', 'localization/es'),
        # Hand-curated, read-only content (not user data -- see
        # app_paths.resource_dir): the fixed-phrase templates and
        # terminology glossary that ship with the app.
        ('translation/en_es/templates.json', 'translation/en_es'),
        ('translation/en_es/terminology.json', 'translation/en_es'),
    ],
    hiddenimports=[
        'webview.platforms.edgechromium',
        'webview.platforms.winforms',
        'webview.platforms.mshtml',
        'clr_loader',
        'pythonnet',
    ],
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
    name='TraductorDeModpacks',
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
    icon='gui/assets/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TraductorDeModpacks',
)
