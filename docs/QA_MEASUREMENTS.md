# QA measurements — MD Viewer Pro v26.1.1

- 計測日: 2026-11-01 12:57 JST
- 計測機: Apple M3 Ultra / macOS 26.4
- 計測方法: `scripts/measure.sh`（アプリ起動 → JS の `ui_ready` が記録した経過ms、RSS は起動 1.5 秒後にプロセスツリーを合算）
- 入力: 120 見出し・表・コード・数式を含む約 40KB の Markdown

| 指標 | 値 |
|---|---|
| 起動〜UI ready | 1108 ms |
| プロセスツリー RSS（起動 1.5 秒後） | 112 MB |
| 実行ファイル | 8.3 MB (8671312 bytes) |
| .app バンドル | 8 MB |
| DMG | 5 MB (5898109 bytes) |
| DMG SHA-256 | 12fb53cf4520b17ce36983f8a72774bdf173e1ccaef2e6f06cb67b72a38f3b01 |

## 参考: 旧版 v1.5.3（社内記録）

| 指標 | 値 |
|---|---|
| DMG | 約 175 MB |
| Windows Setup.exe | 119 MB |
| 常駐メモリ | 約 300 MB |
| コールド起動（Windows 実機） | 8.5 秒 |
