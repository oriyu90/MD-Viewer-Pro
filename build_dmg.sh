#!/bin/bash
# ══════════════════════════════════════════════════════════
#  MD Viewer Pro — 安定版ビルドスクリプト
#  使い方: cd ~/Used_ai/MDviewer && ./build_dmg.sh
# ══════════════════════════════════════════════════════════
set -e

PYTHON="$(dirname "$0")/venv_new/bin/python3"
APP_NAME="MDViewerPro"
DMG_NAME="MDViewerPro-Installer"

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: venv_new が見つかりません。python3 -m venv venv_new && $PYTHON -m pip install pyinstaller pyside6 markdown pygments"
    exit 1
fi

echo "══════════════════════════════════════════"
echo "  MD Viewer Pro ビルド開始"
echo "  Python: $($PYTHON --version)"
echo "══════════════════════════════════════════"

echo "[1/5] 古いビルドを削除..."
rm -rf build dist __pycache__ "${DMG_NAME}.dmg" dmg_tmp

echo "[2/5] .app をビルド中..."
"$PYTHON" -m PyInstaller MDViewerPro.spec --noconfirm
echo "      完了"

echo "[3/5] QtWebEngine フレームワーク構造を修正..."
bash "$(dirname "$0")/fix_webengine.sh"
echo "      完了"

echo "[4/5] DMG を作成中..."
mkdir -p dmg_tmp
cp -R "dist/${APP_NAME}.app" dmg_tmp/
ln -s /Applications dmg_tmp/Applications

hdiutil create \
    -volname "MD Viewer Pro" \
    -srcfolder dmg_tmp \
    -ov -format UDRW \
    "dist/${DMG_NAME}-rw.dmg" >/dev/null

hdiutil convert \
    "dist/${DMG_NAME}-rw.dmg" \
    -format UDZO -imagekey zlib-level=9 \
    -o "${DMG_NAME}.dmg" >/dev/null

rm -f "dist/${DMG_NAME}-rw.dmg"
rm -rf dmg_tmp
echo "      完了"

echo ""
echo "══════════════════════════════════════════"
echo "  ビルド完了!"
echo "  .app  →  ./dist/${APP_NAME}.app"
echo "  .dmg  →  ./${DMG_NAME}.dmg"
echo "══════════════════════════════════════════"
