# MD Viewer Pro v26.0.1 — Rust / Tauri 2 版（pre-release）

Python/PySide6 実装（v1.5.3）を **Rust + Tauri 2** で全面的に書き直した最初のリリースです。
文書の解析・整形・保存・設定はすべて Rust 側で処理し、表示だけを macOS の WKWebView に任せます。

## ダウンロード

- `MDViewerPro-26.0.1-macOS.dmg`（Apple Silicon / macOS 11+）

> ad-hoc 署名・未公証です。初回起動時に Gatekeeper の警告が出ます。
> Applications へ移動した後、必要に応じて `xattr -cr "/Applications/MD Viewer Pro.app"` を実行してください。

## 軽量化（実測 / Apple M3 Ultra・macOS 26.4）

| 指標 | v1.5.3（Python/Qt） | v26.0.1 |
|---|---|---|
| DMG | 約 175 MB | **5.3 MB** |
| 実行ファイル | — | 7.6 MB |
| 常駐メモリ（プロセスツリー） | 約 300 MB | **112 MB** |
| 起動〜UI ready | 数秒（Windows 実機 8.5 秒） | **952 ms** |

## 主な機能

- GFM 表示（表・タスクリスト・打ち消し・脚注・自動リンク）、コードハイライト、コピー
- 目次パネル、Cmd+F のページ内検索
- オフラインの KaTeX 数式・Mermaid 図
- ソース編集 + リアルタイムプレビュー（書式ツールバー、行番号）
- YAML フロントマター、A4 文書 / フリー表示、余白設定
- ダーク / ライト / システム、アクセント色、フォント、文字サイズ、5 段階ズーム
- クリップボード（フレーズ集、200 件 / 5000 字）
- HTML 書き出し、PDF 書き出し（macOS 印刷ダイアログ経由）
- 日本語 / English / Deutsch / Français / 简体中文
- macOS ネイティブメニュー、ファイル関連付け、Finder から開く、単一インスタンス、ウィンドウ状態復元

## 既知の制限

- PDF 書き出しは macOS の印刷ダイアログから「PDF として保存」を選ぶ方式です
  （WKWebView の直接 PDF 化は、ページ分割が正しく行えないことを実機検証で確認したため見送りました）
- MD 編集の WYSIWYG は非対応です。原文を壊さない「ソース + プレビュー」に統一しました
- Windows / Linux 版は未配布です
- Google Drive / OneDrive アップロードは非対応です

## ソース

このリポジトリの `v26-rust` ブランチ（Rust workspace / Tauri / UI / テスト / 設計資料）。

- 設計: `docs/DESIGN.md`、`docs/adr/`（6 件）
- 検証: `docs/QA_REPORT.md`、`docs/ACCEPTANCE_MATRIX.md`、`docs/REVIEW_RESPONSE.md`
