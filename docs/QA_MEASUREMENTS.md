# QA measurements — MD Viewer Pro v26.2.0

- 計測日: 2026-11-01 13:52 JST
- 計測機: Apple M3 Ultra / macOS 26.4
- 計測方法: `scripts/measure.sh`（アプリ起動 → JS の `ui_ready` が記録した経過ms、RSS は起動 1.5 秒後にプロセスツリーを合算）
- 入力: 120 見出し・表・コード・数式を含む約 40KB の Markdown

| 指標 | 値 |
|---|---|
| 起動〜UI ready | 1229 ms |
| プロセスツリー RSS（起動 1.5 秒後） | 112 MB |
| 実行ファイル | 8.3 MB (8687728 bytes) |
| .app バンドル | 8 MB |
| DMG | 5 MB (5911263 bytes) |
| DMG SHA-256 | 22d69413daea312705c1e559834ebd70dc9be4fb213d35962b18a3bb692be842 |

## 参考: 旧版 v1.5.3（社内記録）

| 指標 | 値 |
|---|---|
| DMG | 約 175 MB |
| Windows Setup.exe | 119 MB |
| 常駐メモリ | 約 300 MB |
| コールド起動（Windows 実機） | 8.5 秒 |
