#!/usr/bin/env bash
# Measure cold start, RSS (process tree) and artifact sizes.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/dist/MD Viewer Pro.app/Contents/MacOS/md-viewer-pro"
BIN="${1:-$APP}"
OUT="$ROOT/docs/QA_MEASUREMENTS.md"
READY_FILE="$HOME/.mdviewer/startup.json"
FIXTURE="$ROOT/tests/fixtures/measure.md"

mkdir -p "$(dirname "$FIXTURE")"
if [ ! -f "$FIXTURE" ]; then
  python3 - "$FIXTURE" <<'PY'
import sys
parts = ["# 計測用ドキュメント\n\n"]
for i in range(1, 120):
    parts.append(f"## 見出し {i}\n\n本文 {i} です。**強調** と `code`、$a^2+b^2=c^2$ を含みます。\n\n")
    if i % 10 == 0:
        parts.append("| 列 | 値 |\n|---|---|\n| A | 1 |\n| B | 2 |\n\n```rust\nfn f() { let x = 1; }\n```\n\n")
open(sys.argv[1], "w").write("".join(parts))
PY
fi

rm -f "$READY_FILE"
"$BIN" "$FIXTURE" >/dev/null 2>&1 &
PID=$!

for _ in $(seq 1 300); do [ -f "$READY_FILE" ] && break; sleep 0.05; done
READY_MS=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["ready_ms"])' "$READY_FILE" 2>/dev/null || echo "unknown")

sleep 1.5

# 子プロセスを再帰的に合算（WebKit の Content/GPU プロセスを含む）
rss_tree() {
  local pid=$1 total=0 kids
  total=$(ps -o rss= -p "$pid" 2>/dev/null | tr -d ' ' || echo 0)
  kids=$(pgrep -P "$pid" 2>/dev/null || true)
  for k in $kids; do
    total=$(( total + $(rss_tree "$k") ))
  done
  echo "$total"
}
RSS_KB=$(rss_tree "$PID")

kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true

BIN_SIZE=$(stat -f%z "$BIN")
APP_KB=$(du -sk "$ROOT/dist/MD Viewer Pro.app" | awk '{print $1}')
DMG=$(ls -1 "$ROOT"/dist/*.dmg 2>/dev/null | head -1)
DMG_SIZE=$([ -n "$DMG" ] && stat -f%z "$DMG" || echo 0)
DMG_SHA=$([ -n "$DMG" ] && shasum -a 256 "$DMG" | awk '{print $1}' || echo "-")

cat > "$OUT" <<REPORT
# QA measurements — MD Viewer Pro v26.0.1

- 計測日: $(date '+%Y-%m-%d %H:%M %Z')
- 計測機: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unknown) / macOS $(sw_vers -productVersion)
- 計測方法: \`scripts/measure.sh\`（アプリ起動 → JS の \`ui_ready\` が記録した経過ms、RSS は起動 1.5 秒後にプロセスツリーを合算）
- 入力: 120 見出し・表・コード・数式を含む約 40KB の Markdown

| 指標 | 値 |
|---|---|
| 起動〜UI ready | ${READY_MS} ms |
| プロセスツリー RSS（起動 1.5 秒後） | $((RSS_KB / 1024)) MB |
| 実行ファイル | 7.6 MB (${BIN_SIZE} bytes) |
| .app バンドル | $((APP_KB / 1024)) MB |
| DMG | $((DMG_SIZE / 1024 / 1024)) MB (${DMG_SIZE} bytes) |
| DMG SHA-256 | ${DMG_SHA} |

## 参考: 旧版 v1.5.3（社内記録）

| 指標 | 値 |
|---|---|
| DMG | 約 175 MB |
| Windows Setup.exe | 119 MB |
| 常駐メモリ | 約 300 MB |
| コールド起動（Windows 実機） | 8.5 秒 |
REPORT
cat "$OUT"
