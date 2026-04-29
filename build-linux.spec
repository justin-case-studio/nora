# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks.gi import get_gi_typelibs

block_cipher = None
added_files = [
    ('./gui', 'gui'),
]

# Bundle charset_normalizer fully (requests dependency; 3.x uses mypyc PyInstaller misses)
cn_datas, cn_binaries, cn_hidden = collect_all('charset_normalizer')

# pywebview's GTK backend imports WebKit2/Soup lazily at runtime. PyInstaller's
# analysis doesn't see those imports, so its gi runtime hook (which overwrites
# GI_TYPELIB_PATH with $_MEIPASS/girepository-1.0) ends up pointing at a
# directory that lacks WebKit2/Soup typelibs, even when linuxdeploy bundled
# them into the AppDir. Force-include them here so PyInstaller's own typelib
# dir has everything pywebview needs.
wk_bin, wk_data, wk_hidden = get_gi_typelibs('WebKit2', '4.0')
sp_bin, sp_data, sp_hidden = get_gi_typelibs('Soup', '2.4')
# WebKit2 depends on JavaScriptCore's typelib at import time; get_gi_typelibs
# doesn't walk transitive typelib deps, so pull it in explicitly.
jsc_bin, jsc_data, jsc_hidden = get_gi_typelibs('JavaScriptCore', '4.0')

a = Analysis(['./src/index.py'],
             pathex=['./dist', './src'],
             binaries=cn_binaries + wk_bin + sp_bin + jsc_bin,
             datas=added_files + cn_datas + wk_data + sp_data + jsc_data,
             hiddenimports=['clr', 'chardet'] + cn_hidden + wk_hidden + sp_hidden + jsc_hidden,
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# Exclude libs that use DT_RELR relocations (Fedora's glibc 2.36+ feature)
# and are universally available on target systems.
EXCLUDE_LIBS = ('libz.so', 'libz.so.1')
a.binaries = [b for b in a.binaries if not any(b[0].startswith(l) for l in EXCLUDE_LIBS)]

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='nora',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=[],
          #icon='./src/assets/logo.ico',
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
