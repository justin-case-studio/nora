# -*- mode: python ; coding: utf-8 -*-
# macOS .app bundle spec — onedir + BUNDLE pattern
# Per PyInstaller maintainers: use EXE(exclude_binaries=True) + COLLECT + BUNDLE
# NOT onefile+BUNDLE (which PyInstaller maintainers explicitly discourage)
# See: https://github.com/orgs/pyinstaller/discussions/8444

from PyInstaller.utils.hooks import collect_all

block_cipher = None
added_files = [
    ('./gui', 'gui'),
]

# Bundle charset_normalizer fully (requests dependency; 3.x uses mypyc PyInstaller misses)
cn_datas, cn_binaries, cn_hidden = collect_all('charset_normalizer')

a = Analysis(
    ['./src/index.py'],
    pathex=['./dist', './src'],
    binaries=cn_binaries,
    datas=added_files + cn_datas,
    # Note: clr (pythonnet) is Windows-only — omitted here to avoid macOS warnings
    hiddenimports=['chardet'] + cn_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# exclude_binaries=True: binaries collected separately by COLLECT (onedir pattern)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='nora',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
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
    name='nora',
)

app = BUNDLE(
    coll,
    name='Nora.app',
    # icon regenerated automatically via `npm run icons` (scripts/generate-icons.sh) from src/assets/logo.png (the SOT)
    icon='src/assets/logo.icns',
    bundle_identifier='io.nora.app',
    version='1.1.0',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleShortVersionString': '1.1.0',
        'CFBundleDisplayName': 'Nora',
    },
)
