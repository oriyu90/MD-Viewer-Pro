# MD Viewer Pro v26.1.0 — Rust / Tauri 2 機能完成版

v26.0.1 で未実装だった機能を補完し、実機の UI スナップショットで表示を検査した版です。

## ダウンロード

- `MDViewerPro-26.1.0-macOS.dmg`（Apple Silicon / macOS 11+・ad-hoc 署名・未公証）

## v26.0.1 からの追加

- **PDF 直接書き出し**: A4 縦/横、余白 (mm)、テーマ（アプリ/ダーク/ライト/プラグイン）、画像有無を指定。
  WKWebView の矩形キャプチャをページ単位で行い、lopdf で 1 つの PDF に結合
- **プラグインテーマ**: `~/.mdviewer/themes/*.json` のパレットを全面適用（必須キー検証・背景輝度で dark 判定）
- **起動ダイアログ**: ファイルを開く / 新規作成 / 説明 / 言語選択
- **複数ウィンドウ**: ウィンドウごとに独立した文書状態
- **Google Drive / OneDrive**: 各サービスのアップロード画面を開く（旧版と同じ）
- **編集の追従スクロール**、**フォント削除 UI**、**テーマ一覧の動的更新**
- **Windows / Linux の CI**（テスト・ビルド・clippy）

## 実測（Apple M3 Ultra / macOS 26.4）

| 指標 | v1.5.3（Python/Qt） | v26.1.0 |
|---|---|---|
| DMG | 約 175 MB | 約 7 MB |
| 実行ファイル | — | 約 9 MB |
| 常駐メモリ（プロセスツリー） | 約 300 MB | 約 115 MB |
| 起動〜UI ready | 数秒 | 約 1.0 秒 |

## 検証

- Rust 単体テスト 27 件 PASS
- 実 WKWebView の E2E（描画・TOC・数式・Mermaid・ハイライト・開く/保存・PDF）PASS
- UI 検査: 閲覧/編集/A4/起動/設定/PDF設定/検索/プラグインテーマを実表示で撮影（`docs/ui/`）

## 既知の制限

- WYSIWYG 編集（contenteditable）は非対応。原文を壊さない「ソース + プレビュー」に統一
- Windows / Linux は CI 検証のみ（配布物は未作成）
- PDF のページ分割はブロック境界で行うため、ページ下部に余白ができることがあります
- サイト（Studio RIZI）の v26.1 掲載は未実施

## ソース

`v26-rust` ブランチ（`docs/PLAN.md` / `DESIGN.md` / ADR / QA / UI_REVIEW）。
