# 設計書 — MD Viewer Pro v26.0.1

- 版: 1.0（2026-11-01）
- 実装: Rust 2021 / Tauri 2.12 / comrak 0.59 / ammonia 4
- 対象 OS: macOS 11+（検証は macOS 26.4 / Apple Silicon）

---

## 1. 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│ macOS ネイティブ層                                            │
│  NSWindow / メニューバー / Finder 関連付け / 単一インスタンス    │
├─────────────────────────────────────────────────────────────┤
│ Tauri 2 ランタイム（Rust）                                     │
│  commands.rs : UI からの操作を検証してコアへ渡す                 │
│  menu.rs     : ネイティブメニュー                               │
│  state.rs    : 設定・文書・クリップ・フォント・ソケット           │
├─────────────────────────────────────────────────────────────┤
│ mdv-core（GUI 非依存クレート）                                  │
│  doc.rs      : 読み書き・文字コード・上限・原子的保存             │
│  render.rs   : comrak → HTML → ammonia → 見出し/TOC/メタ         │
│  settings.rs : 設定スキーマ・検証・移行・永続化                   │
│  theme.rs    : パレット・アクセント導出                          │
├─────────────────────────────────────────────────────────────┤
│ WKWebView（表示専用）                                          │
│  ui/index.html + app.css + app.js                              │
│  assets/: katex 0.19 / mermaid 11 / highlight.js 11             │
└─────────────────────────────────────────────────────────────┘
```

**境界の原則**: 文書の真実は Rust が持つ。WebView は「与えられた HTML を表示し、
入力イベントを Rust に返す」だけ。WebView からファイルシステムへ直接アクセスさせない。

---

## 2. クレート構成

| パス | 役割 | 依存 |
|---|---|---|
| `crates/mdv-core` | 文書・描画・設定・テーマ | comrak, ammonia, serde, encoding_rs, chardetng |
| `apps/desktop` | Tauri アプリ・コマンド・メニュー | tauri, mdv-core, rfd, open, arboard |
| `ui/` | 表示（HTML/CSS/JS） | なし（ビルド不要の静的アセット） |
| `ui/assets/` | KaTeX / Mermaid / highlight.js | 同梱・オフライン |

フロントエンドに Node/npm は不要。`frontendDist` が `ui/` をそのまま埋め込む。

---

## 3. 文書処理パイプライン

```
open_path(path)
  ├─ メタデータ取得（32MiB 上限）
  ├─ バイナリ判定（先頭 8KiB の NUL）
  ├─ 文字コード: BOM → UTF-8 → chardetng 推定 → 置換（警告を返す）
  ├─ Document { source, generation, kind }
  └─ render_markdown(source, hard_breaks)
        ├─ フロントマター分離（--- 〜 ---、最大 200 行）
        ├─ comrak（table/strikethrough/autolink/tasklist/footnotes/description_lists）
        ├─ AST から見出し収集 → slug（重複は -1, -2）
        ├─ <hN> へ id を注入
        ├─ フロントマター表を先頭に付与
        └─ ammonia で allowlist サニタイズ
              → Rendered { html, headings, title, front_matter, has_math, has_mermaid, plain }
```

### サニタイズ方針（ammonia）

- 許可: 通常の文章タグ + table/thead/tbody/tr/th/td + input[type=checkbox] + del/s/sup/sub/kbd/mark
- 属性: `class`（コード言語）、`id`（見出しアンカー）、`href/title`、`img[src/alt]`、`align`
- 禁止: `script` / `iframe` / `style` 属性 / `on*` / `javascript:` URL
- リンクには `rel="noopener noreferrer"` を自動付与

### 数式・図（WebView 側）

1. Rust は ` ```mermaid ` を `<pre><code class="language-mermaid">` として出力
2. JS が `div.mermaid` に置換し `mermaid.run()`（securityLevel: strict）
3. `renderMathInElement()` が本文テキストノードの `$…$` / `$$…$$` を KaTeX 化
4. highlight.js が `pre code` を色付け
5. 各 `pre` にコピーボタンを付与（Rust の `copy_text` を呼ぶ）

---

## 4. IPC（Tauri コマンド）

| コマンド | 引数 | 返り値 | 備考 |
|---|---|---|---|
| `bootstrap` | — | 設定・パレット・フォント・テーマ・パス | 起動時に 1 回 |
| `open_path` | path | 文書 + Rendered | 最近開いた文件を更新 |
| `pick_file` / `pick_save` | suggested | path | rfd（ネイティブダイアログ） |
| `render` | source, hardBreaks | Rendered | 編集のデバウンスごと |
| `save_document` | path, source | path | 原子的保存（tmp→rename） |
| `save_text` | path, content | — | HTML 書き出し |
| `save_settings` | settings | Bootstrap | 検証して保存 |
| `copy_text` | text | — | arboard |
| `open_external` | url | — | http/https/mailto のみ |
| `reveal_path` | path | — | Finder で表示 |
| `clips_get` / `clip_add` / `clip_remove` | — | 配列 | 上限 200 件 / 5000 字 |
| `fonts_list` / `font_add` / `font_remove` | — | 配列 | `~/.mdviewer/fonts` |
| `themes_list` / `open_themes_dir` | — | — | `~/.mdviewer/themes/*.json` |
| `print_page` | — | — | macOS: NSPrintOperation |
| `selftest_report` | payload | — | `--selftest` 専用 |

**公開範囲**: `capabilities/default.json` は `core:default` のみ。
プラグイン（fs/shell/dialog）は使わず、必要な操作は上表のコマンドに閉じる。

---

## 5. 設定スキーマ（v2）

```json
{
  "version": 2,
  "lang": "ja",
  "theme": "dark",
  "accent_color": "",
  "font_family": "Helvetica Neue",
  "font_size": 16,
  "scale_idx": 2,
  "page_mode": "free",
  "margins": [20, 20, 20, 20],
  "hard_breaks": true,
  "show_toc": true,
  "show_clip": false,
  "bold_mode": false,
  "recent": [],
  "last_dir": "",
  "last_pdf_dir": "",
  "pdf_embed_images": true,
  "window": { "width": 1280, "height": 900, "x": null, "y": null, "maximized": false },
  "window_geometry": ""
}
```

- 旧 `~/.mdviewer/settings.json` と同一ディレクトリ・同一キー名を維持（無いキーは既定値）
- 破損時は `.bak` へ退避して既定値で起動
- 保存は tmp + fsync + rename

---

## 6. UI 構成

```
#app
 ├─ #main-toolbar      戻る / 閲覧・編集 / フリー・A4 / 余白 / スケール / 目次 / クリップ / 設定 / PDF
 ├─ #fmt-toolbar       編集時のみ: B I ~~ code / H1 H2 H3 本文 / リスト 番号 チェック 引用 水平線 / リンク 画像 表
 ├─ #workspace
 │   ├─ #toc-panel     見出し一覧（クリックでスクロール、現在位置をハイライト）
 │   ├─ #editor-pane   行番号 + textarea（編集時のみ）
 │   ├─ #preview-pane  #doc（Markdown 表示）
 │   └─ #clip-panel    フレーズ集（右スライド）
 └─ dialogs            詳細設定 / 余白設定 / クリップ追加
```

- 配色は Rust の `Palette` を CSS 変数へ流し込む（`--bg`, `--accent`, …）
- テーマ色は `effective_accent` / `effective_heading` で背景に応じて補正
- 文字サイズ = `font_size × SCALES[scale_idx]`
- A4 時は 210mm 幅・`--m{ t,r,b,l }` の余白でページを表現し、`@page` で印刷

---

## 7. プラットフォーム統合（macOS）

| 機能 | 実装 |
|---|---|
| ネイティブメニュー | `tauri::menu`（アプリ/ファイル/編集/表示/ウインドウ） |
| ファイル関連付け | Info.plist `CFBundleDocumentTypes`（md/markdown/txt/yml/yaml） |
| Finder から開く | `RunEvent::Opened` → `open-path` イベント |
| 単一インスタンス | `~/.mdviewer/instance.sock`（UnixListener）。2 個目はパスを送って終了 |
| ウィンドウ状態 | 終了時にサイズ・位置・最大化を保存、次回復元（設定に保存） |
| 印刷 / PDF | `WebviewWindow::print()`（macOS の印刷ダイアログ） |
| 外観 | `defaults read -g AppleInterfaceStyle` でダーク判定 |

---

## 8. ビルドと配布

```
scripts/package_macos.sh
  cargo build --release -p md-viewer-pro
  → dist/MD Viewer Pro.app（Info.plist / icon.icns / 実行ファイル）
  → codesign --force --deep --sign -（ad-hoc）
  → codesign --verify --deep --strict
  → hdiutil で MDViewerPro-26.0.1-macOS.dmg
```

- `bundle.active=false`（Tauri CLI を使わず、独自スクリプトで .app を組む）
- 署名は common rules 8 に従い ad-hoc。Developer ID 取得時に差し替え

---

## 9. 既知の制約（v26.0.1）

1. PDF 書き出しは macOS の印刷ダイアログ経由（「PDF として保存」を選ぶ）。直接保存は将来対応
2. MD 編集の WYSIWYG は非対応（ソース + プレビュー）
3. ページ内検索は本文の DOM を走査する簡易実装（数式・図の内部は対象外）
4. Windows / Linux の配布ビルドは未検証（設計は共通、Linux は WebKitGTK 依存）
5. クラウドアップロード（Google Drive / OneDrive）は非対応
6. 数式・Mermaid は WebView 側 JS に依存（オフライン同梱）
