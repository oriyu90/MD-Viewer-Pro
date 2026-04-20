# -*- mode: python ; coding: utf-8 -*-
import os
import shutil
from PyInstaller.utils.hooks import collect_all

import glob as _glob
datas = []
binaries = []
hiddenimports = []

# 資料箱のサンプルファイルをバンドルに含める
_shiryobako = os.path.join(os.path.dirname(os.path.abspath(SPEC)), '資料箱')
for _f in _glob.glob(os.path.join(_shiryobako, 'sample_*.md')):
    datas.append((_f, '資料箱'))

for pkg in ('PySide6', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebChannel',
            'markdown', 'pygments'):
    try:
        tmp = collect_all(pkg)
        datas    += tmp[0]
        binaries += tmp[1]
        hiddenimports += tmp[2]
    except Exception:
        pass

hiddenimports += [
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebChannel',
    'PySide6.QtPrintSupport',
    'markdown.extensions.tables',
    'markdown.extensions.fenced_code',
    'markdown.extensions.codehilite',
    'pygments',
    'pygments.lexers',
    'pygments.formatters',
    'pygments.styles',
    'html.parser',
    'urllib.request',
    'urllib.error',
    'base64',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
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
    [],
    exclude_binaries=True,
    name='MDViewerPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='MDicon.icns',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MDViewerPro',
)
app = BUNDLE(
    coll,
    name='MDViewerPro.app',
    icon='MDicon.icns',
    bundle_identifier='com.mdviewerpro.app',
    info_plist={
        'CFBundleName': 'MD Viewer Pro',
        'CFBundleDisplayName': 'MD Viewer Pro',
        'CFBundleVersion': '1.00',
        'CFBundleShortVersionString': '1.00',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion': '10.14',
        'NSPrincipalClass': 'NSApplication',
        # macOS Gatekeeper / Sandbox 対策
        'NSAppleEventsUsageDescription': 'MD Viewer Pro requires Apple Events.',
        'com.apple.security.cs.allow-unsigned-executable-memory': True,
        'com.apple.security.cs.disable-library-validation': True,
        # .md / .markdown ファイルの関連付け
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Markdown Document',
                'CFBundleTypeExtensions': ['md', 'markdown'],
                'CFBundleTypeIconFile': 'MDicon',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
                'LSItemContentTypes': [
                    'net.daringfireball.markdown',
                    'public.plain-text',
                ],
            }
        ],
        'UTImportedTypeDeclarations': [
            {
                'UTTypeIdentifier': 'net.daringfireball.markdown',
                'UTTypeDescription': 'Markdown Document',
                'UTTypeConformsTo': ['public.plain-text', 'public.content'],
                'UTTypeTagSpecification': {
                    'public.filename-extension': ['md', 'markdown'],
                    'public.mime-type': 'text/markdown',
                },
            }
        ],
    },
)
