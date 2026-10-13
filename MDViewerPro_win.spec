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

# ウィンドウアイコン (setWindowIcon 用)。ICO形式。
_favicon = os.path.join(_spec_dir, 'favicon.ico')
if os.path.exists(_favicon):
    datas.append((_favicon, 'assets'))

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
#  注意: WindowsのDLL名は Qt6* (例 Qt6Pdf.dll) のため、素名に加えて
#  Qt6 付きも列挙する。Qt6Quick / Qt6Qml 本体は除外しないこと。
# ══════════════════════════════════════════════════════════
import re as _re
import os as _os

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
    'Qt63D', 'Qt6Graphs', 'Qt6DataVisualization',
    'Qt6Location', 'Qt6Bluetooth', 'Qt6Nfc', 'Qt6Sensors',
    'Qt6Serial', 'Qt6Sql', 'Qt6Test', 'Qt6Scxml',
    'Qt6RemoteObjects', 'Qt6Designer', 'Qt6Help',
    'Qt6Pdf', 'Qt6WebSockets', 'Qt6NetworkAuth',
    'Qt6Quick3D', 'Qt6QuickControls2', 'Qt6QuickDialogs2',
    'Qt6TextToSpeech', 'Qt6VirtualKeyboard',
]
_deny_re = _re.compile(r'(?:^|/)(?:' + '|'.join(_DENY_PREFIX) + r')')

# アプリ表示言語 (ja/en/de/fr/zh) 以外の Qt/WebEngine 翻訳は除外する。
# QFileDialog 等の標準文言に使う qtbase/qt、WebEngine文言の qtwebengine、
# Chromiumロケールの locale パックだけを残す (英語は原文のため .qm 不要、
# WebEngine の en-US パックのみ残す)。
_KEEP_QM = {
    'qtbase_ja.qm', 'qtbase_de.qm', 'qtbase_fr.qm',
    'qtbase_zh_CN.qm', 'qtbase_zh_TW.qm',
    'qt_ja.qm', 'qt_de.qm', 'qt_fr.qm', 'qt_zh_CN.qm', 'qt_zh_TW.qm',
    'qtwebengine_ja.qm', 'qtwebengine_de.qm', 'qtwebengine_fr.qm',
    'qtwebengine_zh_CN.qm', 'qtwebengine_zh_TW.qm',
    'qt_help_ja.qm', 'qt_help_de.qm', 'qt_help_fr.qm',
    'qt_help_zh_CN.qm', 'qt_help_zh_TW.qm',
    'ja.pak', 'de.pak', 'fr.pak', 'zh-CN.pak', 'zh-TW.pak',
    'en-US.pak', 'en-GB.pak',
}

# WebEngine のデバッグ・開発者ツール用リソース (製品動作に不要)。
# devtools_resources.pak はリモートデバッグ時のみ使用する。
_DENY_RES_SUBSTR = (
    '.debug.pak', '.debug.bin', 'devtools_resources',
)

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
    # 拡張子付きの basename で比較する (qmlls.exe 等の素通り防止)。
    if _os.path.splitext(d.rsplit('/', 1)[-1])[0] in _DENY_TOOL_BASE:
        return False
    if '/translations/' in d:
        base = d.rsplit('/', 1)[-1]
        if base.endswith(('.qm', '.pak')) and base not in _KEEP_QM:
            return False
    if any(t in d for t in _DENY_RES_SUBSTR):
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
