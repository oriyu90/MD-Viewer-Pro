# Release notes

## v26.2.0 — MD編集 / TXT編集の分離

v1.5.3 と同じ 3 モード構成に戻した版。

- **MD編集**: プレビューを直接編集（contenteditable）。書式ボタンは DOM に適用
- **TXT編集**: 左ソース + 右プレビュー（従来どおり）
- 保存・モード切替時は**変更ブロックだけ**を Markdown に戻して原文へ反映
  - comrak の sourcepos で行範囲を特定し、Turndown(GFM) で変換
  - 数式は KaTeX の annotation から TeX を復元、Mermaid はフェンスに戻す
  - 未編集ブロックはそのまま保持（全文の書き換えをしない）
- ツールバーに 3 モードを表示（閲覧 / MD編集 / TXT編集）

v26.1.1 — v1.5.3 デザイン整合

UI を v1.5.3 の見た目に寄せた版。旧版の紹介動画から実画面を抽出し、配色・寸法・操作感を比較して調整。

- ツールバーを 72px のフラットなテキストバーに変更（角丸ボタン・青い主要ボタンを廃止）
- グループ間の縦区切り線、選択項目は灰色のブロック表示（v1.5.3 と同じ）
- スケールはセレクトからスライダー + % 表示に変更
- 書式ツールバーを 52px のフラット表示に統一
- エディタの行番号を廃止（v1.5.3 の TXT編集と同じ）
- 目次パネルは編集時のみ表示（閲覧時は全幅表示）
- ウィンドウタイトルに文書名を表示

v26.1.0 — 機能完成版（pre-release）

v26.0.1 で未実装だった機能を補完し、UI を実機スナップショットで検査した版。

### 追加・改善

- **PDF 直接書き出し**: A4 縦/横、余白（mm）、テーマ（アプリ/ダーク/ライト/プラグイン）、画像有無を指定し、A4 ページに分割して 1 つの PDF に保存（WKWebView の矩形キャプチャ + lopdf 結合）
- **プラグインテーマ**: `~/.mdviewer/themes/*.json` のパレットを全面適用（必須キー検証、背景輝度で dark 判定）
- **起動ダイアログ**: ファイルを開く / 新規作成 / 説明 / 言語選択。ファイル引数がある場合は非表示
- **複数ウィンドウ**: 新規ウィンドウ（`Cmd+Shift+N`）。ウィンドウごとに文書状態を保持
- **Google Drive / OneDrive**: メニューから各サービスのアップロード画面を開く（旧版と同じ挙動）
- **編集の追従スクロール**: エディタのスクロール位置に合わせてプレビューが追従（設定で ON/OFF）
- **フォント削除 UI**、**テーマ一覧の動的更新**
- **Windows / Linux の CI**（GitHub Actions でテスト・リリースビルド・clippy）

### 実測（Apple M3 Ultra / macOS 26.4）

| 指標 | v1.5.3 | v26.1.0 |
|---|---|---|
| DMG | 約 175 MB | 約 7 MB |
| 常駐 RSS | 約 300 MB | 約 115 MB |
| 起動〜UI ready | 数秒 | 約 1.0 秒 |

### 既知の制限

- WYSIWYG 編集は非対応（ソース + プレビュー）。原文破壊を避けるための設計判断
- Windows / Linux は CI 検証のみで配布物は未作成
- サイト（Studio RIZI）の v26.1 掲載は未実施

v26.0.1 — Rust rewrite (pre-release)

First release of the Rust/Tauri 2 line. The v1.5.x Python application remains the
previous stable line.

### Highlights

- Full rewrite of the document engine in Rust (`mdv-core`): parsing, sanitization,
  settings, themes and file I/O no longer depend on Python or Qt.
- Native macOS window, menu bar, file associations, Finder "Open With", single
  instance and window-state restoration.
- Offline KaTeX math and Mermaid diagrams, bundled with the app.
- In-page search (Cmd+F) with highlight and next/previous navigation.
- Source-of-truth editing: the Markdown source is never reconstructed from HTML, so
  saving can no longer rewrite or damage the document.
- Ad-hoc signed, not notarized (same policy as v1.5.x).
- Security hardening: HTML is sanitized in Rust (ammonia) and file writes are restricted to
  paths the user explicitly chose in a save/open dialog.

### Measured (Apple Silicon, macOS 26.4)

| Metric | v1.5.3 (Python/Qt) | v26.0.1 (Rust/Tauri) |
|---|---|---|
| App binary | — (PyInstaller bundle) | 7.7 MB |
| DMG | ~175 MB | see asset |
| Cold start | ~8.5 s (Windows), several seconds on macOS | ~1 s |
| Peak RSS (main process) | ~300 MB total | ~44 MB (main) + WebView |

### Known limitations

- PDF export uses the macOS print dialog ("Save as PDF").
- WYSIWYG Markdown editing is replaced by source + preview.
- Windows/Linux builds are not shipped in this release.
- Google Drive / OneDrive upload is not implemented.

### Upgrade notes

Settings are read from the existing `~/.mdviewer/settings.json` (unknown keys are
ignored, missing keys use defaults). Clipboard phrases are read from
`~/.mdviewer/clipboard.json`. The Python app can still be used side by side.
