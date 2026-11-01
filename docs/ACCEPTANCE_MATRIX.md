# 受け入れ条件マトリクス — MD Viewer Pro v26.1.0

- 判定日: 2026-11-01
- 検証手段: `cargo test`（27件）/ `--selftest`（実 WKWebView E2E）/ `--screenshot`（実表示の画像検査）/ ヘッドレス PDF 書き出し / 静的確認
- 状態: PASS / PARTIAL / NOT_TESTED

| AC | 要件 | 検証方法 | 結果 | 証拠 |
|---|---|---|---|---|
| AC-01 | macOS で .app が起動しウィンドウ表示 | 起動・プロセス・selftest | PASS | selftest `ok:true`、複数ウィンドウ生成確認 |
| AC-02 | GFM（表・タスク・打ち消し・脚注・自動リンク） | 単体 + selftest | PASS | tables=2 / taskItems=2 |
| AC-03 | 見出し ID と TOC | 単体 + selftest | PASS | tocItems=2 |
| AC-04 | フロントマター表示・本文から除外 | 単体 | PASS | `front_matter_is_extracted_and_hidden` |
| AC-05 | コードハイライト・コピー | selftest + 画像 | PASS | highlighted=2、コピーボタン表示 |
| AC-06 | 数式（KaTeX）・Mermaid（オフライン） | selftest | PASS | katex=1 / mermaidSvg=1 |
| AC-07 | 開く・保存（原子的） | 単体 + selftest | PASS | savedBytes / savedHasAppend |
| AC-08 | 設定の永続化 | 単体 + 実機 | PASS | PDF/テーマ/余白設定の反映を実測 |
| AC-09 | 5 言語 UI | 抽出 + 照合 | PASS | 160 キー × 5、欠落 0 |
| AC-10 | テーマ・アクセント | 単体 + 画像 | PASS | ダーク/ライト/プラグイン（Solarized）を撮影 |
| AC-11 | HTML 書き出し | コード | PARTIAL | 出力経路は実装済み。ダイアログ操作の自動化は未実施 |
| AC-12 | PDF 直接書き出し | ヘッドレス実行 | PASS | A4 15 ページ / 87KB、縦横・余白・テーマ・画像有無を実測 |
| AC-13 | クリップ（保存・コピー・削除） | 画像 + コード | PASS | 3 件表示・削除ボタン・上限 200/5000 |
| AC-14 | D&D・関連付け・単一インスタンス | 実機 | PARTIAL | 単一インスタンス転送は実測。D&D は未実施 |
| AC-15 | DMG・ad-hoc 署名・手順書 | 実行 | PASS | `codesign --verify` 成功 |
| AC-16 | 軽量性 | 実測 | PASS | `QA_MEASUREMENTS.md` |
| AC-17 | 起動ダイアログ | 画像 | PASS | 3 択 + 言語選択を撮影 |
| AC-18 | プラグインテーマ | 実機 | PASS | 全パレット置換を撮影 |
| AC-19 | 複数ウィンドウ | 実機 | PASS | 2 ウィンドウ生成を CGWindowList で確認 |
| AC-20 | 追従スクロール | コード + 画像 | PARTIAL | 実装済み。長文での体感確認は未実施 |
| AC-21 | Google Drive / OneDrive | コード | PASS | 各サービスの URL を開く（旧版同様） |
| AC-22 | レスポンシブ UI | 画像 | PARTIAL | 720/900/1080px の CSS を実装。狭幅の実画面撮影は未実施 |
| AC-23 | Windows / Linux ビルド | CI 定義 | PARTIAL | GitHub Actions を追加。実ランナーでの結果は未取得 |
| AC-24 | WYSIWYG 編集 | — | NOT_IMPLEMENTED | 原文を壊さない設計判断により非対応（ADR-0005） |

## 未確認の理由

- ディスプレイがスリープ状態のため `screencapture` は黒画像になる。代わりに
  `WKWebView.takeSnapshot` による実表示キャプチャで UI を検査した。
- Windows / Linux はこの Mac 上で実行できないため、CI 定義とドキュメントのみ。
- WYSIWYG は旧版の contenteditable + HTML→MD 逆変換を再導入しない方針（ADR-0002/0005）。
