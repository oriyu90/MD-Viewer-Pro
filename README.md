# MD Viewer Pro

A fast, native-feeling Markdown viewer and editor for macOS, rebuilt in Rust with Tauri 2.

**Version β2.0** (`26.2.0-beta.2.0`) — Rust rewrite (previous line: v1.5.3, Python + PySide6).

[日本語](#日本語) | [English](#english)

---

## 日本語

### 概要

MD Viewer Pro は、Markdown の閲覧・編集・書き出しを行うデスクトップアプリです。
v26.0.1 で Python/PySide6 から **Rust + Tauri 2** へ作り直し、次の点を改善しました。

- 配布物: 約 175MB（DMG）→ **約 8MB**（アプリ本体）
- 常駐メモリ: 約 300MB → **約 150MB**（WebView プロセス込み）
- コールド起動: 8.5 秒 → **1 秒前後**（実機計測は下記）
- 文書の解析・整形・保存・設定をすべて Rust 側で処理

### 主な機能

| 機能 | 説明 |
| --- | --- |
| 閲覧 | GFM（表・タスクリスト・打ち消し・脚注・自動リンク）、シンタックスハイライト、コードのコピーボタン |
| 編集 | **MD編集**（WYSIWYG・プレビューを直接編集）と **TXT編集**（ソース + リアルタイムプレビュー）の2モード + 書式ツールバー |
| 目次 / 検索 | 見出し一覧、クリックでジャンプ、現在位置のハイライト。Cmd+F のページ内検索（ハイライト・前後移動） |
| 数式 | `$…$` / `$$…$$` / `\(…\)` をオフラインで組版（KaTeX 同梱） |
| 図 | ` ```mermaid ` をフローチャート等として描画（オフライン同梱） |
| フロントマター | YAML のメタ情報を表として表示。`.yml` / `.yaml` も閲覧可 |
| 表示 | ダーク / ライト / システム、アクセント色（プリセット + カスタム）、フォント、文字サイズ、5 段階ズーム |
| デザイン | v1.5.3 準拠のフラットなテキストツールバー（72px・区切り線・灰色の選択ブロック・スケールスライダー） |
| レイアウト | フリー / A4 文書（余白設定、印刷 CSS） |
| クリップ | 定型文を右パネルに保存し、ワンクリックでコピー（上限 200 件 / 5000 字） |
| 書き出し | HTML、PDF 直接書き出し（A4・縦/横・余白・テーマ・画像有無を指定して保存） |
| テーマ | ダーク / ライト / システム + `~/.mdviewer/themes/*.json` のプラグインテーマ（パレット全面適用） |
| 多言語 | 日本語 / English / Deutsch / Français / 简体中文 |
| macOS 連携 | ネイティブメニュー、ファイル関連付け、Finder から開く、単一インスタンス、複数ウィンドウ、ウィンドウ状態の復元 |
| 起動 | 起動ダイアログ（ファイルを開く / 新規作成 / 説明）、言語選択 |

### インストール（macOS）

1. `MDViewerPro-26.0.1-macOS.dmg` をダウンロード
2. 開いて **MD Viewer Pro.app** を Applications へドラッグ
3. 初回起動時に警告が出る場合: システム設定 → プライバシーとセキュリティ → 「このまま開く」

> 本アプリは **ad-hoc 署名・未公証** です（Apple Developer Program 未加入のため）。
> 「壊れているため開けません」と出る場合は、Applications へ移動した後に
> `xattr -cr "/Applications/MD Viewer Pro.app"` を実行してから開いてください。

### ソースからビルド

```bash
# 必要条件: Rust 1.80+ / Xcode Command Line Tools / macOS 11+
git clone <this repo>
cd md-viewer-pro-rust
cargo test --workspace
./scripts/package_macos.sh        # dist/MD Viewer Pro.app と DMG を生成
```

フロントエンドの Node/npm は不要です（`ui/` の静的ファイルをそのまま埋め込みます）。

### 既知の制限（v26.0.1）

- MD編集の反映は変更ブロック単位です。複雑な入れ子構造は Turndown の変換結果に依存します
- Windows / Linux 版は未配布です（CI でビルド検証、Linux は WebKitGTK 4.1 が必要）
- Google Drive / OneDrive は各サービスのアップロード画面を開くのみ（自動アップロードはしません）
- 外部画像（`https://…`）は表示のために取得されます（ローカルファイルは取得しません）

### ライセンス

MIT License — Copyright (c) 2026 Yuki_Orita

同梱する第三者ソフトウェアは [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) を参照してください。

---

## English

### Overview

MD Viewer Pro is a desktop Markdown viewer/editor. v26.0.1 is a full rewrite from
Python/PySide6 to **Rust + Tauri 2**, reducing the app bundle from ~175MB to ~8MB,
resident memory from ~300MB to ~150MB (including the WebView process), and cold start
from 8.5s to about 1s.

### Features

GFM rendering with tables, task lists, footnotes and autolinks; syntax highlighting and
copy buttons; source editing with live preview; table of contents; offline KaTeX math and
Mermaid diagrams; YAML front matter; dark/light/system themes with accent colors; font and
zoom controls; free/A4 layouts with margins and print CSS; clipboard phrase panel; HTML and
PDF export; Japanese/English/German/French/Simplified Chinese UI; native menu bar, file
associations, Finder integration, single instance and window restoration on macOS.

### Install (macOS)

Open the DMG, drag **MD Viewer Pro.app** to Applications, then launch it. The app is
**ad-hoc signed and not notarized**; if macOS refuses to open it, run
`xattr -cr "/Applications/MD Viewer Pro.app"` and try again.

### Build

```bash
cargo test --workspace
./scripts/package_macos.sh
```

### Known limitations

PDF export goes through the macOS print dialog ("Save as PDF"). WYSIWYG Markdown editing
is not included; editing is source + preview. Windows/Linux builds and cloud upload are not available in v26.0.1.

### License

MIT License — Copyright (c) 2026 Yuki_Orita. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
