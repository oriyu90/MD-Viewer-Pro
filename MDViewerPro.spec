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

# LICENSE / NOTICE をバンドルに含める (LGPL準拠)
_spec_dir = os.path.dirname(os.path.abspath(SPEC))
for _lf in ('LICENSE', 'NOTICE.md'):
    _lpath = os.path.join(_spec_dir, _lf)
    if os.path.exists(_lpath):
        datas.append((_lpath, '.'))

for pkg in ('PySide6', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebChannel',
            'markdown', 'pygments'):
    try:
        tmp = collect_all(pkg)
        datas    += tmp[0]
        binaries += tmp[1]
        hiddenimports += tmp[2]
    except Exception:
        pass

# PyObjC (macOS Dock メニュー対応)
for pkg in ('objc', 'AppKit', 'Foundation'):
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
    'objc',
    'AppKit',
    'Foundation',
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

# ══════════════════════════════════════════════════════════
#  バンドル軽量化: アプリが実際に使う Qt モジュールだけを残す
#  保持セットは QtWebEngine の依存解析 (otool) に基づく 19 framework:
#    QtCore, QtDBus, QtGui, QtNetwork, QtOpenGL, QtOpenGLWidgets,
#    QtPositioning, QtPrintSupport, QtQml, QtQmlMeta, QtQmlModels,
#    QtQmlWorkerScript, QtQuick, QtQuickWidgets, QtSvg, QtWebChannel,
#    QtWebEngineCore, QtWebEngineWidgets, QtWidgets
#  これら以外の未使用 Qt モジュール/開発ツールを除外する。
# ══════════════════════════════════════════════════════════
import re as _re

# 未使用 Qt モジュール (プレフィックス一致で系列ごと除外)。
# 保持セットの名前を誤って含まないよう注意（QtQuick 単体は除外しない）。
_DENY_PREFIX = [
    'Qt3D', 'QtCharts', 'QtGraphs', 'QtDataVisualization', 'QtMultimedia',
    'QtSpatialAudio', 'QtLocation', 'QtBluetooth', 'QtNfc', 'QtSensors',
    'QtSerial', 'QtSql', 'QtTest', 'QtScxml', 'QtStateMachine',
    'QtRemoteObjects', 'QtDesigner', 'QtUiTools', 'QtUiPlugin', 'QtHelp',
    'QtPdf', 'QtWebEngineQuick', 'QtWebView', 'QtWebSockets', 'QtNetworkAuth',
    'QtQuick3D', 'QtQuickControls2', 'QtQuickTemplates2', 'QtQuickDialogs2',
    'QtQuickParticles', 'QtQuickShapes', 'QtQuickTimeline', 'QtQuickEffects',
    'QtQuickLayouts', 'QtQuickTest', 'QtShaderTools', 'QtVirtualKeyboard',
    'QtTextToSpeech', 'QtSvgWidgets', 'QtConcurrent', 'QtPositioningQuick',
]
_deny_re = _re.compile(r'(?:^|/)(?:' + '|'.join(_DENY_PREFIX) + r')')

# 不要な Qt プラグインディレクトリ
_DENY_PLUGINDIR = (
    'plugins/sqldrivers', 'plugins/multimedia', 'plugins/sceneparsers',
    'plugins/geometryloaders', 'plugins/renderplugins', 'plugins/designer',
    'plugins/position', 'plugins/sensors', 'plugins/canbus',
    'plugins/texttospeech', 'plugins/virtualkeyboard', 'plugins/assetimporters',
    'plugins/qmltooling', 'plugins/webview',
)

# 配布物に不要な Qt 開発ツール (.app / 実行ファイル)
_DENY_TOOL_SUBSTR = (
    'Assistant.app', 'Designer.app', 'Linguist.app',
    'Assistant__dot__app', 'Designer__dot__app', 'Linguist__dot__app',
)
_DENY_TOOL_BASE = {
    'balsam', 'balsamui', 'lrelease', 'lupdate', 'lconvert', 'qmlformat',
    'qmllint', 'qmlls', 'qsb', 'svgtoqml', 'qmltyperegistrar',
    'qmlimportscanner', 'qmlcachegen', 'qmlprofiler', 'qmlscene',
    'qmltestrunner', 'designer', 'assistant', 'linguist',
}

def _mdv_keep(dest):
    d = str(dest).replace('\\', '/')
    if _deny_re.search(d):
        return False
    if any(t in d for t in _DENY_PLUGINDIR):
        return False
    if any(t in d for t in _DENY_TOOL_SUBSTR):
        return False
    if d.rsplit('/', 1)[-1] in _DENY_TOOL_BASE:
        return False
    return True

def _mdv_filter(toc, label):
    before = len(toc)
    kept = [e for e in toc if _mdv_keep(e[0])]
    print('[slim] %-9s %d -> %d (removed %d)' % (label, before, len(kept), before - len(kept)))
    return kept

a.binaries = _mdv_filter(a.binaries, 'binaries')
a.datas    = _mdv_filter(a.datas, 'datas')

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
        'CFBundleVersion': '1.3.2',
        'CFBundleShortVersionString': '1.3.2',
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
