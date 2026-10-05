# -*- mode: python ; coding: utf-8 -*-
# MD Viewer Pro — Windows (x64) portable build spec.
# Derived from MDViewerPro.spec (macOS). Differences:
#   - no BUNDLE / info_plist (macOS only)
#   - icon: 資料箱/IMG_1152.ico (same image as favicon.ico)
#   - no argv_emulation / codesign_identity / entitlements (macOS only)
#   - no objc/AppKit/Foundation collection (macOS Dock support only)
import os
from PyInstaller.utils.hooks import collect_all

import glob as _glob
datas = []
binaries = []
hiddenimports = []

# 資料箱のサンプルファイルをバンドルに含める (ASCII名 v1.4.7)
_shiryobako = os.path.join(os.path.dirname(os.path.abspath(SPEC)), '資料箱')
for _f in _glob.glob(os.path.join(_shiryobako, 'sample_*.md')):
    datas.append((_f, '資料箱'))

# LICENSE / NOTICE をバンドルに含める (LGPL準拠)
_spec_dir = os.path.dirname(os.path.abspath(SPEC))
for _lf in ('LICENSE', 'NOTICE.md'):
    _lpath = os.path.join(_spec_dir, _lf)
    if os.path.exists(_lpath):
        datas.append((_lpath, '.'))

# mermaid.js (図表描画、MITライセンス、オフライン同梱) をバンドルに含める
_mermaid_js = os.path.join(_spec_dir, 'assets', 'mermaid.min.js')
if os.path.exists(_mermaid_js):
    datas.append((_mermaid_js, 'assets'))

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

# ══════════════════════════════════════════════════════════
#  バンドル軽量化: macOS版と同じ保持セットの方針を踏襲する。
#  Windowsでは .dll / plugins / qml / translations が対象になる。
# ══════════════════════════════════════════════════════════
import re as _re

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

_DENY_PLUGINDIR = (
    'plugins/sqldrivers', 'plugins/multimedia', 'plugins/sceneparsers',
    'plugins/geometryloaders', 'plugins/renderplugins', 'plugins/designer',
    'plugins/position', 'plugins/sensors', 'plugins/canbus',
    'plugins/texttospeech', 'plugins/virtualkeyboard', 'plugins/assetimporters',
    'plugins/qmltooling', 'plugins/webview',
)

_DENY_TOOL_SUBSTR = (
    'Assistant', 'Designer', 'Linguist',
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
    target_arch=None,
    icon=os.path.join(_spec_dir, '資料箱', 'IMG_1152.ico'),
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
