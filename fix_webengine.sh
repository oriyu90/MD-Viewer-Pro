#!/bin/bash
# PyInstaller が生成した MDViewerPro.app の QtWebEngineCore.framework 構造を修正するスクリプト
set -e

APP="dist/MDViewerPro.app"
FW_BASE="$APP/Contents/Frameworks/PySide6/Qt/lib/QtWebEngineCore.framework"

echo "[fix] quarantine 属性を削除..."
xattr -cr "$APP" 2>/dev/null || true

echo "[fix] QtWebEngineProcess.app のパスを確認・修正..."
# PyInstaller が生成した .app 内での QtWebEngineProcess の場所を探す
HELPER_APP=$(find "$APP" -name "QtWebEngineProcess.app" -maxdepth 10 2>/dev/null | head -1)

if [ -z "$HELPER_APP" ]; then
    echo "[warn] QtWebEngineProcess.app が見つかりません。スキップします。"
else
    echo "[fix] 発見: $HELPER_APP"
    # Helpers/ ディレクトリへの symlink を確保
    if [ -d "$FW_BASE" ]; then
        HELPERS_DIR="$FW_BASE/Helpers"
        mkdir -p "$HELPERS_DIR"
        if [ ! -e "$HELPERS_DIR/QtWebEngineProcess.app" ]; then
            cp -R "$HELPER_APP" "$HELPERS_DIR/"
            echo "[fix] Helpers/ にコピー完了"
        fi
    fi
fi

echo "[fix] WebEngine Resources を確認..."
if [ -d "$FW_BASE" ]; then
    RES_SRC="$FW_BASE/Resources"
    # Versions/A/Resources がない場合は作成
    if [ -d "$FW_BASE/Versions/A" ] && [ ! -d "$FW_BASE/Versions/A/Resources" ]; then
        mkdir -p "$FW_BASE/Versions/A/Resources"
        if [ -d "$RES_SRC" ]; then
            cp -Rn "$RES_SRC/"* "$FW_BASE/Versions/A/Resources/" 2>/dev/null || true
        fi
    fi
fi

echo "[fix] コード署名..."
# dylib/so を署名
find "$APP" \( -name "*.dylib" -o -name "*.so" \) | while read f; do
    codesign --force --sign - "$f" 2>/dev/null || true
done

# QtWebEngineProcess.app を署名
find "$APP" -name "QtWebEngineProcess.app" | while read f; do
    codesign --force --sign - "$f" 2>/dev/null || true
done

# Framework 全体を署名
if [ -d "$FW_BASE" ]; then
    codesign --force --sign - "$FW_BASE" 2>/dev/null || true
fi

# アプリ全体を署名（最後に行う）
codesign --force --deep --sign - "$APP" 2>/dev/null || true

echo "[fix] 完了: $APP"
