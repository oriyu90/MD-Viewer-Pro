#!/usr/bin/env bash
# Build and package MD Viewer Pro (macOS).
# Usage: scripts/package_macos.sh [--skip-build]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="$(python3 -c 'import json;print(json.load(open("apps/desktop/tauri.conf.json"))["version"])')"
# 配布名は表示版数（例 26.3.0-beta.3.0 -> beta.3.0）。機械版数は Info.plist に残す。
DISP="$(python3 -c "
import re
v='$VERSION'
m=re.search(r'-(alpha|beta)\\.(.+)$', v)
print(f'{m.group(1)}.{m.group(2)}' if m else v)
")"
APP_NAME="MD Viewer Pro"
BIN="md-viewer-pro"
DIST="$ROOT/dist"
APP="$DIST/$APP_NAME.app"

export PATH="$HOME/.cargo/bin:$PATH"

if [[ "${1:-}" != "--skip-build" ]]; then
  echo "==> cargo build (release)"
  cargo build --release -p md-viewer-pro
fi

echo "==> assembling $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "target/release/$BIN" "$APP/Contents/MacOS/$BIN"
cp "apps/desktop/icons/icon.icns" "$APP/Contents/Resources/icon.icns"
printf 'APPL????' > "$APP/Contents/PkgInfo"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundleDisplayName</key><string>$APP_NAME</string>
  <key>CFBundleIdentifier</key><string>com.oriyu90.mdviewerpro</string>
  <key>CFBundleExecutable</key><string>$BIN</string>
  <key>CFBundleIconFile</key><string>icon.icns</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>${VERSION%%-*}</string>
  <key>CFBundleVersion</key><string>${VERSION%%-*}</string>
  <key>CFBundleGetInfoString</key><string>$VERSION</string>
  <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.productivity</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSSupportsAutomaticGraphicsSwitching</key><true/>
  <key>CFBundleDevelopmentRegion</key><string>ja</string>
  <key>CFBundleLocalizations</key>
  <array><string>ja</string><string>en</string></array>
  <!-- 標準アプリ（既定のアプリ）として選べるよう、書類型を 3 つに分ける。
       Markdown は Owner（既定にできる）/ Editor（編集して保存できる）。
       .txt と YAML は Alternate（他アプリの既定を奪わない）。
       public.plain-text の宣言は Markdown 側だけに置き、.txt は拡張子で区別する。 -->
  <key>CFBundleDocumentTypes</key>
  <array>
    <dict>
      <key>CFBundleTypeName</key><string>Markdown Document</string>
      <key>CFBundleTypeRole</key><string>Editor</string>
      <key>LSHandlerRank</key><string>Owner</string>
      <key>LSItemContentTypes</key>
      <array><string>net.daringfireball.markdown</string><string>public.plain-text</string></array>
      <key>CFBundleTypeExtensions</key>
      <array><string>md</string><string>markdown</string><string>mdown</string><string>mkd</string></array>
    </dict>
    <dict>
      <key>CFBundleTypeName</key><string>Plain Text Document</string>
      <key>CFBundleTypeRole</key><string>Editor</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>LSItemContentTypes</key>
      <array><string>public.plain-text</string></array>
      <key>CFBundleTypeExtensions</key>
      <array><string>txt</string></array>
    </dict>
    <dict>
      <key>CFBundleTypeName</key><string>YAML Document</string>
      <key>CFBundleTypeRole</key><string>Viewer</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>LSItemContentTypes</key>
      <array><string>public.yaml</string><string>public.plain-text</string></array>
      <key>CFBundleTypeExtensions</key>
      <array><string>yml</string><string>yaml</string></array>
    </dict>
  </array>
  <!-- Markdown の UTI を自前で宣言する（旧 Python 版と同じ）。
       macOS 標準の UTI データベースに無い環境でも拡張子 .md を認識させる。 -->
  <key>UTImportedTypeDeclarations</key>
  <array>
    <dict>
      <key>UTTypeIdentifier</key><string>net.daringfireball.markdown</string>
      <key>UTTypeDescription</key><string>Markdown Document</string>
      <key>UTTypeConformsTo</key>
      <array><string>public.plain-text</string><string>public.content</string></array>
      <key>UTTypeTagSpecification</key>
      <dict>
        <key>public.filename-extension</key>
        <array><string>md</string><string>markdown</string></array>
        <key>public.mime-type</key><string>text/markdown</string>
      </dict>
    </dict>
  </array>
</dict>
</plist>
PLIST

echo "==> ad-hoc signing (common-rules: Developer ID 未使用時は ad-hoc)"
codesign --force --deep --sign - "$APP" >/dev/null
codesign --verify --deep --strict "$APP"

# 書類型の宣言を検証する（標準アプリ対応の回帰検出）。
echo "==> verifying Info.plist document types"
plutil -lint "$APP/Contents/Info.plist" >/dev/null
python3 - "$APP/Contents/Info.plist" <<'PY'
import plistlib, sys
p = plistlib.load(open(sys.argv[1], 'rb'))
types = p.get('CFBundleDocumentTypes', [])
utis = {u.get('UTTypeIdentifier') for u in p.get('UTImportedTypeDeclarations', [])}
assert 'net.daringfireball.markdown' in utis, 'Markdown UTI declaration missing'
assert len(types) >= 3, f'expected >=3 document types, got {len(types)}'
md = [t for t in types if 'net.daringfireball.markdown' in t.get('LSItemContentTypes', [])]
assert md and md[0].get('LSHandlerRank') == 'Owner', 'Markdown must be LSHandlerRank Owner'
assert md[0].get('CFBundleTypeRole') == 'Editor', 'Markdown must be CFBundleTypeRole Editor'
txt = [t for t in types if 'txt' in t.get('CFBundleTypeExtensions', [])]
assert txt, 'plain text document type missing'
print(f'    document types={len(types)} utis={sorted(u for u in utis if u)}')
PY

echo "==> DMG"
DMG="$DIST/MDViewerPro-$DISP-macOS.dmg"
STAGE="$DIST/dmg-stage"
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
# --skip-build でも前回の DMG を消さないよう、失敗時はステージを残す（原因調査用）。
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"

echo "==> done"
ls -lh "$DMG"
shasum -a 256 "$DMG"
