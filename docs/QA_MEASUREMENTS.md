# QA measurements — MD Viewer Pro v26.0.1

- 計測日: 2026-11-01 02:02 JST
- 計測機: Apple M3 Ultra / macOS 26.4
- 計測方法: `scripts/measure.sh`（アプリ起動 → JS の `ui_ready` が記録した経過ms、RSS は起動 1.5 秒後にプロセスツリーを合算）
- 入力: 120 見出し・表・コード・数式を含む約 40KB の Markdown

| 指標 | 値 |
|---|---|
| 起動〜UI ready | 952 ms |
| プロセスツリー RSS（起動 1.5 秒後） | 112 MB |
| 実行ファイル | 7.6 MB (8029760 bytes) |
| .app バンドル | 8 MB |
| DMG | 5 MB (5566284 bytes) |
| DMG SHA-256 | 18eec56367da7cc76a1916f89a32627b28debd5edb008d2ae9ce7225a0ce2076 |

## 参考: 旧版 v1.5.3（社内記録）

| 指標 | 値 |
|---|---|
| DMG | 約 175 MB |
| Windows Setup.exe | 119 MB |
| 常駐メモリ | 約 300 MB |
| コールド起動（Windows 実機） | 8.5 秒 |
