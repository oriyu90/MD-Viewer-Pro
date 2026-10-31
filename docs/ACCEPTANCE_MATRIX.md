# 受け入れ条件マトリクス — MD Viewer Pro v26.0.1

- 判定日: 2026-11-01
- 検証手段: `cargo test`（26件）/ `--selftest`（実 WebView E2E）/ ブラウザプレビュー / 静的確認
- 状態: PASS / PARTIAL / NOT_TESTED

| AC | 要件 | 検証方法 | 結果 | 証拠 |
|---|---|---|---|---|
| AC-01 | macOS で .app が起動しウィンドウ表示 | `open` / プロセス / selftest | PASS | selftest `ok:true`, プロセス継続 |
| AC-02 | GFM（表・タスク・打ち消し・脚注・自動リンク） | 単体 + selftest | PASS | `gfm_table_and_tasklist`、selftest tables=2 / taskItems=2 |
| AC-03 | 見出し ID と TOC | 単体 + selftest | PASS | `headings_get_stable_ids_and_toc`、selftest tocItems |
| AC-04 | フロントマター表示・本文から除外 | 単体 | PASS | `front_matter_is_extracted_and_hidden` |
| AC-05 | コードハイライト・コピー | selftest + プレビュー | PASS | selftest highlighted=2 |
| AC-06 | 数式（KaTeX）・Mermaid（オフライン） | selftest | PASS | katex=1, mermaidSvg=1 |
| AC-07 | 開く・保存・名前を付けて保存 | 単体 + selftest | PASS | `save_is_atomic_and_normalizes_crlf`、selftest savedBytes/savedHasAppend |
| AC-08 | 設定の永続化 | 単体 + コード | PARTIAL | 設定の保存/読込/移行は単体で PASS。UI ダイアログ経由の E2E は未実施 |
| AC-09 | 5 言語 UI | 抽出 + 照合 | PASS | 148 キー × 5、欠落 0 |
| AC-10 | テーマ・アクセント | 単体 + プレビュー | PARTIAL | `theme` の単体 PASS。ライト/システムの実機目視は未 |
| AC-11 | HTML 書き出し | コード | NOT_TESTED | 保存ダイアログが必要なため自動化せず |
| AC-12 | PDF 書き出し | コード | NOT_TESTED | macOS 印刷ダイアログ経由。GUI 実機未確認 |
| AC-13 | クリップ（保存・コピー・削除） | コード | PARTIAL | 実装済み。E2E 未実施 |
| AC-14 | D&D・関連付け・単一インスタンス | コード | PARTIAL | 実装済み。GUI 実機未確認（画面が取得できない環境のため） |
| AC-15 | DMG・ad-hoc 署名・手順書 | 実行 | PASS | `codesign --verify --deep --strict` 成功、README 記載 |
| AC-16 | 軽量性（サイズ・起動・メモリ） | 実測 | PASS | `docs/QA_MEASUREMENTS.md` |

## 未確認の理由

- 実行環境のディスプレイがスリープ状態で、macOS の画面キャプチャが黒画像になるため、
  GUI の目視確認（印刷ダイアログ、D&D、関連付け）は実施できなかった。
- 代替として、実際の WKWebView 上で動く `--selftest`（描画・TOC・数式・図・保存往復）と、
  同一 HTML/CSS/JS をブラウザで表示するプレビューで UI を検証した。
