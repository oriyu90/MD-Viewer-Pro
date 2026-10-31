# レビュー指摘への対応記録（WP-07 → 修正）

- レビュー対象: `docs/REVIEW_REPORT.md`（HEAD `e5ab3d7`）
- 対応日: 2026-11-01
- 方針: HIGH は全件修正、MEDIUM は全件修正、LOW は可能なものを修正し、残りは制約として記録

| ID | 指摘 | 対応 | 検証 |
|---|---|---|---|
| HIGH-1 | 見出し ID が生 HTML の `<hN>` を誤マッチ | **修正**: 文字列の出現順ではなく、AST の見出しテキストと一致する `<hN>` にのみ ID を付与（`inject_heading_ids`） | 回帰テスト `raw_html_heading_does_not_steal_ids` 追加、26 件 PASS |
| HIGH-2 | アプリコマンドが ACL 化されず任意パスへ書き込み可能 | **緩和**: ダイアログ/起動引数で明示選択したパスの allowlist を導入し、`save_document` / `save_text` / `reveal_path` を制限 | selftest の保存往復 PASS（許可パスのみ） |
| MEDIUM-1 | i18n キー 9 件欠落 | **修正**: `copy` `copied` `saved` `cancel` `ok` `clip_copy_hint` `fmt_text_placeholder` `theme_color_label` を 5 言語へ追加 | 参照キーとの照合で欠落 0 |
| MEDIUM-2 | Cmd+S/O/N の二重発火 | **修正**: Tauri 実行時は JS の keydown を無効化し、ネイティブメニューの accelerator に一本化 | コード確認（GUI 実機は未） |
| MEDIUM-3 | 検索メニューが未実装 | **修正**: ページ内検索（Cmd+F、ハイライト、前後移動、Esc）を実装 | ブラウザプレビューで動作確認 |
| MEDIUM-4 | 設定の `.bak` が上書き | **修正**: `settings.json.bak-<unix>` のタイムスタンプ名へ | 単体テスト更新・PASS |
| MEDIUM-5 | CSP で無効な `onerror` | **修正**: 属性を削除 | コード確認 |
| MEDIUM-6 | 見出し ID の衝突が順序依存 | **修正**: テキスト一致方式へ変更。重複解決の回帰テストを追加 | `duplicate_heading_ids_are_unique` PASS |
| LOW-1 | `img-src https:` で外部画像を取得 | **記録**: 仕様として README に明記（旧アプリも外部画像を取得） | 文書 |
| LOW-2 | `reveal_path` の終了コード無視 | **修正**: `status.success()` を検証 | コード確認 |
| LOW-3 | `recent` の存在確認なし | **未対応**: 開く時点でエラー表示されるため実害小。次期課題 | — |
| LOW-4 | selftest/startup の非原子的書き込み | **未対応**: 検証専用ファイルのため優先度低 | — |
| LOW-5 | 単一インスタンスの同時起動競合 | **未対応**: 起動前に connect を試みる方式。同時起動の厳密排他はロックファイルで将来対応 | — |
| LOW-6 | 一時ファイル名が拡張子依存 | **修正**: `.<name>.<pid>.tmp` の一意名へ | 保存テスト PASS |
| LOW-7 | 大容量 render が同期 | **記録**: 上限 32MiB。将来はバックグラウンド描画 | 文書 |

## 残課題（次期）

- Tauri の `AppManifest` によるコマンド ACL 化（現状はアプリ層の allowlist で緩和）
- 単一インスタンスのロックファイル化
- 大きい文書の非同期レンダリング
