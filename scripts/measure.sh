#!/usr/bin/env bash
# Measure cold start, peak RSS (process tree) and artifact sizes.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/dist/MD Viewer Pro.app/Contents/MacOS/md-viewer-pro"
BIN="${1:-$APP}"
OUT="$ROOT/docs/QA_MEASUREMENTS.md"
TMP="$HOME/.mdviewer/selftest.json"

rm -f "$TMP"
START=$(python3 -c 'import time;print(int(time.time()*1000))')
"$BIN" --selftest >/dev/null 2>&1 &
PID=$!
for _ in $(seq 1 200); do [ -f "$TMP" ] && break; sleep 0.05; done
END=$(python3 -c 'import time;print(int(time.time()*1000))')
READY=$(( END - START - 1200 ))   # セルフテストの発火待ち 1200ms を差し引く

# プロセスツリーの RSS（KiB）
tree_rss() {
  local root=$1 total=0
  local pids
  pids=$(ps -axo pid=,ppid= | awk -v r="$root" '$2==r{print $1}')
  for p in $root $pids; do
    r=$(ps -o rss= -p "$p" 2>/dev/null | tr -d ' ')
    total=$(( total + ${r:-0} ))
  done
  echo $total
}
sleep 1
RSS=$(tree_rss "$PID")
wait "$PID" 2>/dev/null || true

BIN_SIZE=$(stat -f%z "$BIN")
APP_SIZE=$(du -sk "$ROOT/dist/MD Viewer Pro.app" | awk '{print $1}')
DMG=$(ls -1 "$ROOT"/dist/*.dmg 2>/dev/null | head -1)
DMG_SIZE=$([ -n "$DMG" ] && stat -f%z "$DMG" || echo 0)

cat > "$OUT" <<REPORT
# QA measurements — MD Viewer Pro v26.0.1

- 計測日: $(date '+%Y-%m-%d %H:%M %Z')
- 計測機: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unknown) / macOS $(sw_vers -productVersion)
- 計測方法: \`scripts/measure.sh\`（--selftest 起動、起動待ち 1200ms を差し引き）

| 指標 | 値 |
|---|---|
| 起動〜描画完了（推定） | ${READY} ms |
| プロセスツリー RSS（起動 3 秒後） | $((RSS / 1024)) MB |
| 実行ファイル | $((BIN_SIZE / 1024 / 1024)) MB (${BIN_SIZE} bytes) |
| .app バンドル | $((APP_SIZE / 1024)) MB |
| DMG | $((DMG_SIZE / 1024 / 1024)) MB (${DMG_SIZE} bytes) |

## 参考: 旧版 v1.5.3

| 指標 | 値 |
|---|---|
| DMG | 約 175 MB |
| Windows Setup.exe | 119 MB |
| 常駐メモリ | 約 300 MB |
| コールド起動（Windows） | 8.5 秒 |
REPORT
cat "$OUT"
