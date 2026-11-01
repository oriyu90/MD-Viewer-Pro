# 残機能スペック（旧アプリ v1.5.3 からの抽出 / Rust版未実装の補完）

- 対象: `reference/main_v1.5.3.py`（7,915行、PySide6）
- 目的: Rust版に未実装・部分実装の機能について、実装者がそのまま作れる粒度の仕様をまとめる。
- 関連: 画面全体の仕様は `docs/spec/UI_SPEC.md`（既存）を正とし、本書はその補完。重複する記述は UI_SPEC.md を参照する。
- 表記: 出典は `関数名 (行番号)`。行番号は `reference/main_v1.5.3.py` の該当箇所の開始行。
- 凡例: **観測事実** = ソースから直接確認した内容 / **再現仕様** = 旧版の挙動として再現すべき内容 / **Rust案** = 実装の提案 / **推定・未確認** = 断定できない点。
- 既存ファイル（ソース・他docs）は変更していない。

---

## 0. Rust版の現状（比較の前提）

観測（Rust側、2026-11-01時点のワークツリー）:

| 機能 | Rust版の現状 | 根拠 |
|---|---|---|
| クリップ保存・上限 | 実装済み（`MAX_CLIPS=200` / `MAX_CLIP_LEN=5000`、`clip_add`/`clip_remove`） | `apps/desktop/src/commands.rs:325-351`, `state.rs:9-10` |
| フォント追加・削除 | コマンドあり（`font_add`/`font_remove`/`fonts_list`） | `apps/desktop/src/main.rs:104-106`, `commands.rs:385` |
| テーマ一覧 | `themes_list` / `palette_for_theme` あり | `main.rs:107,114`, `commands.rs:434` |
| ウィンドウ状態保存 | `persist_window_state` あり（`window_geometry` は "wxh+x+y" 移行用に保持） | `main.rs:85`, `commands.rs:586`, `settings.rs:53-54` |
| 起動時メタ | `ui_ready` が `startup.json` を書く（計測用、起動ダイアログではない） | `commands.rs:555-563` |
| 起動ダイアログ | **未実装**（本書 §1） | — |
| PDF書き出し | メニュー項目のみ（`export-pdf`）。`print_page` は `window.print()` 経由 | `menu.rs:47`, `commands.rs` `print_page` |
| Google Drive / OneDrive | **未確認**（Rust側に該当コマンドを検出できず） | grep 結果 0 件 |
| 単一インスタンス | **未確認**（Rust側に該当コードを検出できず） | — |

以下、章ごとに記述する。

---

## 1. StartupDialog（起動ダイアログ）

### 観測事実
- クラス定義 `StartupDialog` (3525)。アクション定数 `ACTION_OPEN="open"` / `ACTION_NEW="new"` / `ACTION_GUIDE="guide"` (3526-3528)。
- 起動経路 `MDViewerPro._startup_open` (7479)。
  - 先に `self._initial_file`（コマンドライン引数 / macOS の Apple Events `QFileOpenEvent`）が有効ならダイアログを**出さず**そのファイルを開く (7481-7486)。
  - それ以外は `StartupDialog(self, I18N[self.lang], self.lang)` を `exec()` (7489-7491)。
  - 結果の処理: `ACTION_NEW`→`file_new()`、`ACTION_OPEN`→`QFileDialog.getOpenFileName`（キャンセル時は `_set_sample()`+`_refresh_view()`）、`ACTION_GUIDE`→`_open_guide()`、その他→`file_new()`（フォールバック） (7512-7520)。
  - ダイアログで言語が変わった場合 (`new_lang != self.lang`) は本体の言語を更新し、メニュー・書式ツールバー・テーマを再構築 (7493-7500)。
- ウィジェット構成 (3530-3583):
  - 幅 `setMinimumWidth(360)`。`QVBoxLayout`、余白 `(32, 28, 32, 28)`、間隔 16。
  - タイトル `startup_title`（中央揃え、pointSize 20、太字）。
  - ヒント `startup_hint`（中央揃え）。
  - 間隔 8。
  - ボタン「ファイルを開く」`startup_open`（高さ固定 44）。
  - ボタン「新規作成」`startup_new`（高さ固定 44）。
  - 言語行: ラベル `startup_language`（既定 "Language"）＋ `QComboBox`（`LANGS` のキー＝表示名、既定選択は `current_lang` に対応する項目）。
  - ボタン「説明を開く」`startup_guide`（高さ固定 44）。
- 言語変更 `_on_lang_changed` (3585): コンボ選択で即座に全ラベル・ボタン・ウィンドウタイトルを選択言語へ差し替え（ダイアログを閉じない）。
- 結果の確定 `_on_open` / `_on_new` / `_on_guide` (3600-3611): 押下時点のコンボ言語を `selected_lang` に保存し、`action` を設定して `accept()`。
- `reject` (3616): Esc / ×（閉じる）は `action` 未設定なら **新規作成扱い** (`ACTION_NEW`) として `accept` 相当で閉じる（`super().accept()` を呼ぶ）。
- フォーカス離脱 `changeEvent` / `_check_deactivation` (3623-3649): ダイアログ外（本体ウィンドウ等）がアクティブになったら **新規作成扱い**で閉じる。ただし ComboBox ポップアップ等の一時的非アクティブを除外するため **200ms 待ってから判定**。自身・子ポップアップがアクティブなら何もしない。
- 最近使ったファイル・サンプル表示: **観測されず**。本版ダイアログにはボタン・一覧は無い。

### 再現すべき仕様
1. 起動時、CLI引数またはファイル関連付けで開かれていなければダイアログを表示。引数で開いた場合は表示しない。
2. 3択（ファイルを開く / 新規作成 / 説明を開く）＋言語選択。
3. 閉じる操作（×・Esc・フォーカス喪失）はすべて「新規作成」として扱う（ファイルを開く/説明を開くの意図を持たない限り空の新規文書になる）。
4. 言語コンボの変更はダイアログ内で即時反映し、確定時に本体の言語へ反映。
5. 「ファイルを開く」でキャンセルした場合はサンプル文書を表示（新規空文書ではない点に注意）。

### Rust案
- Tauri フロントエンド側のモーダル（HTML/CSS）で実装。`window` の起動直後に表示を判定する。
- 結果は `invoke("startup_choice", {action, lang})` 等でバックエンドへ渡す。
- フォーカス離脱の 200ms 判定はフロントの `window` の `blur` + `setTimeout(200)` で近似可能。Esc/× を「new」にマップ。
- 「最近使ったファイル」は旧版に無いため、**追加しない**（要件外）。

### 推定・未確認
- 「説明を開く」`_open_guide` (7836) の中身（サンプルか内蔵ガイドか）は本書の範囲外で未精査。
- macOS の `QFileOpenEvent` 経由の起動順序（`_initial_file` の設定タイミング）は `MDApplication.event` (1172) の観測に基づく推定。

---

## 2. PDF書き出し設定ダイアログ・PDF生成

### 2-A 設定ダイアログ `PdfExportDialog`（3651-3731）

観測事実:
- コンストラクタ引数: `page_mode, a4_margins, t, embed_images=True, current_theme="dark", plugin_themes=None, b5_margins=None` (3652-3653)。`b5_margins` は**未使用**（引数のみ）。
- 最小幅 320。ウィンドウタイトル `pdf_settings_title`（既定 "PDF書き出し設定"）。
- 項目（上から）:
  1. **方向** `pdf_orientation`: `QComboBox`（縦向き `pdf_portrait` / 横向き `pdf_landscape`）。既定は縦 (3664-3670)。
  2. **余白設定 (mm)** `margin_title`: `QFormLayout` に 上/右/下/左 の `QSpinBox`（範囲 0〜100、suffix " mm"、初期値は `a4_margins`）(3672-3686)。
  3. **画像を含める** `pdf_embed_images`: チェックボックス `pdf_embed_images_label`（既定 `embed_images`）(3688-3693)。
  4. **スタイルモード** `pdf_style_mode`: `QComboBox`。項目は「ダーク(`dark`)」「ライト(`light`)」＋プラグインテーマ名（テーマ名そのまま）。初期選択は `current_theme`（該当なしは先頭）(3695-3708)。
  5. OK / キャンセル (`QDialogButtonBox`) (3710-3714)。
- `get_settings` (3722-3731): 戻り値 `("A4", landscape, (top,right,bottom,left), embed_images, pdf_theme)`。**用紙は常に "A4"**（選択UIなし）。
- 既定値の出所: `a4_margins` = `(20,20,20,20)` (3850)。`pdf_embed_images` は `_pdf_embed_images`（設定値、既定 True）。

### 2-B 書き出し処理 `_export_pdf` (7266-7452)

観測事実（処理順）:
1. `_save_buf()` で編集内容を確定。失敗なら `capture_error` 警告で中止 (7267-7269)。
2. `PdfExportDialog` を表示。キャンセルで終了 (7270-7280)。
3. 設定を `_pdf_embed_images` に保存し `_save_app_settings()`（7282-7284）。
4. 保存先 `QFileDialog.getSaveFileName`（初期フォルダ `_last_pdf_dir`、フィルタ `PDF (*.pdf)`）。空なら中止。拡張子が `.pdf` でなければ付与。`_last_pdf_dir` を更新して保存 (7286-7298)。
5. `QPageLayout` を生成: 用紙 **A4 固定**、向きは設定値、余白は `QMarginsF(l, t, r, b)`、単位 mm (7300-7309)。
6. **パレット決定** (7317-7345): `dark`→`DARK_PALETTE`、`light`→`LIGHT_PALETTE`、プラグイン名→`_plugin_themes[name]`、それ以外→DARK。欠けたキーは DARK で補完。`accent_color` が有効なら accent/heading を `_effective_accent` / `_effective_heading` で上書き（表示と同一の強調色にする）。
7. **HTML生成**: `self._palette` を一時的に `pdf_palette` へ差し替えて `_build_md_html(self._content_text, editable=False, strip_images=not embed_images)` を実行し、`finally` で元に戻す (7352-7355)。
   - `embed_images=False` のとき画像を **削除**（`strip_images`）。
8. **オフスクリーン View**: 表示中の `_preview_web` は**使わず**、`QWebEngineView` を新規作成して `self` の子にする（不可視・レイアウト非追加）(7371-7384)。背景色は `pdf_palette["bg"]`。
9. 状態機械 `_pdf_state`: `"loading"` → `"printing"` → `"done"`（7389 以降）。
   - `loadFinished` → `_do_print`（`ok` 偽ならエラー表示して終了）。
   - `_do_print`: `pdfPrintingFinished` に `_on_pdf_done` を接続。HTML に `_mdvMermaidReady` が含まれる場合は `_wait_mermaid_then` で描画完了を待ってから `printToPdf(path, layout)`、無ければ即 `printToPdf`。
   - `_on_pdf_done(path, ok)`: 成功なら `pdf_success`、失敗なら `pdf_error` を表示。後始末 `_cleanup_pdf_view`（シグナル切断・`deleteLater`・参照解除）。
10. **タイムアウト**: `QTimer.singleShot(20000, ...)`。20秒以内にロード完了しなければ `pdf_error` を出して破棄 (7450)。
11. 本体の表示（`_preview_web`）・スクロール・カーソルには**一切触れない**（独立Viewにした理由がコメントに明記、7373-7376）。

### 2-C 再現すべき仕様
- 用紙 A4 固定、縦/横、余白は mm で指定（既定 20mm 四辺）。
- 画像埋め込み OFF の場合は画像を出力から除去。
- テーマはダーク/ライト/プラグインから選択。アクセント色は表示と同じ規則で反映。
- 表示画面と独立した描画経路を使い、表示状態を壊さない。
- 完了/失敗を通知し、20秒でタイムアウト。
- 設定（方向・画像埋め込み・保存先フォルダ）は次回に引き継ぐ。

### 2-D Rust案
- PDF生成は Tauri では WebView の印刷 API に依存（`print_page` は `window.print()`、macOS のみ実装の分岐あり）。**ヘッドレスに PDF を直接書き出す API は Tauri に標準では無い**ため、以下のいずれかを選ぶ:
  - (a) 非表示の専用 WebviewWindow に PDF 用 HTML を読み込み、`print` → 保存（プラットフォーム差あり）。
  - (b) Rust 側で HTML→PDF（例: `printpdf` 等）を実装（品質・日本語フォント対応が課題）。
  - 推奨は (a)。旧版の「独立 View」思想を Tauri の隠し WebviewWindow で再現する。
- 設定ダイアログは Tauri フロント側モーダルで実装。`page_mode`/`b5_margins` は**Rust版では不要**（旧版でも b5 は未使用）。
- 設定の保存先は `settings.rs` の `last_pdf_dir` / `pdf_embed_images`（既存フィールド）を流用。

### 2-E 推定・未確認
- `_wait_mermaid_then` (7249) の内部待機ロジックは未精査（描画完了判定の詳細は推定）。
- 「用紙が A4 固定」は `PdfExportDialog.get_settings` の `page = "A4"` から確定。ただし `_export_pdf` 内の `QPageSize(A4)` と一致。B5 は**未実装**（`b5_margins` 引数のみ残存）。
- `_build_md_html` の `strip_images` が画像をどう除去するか（`alt` 残し等）は未精査。

---

## 3. プラグインテーマ（`~/.mdviewer/themes`）

### 観測事実
- 保存先 `PLUGIN_DIR = ~/.mdviewer/themes` (66)。
- 読み込み `load_plugin_themes` (1203-1223):
  - ディレクトリが無ければ作成し、サンプル `_write_example_theme()` を書き出して空を返す (1205-1212)。
  - `*.json` を glob して順に読む (1213)。
  - テーマ名 `name` は JSON の `"name"` キー、無ければファイル名（拡張子除去）(1216)。
  - パレットは `_PALETTE_REQUIRED_KEYS`（= `DARK_PALETTE` の全キー、定義 157）**全てが揃っている場合のみ**採用 (1218-1220)。
  - 読み込み・パース失敗は黙って無視 (1221-1222)。
- 必須キー = `DARK_PALETTE` のキー一覧（113-134 行目）。`_PALETTE_REQUIRED_KEYS` は `list(DARK_PALETTE.keys())`。
- サンプル `_write_example_theme` (1226-1247) が書く内容（"Solarized Dark"）:
  ```json
  {
    "name": "Solarized Dark",
    "bg": "#002b36", "bg2": "#073642", "bg3": "#073642",
    "border": "#586e75", "text": "#839496", "text_dim": "#586e75",
    "accent": "#268bd2", "heading": "#93a1a1",
    "toolbar": "#002b36", "btn": "#073642", "btn_hover": "#586e75",
    "btn_active_bg": "#839496", "btn_active_fg": "#002b36",
    "select": "#073642", "code_fg": "#dc322f",
    "row_even": "#073642", "sep": "#586e75",
    "copy_btn_bg": "rgba(0,43,54,0.85)", "copy_btn_fg": "#93a1a1"
  }
  ```
  ファイル名は `solarized_dark.json`。`ensure_ascii=False, indent=2`。
- **色形式**: サンプルは `#rrggbb` に加え `rgba(...)` を含む（`copy_btn_bg`）。`#rrggbb` 以外を弾く検証は**旧版の `load_plugin_themes` には無い**（必須キーの存在のみ検証）。
- **dark判定**: テーマ単体での dark 判定は無い。適用時に `_hex_is_dark(bg)`（2897-2908、知覚輝度 `0.299R+0.587G+0.114B < 128` で暗色）を**背景色で**判定して使う（アクセント補正・PDF背景の決定、7322-7335 / 5811 以降）。
- **適用方法**: テーマ全体のパレット置換（`_resolve_palette` 5777-5809）。`current_theme` がプラグイン名なら `_plugin_themes[name]` を基底として使い、欠けたキーは DARK で補完。その上で `accent_color`（ユーザー指定）が有効なら `accent`/`heading` のみ上書き。
  - つまり「パレット置換」が基本で、「アクセントのみ変更」は設定の `accent_color` の機能（テーマ側ではない）。
- 設定画面（SettingsDialog）でのテーマ選択: `current_theme` を選ぶ。PDF書き出しのスタイル候補にも同じテーマ名が並ぶ（2-A）。

### 再現すべき仕様
1. `~/.mdviewer/themes/*.json` を起動時に読み込む。ディレクトリが無ければ作ってサンプルを置く。
2. `name` 省略時はファイル名（拡張子除去）。
3. 必須キーが全部揃わないテーマは**無視**（エラー表示なし）。
4. 適用はパレット全置換。欠損キーは DARK 既定で補完。アクセント設定があれば accent/heading を上書き。
5. 暗色判定は背景色の輝度（<128 で暗色）。

### Rust案
- 既存の `themes_list` / `palette_for_theme` / `open_themes_dir` (commands.rs) を流用し、**必須キーの完全性チェック**と「欠損時は無視」を `theme.rs` で揃える（現状を確認のうえ整合）。
- 色の検証は `#rrggbb` と `rgba()` の両方を許容する（旧サンプル互換）。不正値のCSS注入を防ぐため、`settings.rs` の `_ACCENT_RE` 相当の検証を色全般に拡張するかは要判断。
- dark 判定は `hex_is_dark` 相当（輝度式）を `theme.rs` に置く。`rgba` の背景は alpha を無視して RGB で判定する案（推定）。

### 推定・未確認
- `_PALETTE_REQUIRED_KEYS` が `DARK_PALETTE` の全キー（現在 20 個前後）になる点は観測。ただし旧版では**サンプルに無いキーは1つもなく**、サンプルは全キーを満たす前提。
- `rgba(...)` の `copy_btn_bg` を含むテーマが旧版で実際に CSS 適用されたかは未確認（値は文字列としてそのまま渡される可能性が高い）。

---

## 4. Google Drive / OneDrive 連携

### 観測事実
- メニュー（ファイル）から呼ばれる:
  - `_upload_gdrive` (7073-7079): `_save_buf()` → ファイル名を取得（`current_file_path` の basename、無ければ `unsaved_file` 文言）→ `QMessageBox.information` で `gdrive_msg` を `{fname}` 置換して表示 → `webbrowser.open("https://drive.google.com/drive/my-drive")`。
  - `_upload_onedrive` (7081-7087): 同様。`onedrive_msg` を表示 → `webbrowser.open("https://onedrive.live.com")`。
- 表示文言（ja）: `gdrive_msg` = `"ファイル: {fname}\n\nGoogle Drive を開きます。\n"` (233)、`onedrive_msg` = `"ファイル: {fname}\n\nOneDrive を開きます。\n"` (235)。
  - en: `"File: {fname}\n\nOpening Google Drive.\n"`（363）、`"File: {fname}\n\nOpening OneDrive.\n"`（365）。
- ファイル名の扱い: **アップロードはしない**。ブラウザで開くだけ。名前は表示メッセージにのみ使用。未保存時は `unsaved_file` 文言。
- ダイアログのタイトルは `"Google Drive"` / `"OneDrive"` 固定（7076, 7084）。
- 実際のアップロード処理・API 呼び出し・認証は**存在しない**。

### 再現すべき仕様
1. メニュー項目選択 → 先に保存バッファ確定 → 案内メッセージ（ファイル名入り）→ OK 後に既定ブラウザで各サービスのトップを開く。
2. ファイル自体は送信しない。ユーザーが手動でアップロードする前提。
3. 未保存時はファイル名の代わりに「未保存」相当の文言を出す。

### Rust案
- メニュー項目 `gdrive`/`onedrive` を追加（現状 `menu.rs` に該当なし）。
- ハンドラで `save_buf` 相当の確定 → メッセージ表示（ダイアログ）→ `open::that(url)`（既に `open` クレートを使用、`open_themes_dir` 参照）。
- URL は上記2つを定数化。

### 推定・未確認
- 文言の正確な翻訳は他言語（de/fr/zh）も同様に存在するが、本書では ja/en のみ転記。
- 「未保存」時のメッセージ文字列（`unsaved_file`）の実値は未確認（キー名のみ観測）。

---

## 5. TXT編集の追従スクロールと編集行ハイライト

### 観測事実
- 同期の発火: `self._md_editor.cursorPositionChanged.connect(self._on_txt_cursor_moved)` (4025)。
- ハンドラ `_on_txt_cursor_moved` (6974-6980):
  - `edit_mode != "txt"` または `_preview_web` 未生成なら何もしない。
  - 基準は **カーソルの論理行番号** `textCursor().blockNumber()`（0始まり）。
  - `window._mdvHighlightLine(line)` を JS 実行。
- 同期ハイライト JS `_line_sync_js` (5465-5488):
  - プレビュー内の `[data-src-line]` 要素を走査。`data-src-line <= line` の**最後**の要素を `target` にする（行番号より前で最も近いブロック）。
  - 既存の `.mdv-line-hl` を外し、`target` に `.mdv-line-hl` を付与。
  - `target` の矩形が画面外（`top<0` または `bottom>innerHeight`）なら `scrollIntoView({behavior:"smooth", block:"center"})`。画面内なら**スクロールしない**。
- ハイライトの見た目: `.mdv-line-hl{background:rgba(255,60,60,.16)!important;...}` (5701)。
- `data-src-line` の付与: `_tag_src_lines` (5422) が `block_starts` からブロック開始行を付与。`_split_source_blocks` (5378) で分割。
- 初回表示: `_refresh_view` で `sync_lines = (edit_mode == "txt")` を渡し HTML を生成 (6047-6057)。
- 閲覧→TXT 切替時のアンカー: `_editor_anchor` (6288)・`_scroll_editor_to_anchor` (6317)・`_js_restore_anchor` (6259) で見出し/ブロック基準の位置を引き継ぐ。

### 再現すべき仕様
1. トリガー: **TXT編集内のカーソル移動全般**（`cursorPositionChanged`。入力・クリック・矢印キーすべて）。
2. 基準: カーソルの**論理行番号**（0始まり）。
3. 対応: プレビュー側で「行番号以下の最後のブロック」を探し、そこにハイライト（赤系の淡い背景）。
4. スクロール: 対象が**画面外に出ている時だけ**中央へスムーズスクロール。画面内なら動かさない（ユーザーの視点を乱さない）。
5. モード切替時は見出し/ブロック単位のアンカーで位置を引き継ぐ。

### Rust案
- フロントのテキストエディタ（CodeMirror 等／現行の「ソース+プレビュー」）の `selectionchange`/カーソル移動イベントで、カーソル行 N を取得。
- プレビュー DOM の `data-src-line` 属性を付与（レンダラ `render.rs` 側で原行番号をブロックに付ける）。
- 同じ「N 以下で最後のブロック」ロジックを JS で実装。画面外判定は `getBoundingClientRect` で同様。
- ハイライトクラスを付与・剥がし。

### 推定・未確認
- 「行番号以下で最後」は、ブロックが行番号順に並ぶ前提（`break` で打ち切り）。並びが乱れる入力では誤動作の可能性（推定）。
- 同期は**エディタ→プレビューの一方向のみ**。プレビューのクリックでエディタを動かす逆方向は旧版に見当たらない（未確認、`_on_toc_item_clicked` 6951 は目次→プレビュー）。
- 閲覧モードでの同期は無効（`sync_lines` が TXT のみ）。

---

## 6. レスポンシブUI

### 観測事実
- 幅区分 `_get_ui_scale_cat` (4400-4421): `w>=1100`→large、`>=780`→medium、`>=620`→small、それ未満→xsmall。
- 寸法表 `_UI_SIZE_TABLE` (4412-4421)（**ボタン余白 `btn_pad`/`fmt_pad` は左右 px**。実際の最小幅は `min_w + btn_pad*2`）:

  | 区分 | 幅 | tb_fs | btn_pad | fmt_fs | fmt_pad | lbl_fs | min_w | slider_w | val_w |
  |---|---|---|---|---|---|---|---|---|---|
  | large | ≥1100 | 17 | 16 | 15 | 13 | 15 | 44 | 120 | 48 |
  | medium | ≥780 | 14 | 11 | 13 | 9 | 13 | 28 | 92 | 40 |
  | small | ≥620 | 12 | 6 | 11 | 5 | 11 | 26 | 64 | 36 |
  | xsmall | <620 | 10 | 3 | 10 | 3 | 10 | 20 | 44 | 30 |

- ツールバー高さ `_apply_responsive_style` (4423-4446):
  - large: `TB_H=72` / `FMT_H=52`
  - medium: 58 / 44
  - small: 46 / 36
  - xsmall: 40 / 32
- 区分が変わったときだけ再適用（`_last_ui_scale_cat` で差分判定、4428-4430）。
- 「`min_w` はスタイルシートの min-width、実文字は `PianoBtn` が個別に詰める」(4402-4407 コメント)。`PianoBtn` の `_fit_text` (3798) が文字を縮めて枠内に収める。`set_fit_metrics` (3756) で基準px・パディング・最小ヒント幅を受け取る。
- リサイズ: `resizeEvent` (4387) が `_resize_timer` を起動（デバウンス）。目次/クリップの幅も同時に追従 (6511, 6551)。
- アスペクト連動の側方空白: UI_SPEC.md §1 を参照（重複のため本書では省略）。
- 短縮表示: **ボタンのラベル文字の縮小（`_fit_text`）が主手段**。ラベルそのものを省略・アイコン化する記述は確認できず。

### 再現すべき仕様
1. 幅4段階で文字サイズ・パディング・ツールバー高さを切り替える（表の値）。
2. ボタン文字は枠幅に合わせて縮小（省略記号ではなく**フォントサイズ縮小**）。
3. ツールバー高さは段階ごとに固定。

### Rust案
- CSS のメディアクエリ（`@media (min-width:1100px)` 等）で4段階を再現。`--tb-fs` 等の CSS 変数に表の値を入れる。
- ボタン文字縮小は `font-size` を `ResizeObserver` で計算、または CSS `clamp()` で近似。
- ツールバー高さは `header { height: var(--tb-h) }`。

### 推定・未確認
- `_fit_text` (3798) の縮小アルゴリズム（段階刻み・下限）は本書では未精査。
- 狭幅での「ラベル省略」（…表示）の有無は未確認（`_fit_text` の内部次第）。

---

## 7. MD編集（contenteditable）— 参考情報（Rust版では置換済み）

Rust版は「ソース+プレビュー」に置換済み。以下は**参考**としての動作差分の整理。

### 観測事実
- MD編集の有効化: `_mode_available` (6017-6026): 読み取り専用ファイル (`_readonly_file`) は不可、`doc_kind=="yaml"` は MD 編集不可。
- DOM 編集: プレビュー WebView 内の `.wrap` に `contenteditable="true" spellcheck="false"` (5710-5711) を付与。`editable` 時のみ。
- 書式 JS `_md_edit_fmt_js` (4636-): `window._mdvNormalize`（execCommand が生成する不正な `<p>` 内 `<ol>/<ul>` を修復、4642 以降）等の関数群を注入。
- 変更通知: `ContentBridge.contentChanged` → `_on_md_content_changed` (6069-6080)。HTML→Markdown 変換 `_html_to_markdown` (5766) → `_content_text` 更新 → dirty 化 → 目次再構築。
- 保存経路: `_save_buf` (6985-6991) で MD モードは `_flush_md_buf()` を呼ぶ。`_flush_md_buf` (6199-) は**入力の 400ms 遅延を待ち合わせて同期取得**する（取りこぼし防止）。戻り値 `ok`/`empty`/`failed` を区別。
- 変換 `_HTML2MD` (1459-1777) / `_html_to_md` (1778)。

### 既知の制約（観測・コメントより）
- ブラウザ側の変更通知は入力後 400ms 遅れて届く → 保存直前は同期取得が必須（コメント 6200-6206）。
- contenteditable の DOM 正規化が不完全（リストの入れ子崩れ）→ `_mdvNormalize` で修復（4642 以降のコメント）。
- HTML→Markdown 変換は**可逆ではない**（構文の揺れ・改行の扱い）。`_html_to_md` の `hard_breaks` 設定に依存。

### Rust版との差分（参考）
- Rust 版は「ソース（テキスト）+プレビュー（読取専用）」。contenteditable による WYSIWYG 編集は**採用しない**のが前提。
- したがって §7 の DOM 変換・同期の複雑さは**再実装不要**。書式ボタンは「ソース挿入（`**`・`#`・リスト等の記号挿入）」へ置換する案。

---

## 8. クリップボード（フレーズ集）

### 観測事実
- 保存先 `~/.mdviewer/clipboard.json`（`_clipboard_path` 929-935、`CLIPBOARD_FILE` 定数 85-86）。
- 上限: `MAX_CLIPS=200`（件数）、`MAX_CLIP_LEN=5000`（1件の文字数）、`MAX_CLIP_FILE_BYTES=1MB`（ファイルサイズ、読み込み時に超えたら空扱い）(88-90)。
- 正規化 `_normalize_clip_text` (938-952): 非文字列は `""`、改行を `\n` に統一、NUL 除去、前後空白除去、上限で切り詰め。
- 読み込み `load_clips` (955-980): 非リスト・破損・巨大ファイルは空。上限件数で打ち切り。
- 保存 `save_clips` (982-1024): **原子的書き込み**（同フォルダの一時ファイル → `fsync` → `os.replace`）。失敗時は既存ファイルを維持して False。
- 追加 `_on_clip_add` (6719-6770):
  - 件数が `MAX_CLIPS` に達していれば `clip_limit_msg` を警告して終了（6721-6727）。
  - 追加ダイアログ `ClipAddDialog`（3180-3232）: プレーンテキスト専用エディタ `PlainPasteEdit`（貼付は `insertFromMimeData` で text のみ、3132-3149）。空は警告 `clip_empty_warning`。
  - 原文が `MAX_CLIP_LEN` を超えたら `clip_too_long` を案内してから切り詰め (6751-6758)。
  - 追加後、上限超過は**古いものから落とす**（`self._clips[-MAX_CLIPS:]`、6764-6767）。
- 削除 `_on_clip_delete` (6772-6806): 削除ボタン → `QMessageBox.question`（Yes/No）で `clip_delete_msg` を表示（フレーズ本文を120文字で省略）→ Yes で削除・保存。
- コピー `_ClipCard.mousePressEvent` (3166-3178): **左クリックで `_copy_fn(self._clip_text)` を呼ぶ**（ClipboardBridge 経由）。コピーは**プレーンテキスト固定**。
- 表示: 一覧は80文字で省略 `_clip_preview_text` (6598)、カードごとに `_ClipCard` (3151)。

### 再現すべき仕様
1. 件数200・1件5000字・ファイル1MB の上限。
2. 追加は**プレーンテキスト**のみ。貼り付けのリッチ書式は除去。
3. 上限到達時は追加不可（警告）。上限超過の自動追加は古い順に落とす（※ 追加ダイアログ側は上限到達で拒否、関数 `_on_clip_add` の後段は保険）。
4. 削除は確認ダイアログ後のみ。
5. クリックでコピー（プレーンテキスト）。
6. 保存は原子的、破損・巨大ファイルは空で起動。

### Rust案
- **既に実装済み**（`clip_add` は trim + 重複排除 + 先頭挿入 + truncate(200) 、`clip_remove`）。差分:
  - 旧版は「追加時に末尾へ、上限超過で古い先頭を落とす」（`append` + `[-MAX:]`）。Rust 版は「先頭挿入・重複削除（`retain`）」。**挙動が異なる**ため、仕様統一が必要（要判断、下記 §10）。
  - 旧版は上限到達で**追加を拒否**（警告）。Rust 版は黙って切り詰め。ここも統一要。
- 削除確認ダイアログは Rust 版で未確認 → フロントで確認ダイアログを追加（推奨）。
- コピーは `arboard`（commands.rs 288）でプレーンテキスト。現状と一致。

### 推定・未確認
- 旧版で「上限到達時に追加ダイアログを開く前に拒否」(6721) と「ダイアログ後の後段で切り詰める保険」の2段は、どちらが実際の振る舞いかは **拒否が先に効く**（推定）。
- `clip_limit_msg` 等の翻訳文字列は I18N に存在（例: ja "保存できるフレーズは最大 {n} 件です。" 、en "You can save up to {n} phrases." 、454/584 付近）。

---

## 9. その他

### 9-A フォント削除UI
- 観測: 設定ダイアログ `SettingsDialog` にフォント追加/削除ボタン。`_on_add_font` (3441) → `add_user_font`、`_on_remove_font` (3456) → `remove_user_font`。
- 削除の挙動 `remove_user_font` (1080-1104): 登録解除（`removeApplicationFont`）→ **ファイルを削除**（`os.remove`）→ 関連ファミリ名を `_USER_FONTS` から除去。**システム標準フォントは対象外**（`_USER_FONTS` に無いので False を返す）。
- 追加 `add_user_font` (1061-1078): `~/.mdviewer/fonts/` にコピー → 登録。読めないファイルは取り込まず削除。
- 対象拡張子 `_FONT_EXTS = (.ttf,.otf,.ttc,.otc)` (1019)。
- 起動時 `load_user_fonts` (1047) が `FONT_DIR` を全登録。`MDApplication.__init__` (1106) で**ウィンドウ生成前に**呼ぶ（QFontDatabase の制約）。
- Rust 版: `font_add`/`font_remove`/`fonts_list` が既にある（main.rs:104-106）。**差分の確認が必要**（削除で実ファイルを消すか、確認ダイアログの有無）。

### 9-B ウィンドウ状態復元
- 保存: `_save_app_settings` (7017) が `saveGeometry()` を Base64 化して `window_geometry` に保存。
- 復元: `__init__` 内 (3912-3917) で `restoreGeometry`。
- 他に保存される UI 状態: `show_toc`、`show_clip`（7017-7033）。
- Rust 版: `persist_window_state` (commands.rs:586) で実装済み（`window_geometry` は "wxh+x+y" 形式の移行用フィールド、settings.rs:53）。**形式の差（Qt の Base64 バイナリ vs 文字列）に注意**。新形式で保存する方針で良い（移行対象は文字列形式のみ）。

### 9-C 単一インスタンス
- 観測: **旧版は単一インスタンス制御を実装していない**。`MDApplication` は複数ウィンドウを前提（`new_window` 1118）。`_on_window_closed` で全閉じ時に `quit`（1127-1132）。
- ファイルを開く経路は macOS の `QFileOpenEvent` (1172-1190): 既存ウィンドウが内容ありなら**新規ウィンドウで開く**、無ければそのウィンドウで開く。
- Dock アイコン再表示時 `ApplicationActivated` で可視ウィンドウが無ければ復帰 (1191-1200)。
- Dock メニュー「New Window」(1134-1170)。
- **結論: 単一インスタンスは旧版にも無い。Rust 版でも不要（推定）。**

### 9-D 関連付け（ファイルタイプ登録）
- 観測: 旧版はコード上でファイル関連付けを登録していない。**macOS の `QFileOpenEvent` を受けるのみ**（1172）。関連付けは OS/パッケージ側（PySide6 アプリの配布設定）の責務。
- `OPEN_FILTER` (93-94): `*.md *.markdown *.txt *.yml *.yaml`。`YAML_EXTS` (96)。
- Rust 版: Tauri 側の `bundle.fileAssociations`（`tauri.conf.json`）で定義する必要あり。**未確認**（本書の範囲外、設定ファイル未調査）。

### 推定・未確認
- Windows/Linux での関連付け・単一インスタンス挙動は本書では未検証（旧版のコードは macOS 寄り）。
- Rust 版の `tauri.conf.json` の fileAssociations の有無は未確認。

---

## 10. 実装優先度

| 優先度 | 機能 | 理由・備考 |
|---|---|---|
| **Must** | §2 PDF書き出し（設定+生成） | 旧版の主要出力経路。Rust版は未実装（メニューのみ）。 |
| **Must** | §1 起動ダイアログ | 初回体験の要。CLI起動でスキップする条件を含めて再現。 |
| **Must** | §5 TXT追従スクロール・行ハイライト | 編集体験の核。`data-src-line` 付与が前提。 |
| **Should** | §3 プラグインテーマ（完全性検証・dark判定） | 既存 `themes_list` の整合確認。必須キー検証を揃える。 |
| **Should** | §8 クリップ上限・追加/削除の挙動統一 | 既存実装との差（先頭挿入 vs 末尾追加、拒否 vs 切り詰め）の決定が必要。 |
| **Should** | §4 Google Drive / OneDrive | 文言・URL・ファイル名表示。実装は小さい。 |
| **Should** | §6 レスポンシブUI（4段階表） | CSS 変数化で再現可能。 |
| **Nice** | §9-A フォント削除の確認ダイアログ・挙動確認 | 既存 `font_remove` の確認が先。 |
| **Nice** | §9-B ウィンドウ状態の形式統一 | 既存で機能する。移行は文字列形式のみで十分。 |
| **Nice** | §7 MD編集（contenteditable） | Rust版では不採用（置換済み）。**実装不要**。 |
| **対象外** | §9-C 単一インスタンス | 旧版にも無い。 |

---

## 11. 未確認事項（まとめ）

1. §4: Rust 版に Google Drive / OneDrive 相当のコマンド・メニューが存在するかは未確認（grep 0 件）。
2. §9-C / §9-D: 単一インスタンス・ファイル関連付けの Rust 版設定（`tauri.conf.json`）は未調査。
3. §2: `_wait_mermaid_then` と `strip_images` の内部挙動は未精査。B5 は未実装（引数のみ）。
4. §6: `_fit_text` の縮小アルゴリズム詳細は未精査。
5. §5: 同期の逆方向（プレビュー→エディタ）の有無は未確認。
6. §8: 旧版の「追加拒否 vs 切り詰め」の実際の優先順位は推定。
7. §1: 「説明を開く」`_open_guide` の中身は未精査。

---

## 12. 自己検証メモ

- 見出し構造: `#`（文書タイトル）→ `##`（§0〜§12）→ `###`（小項目）で整合。
- 引用行番号のスポットチェック（実ファイルと照合、後述の検証結果を参照）。
- 既存の `UI_SPEC.md` と重複する寸法表（§6）は、本書では**割愛せず転記**（実装者が本書だけで完結できるように）。値は `UI_SPEC.md` の §1 と一致させた。
