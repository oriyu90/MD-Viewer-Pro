# UI・挙動スペック（旧アプリ v1.5.3 からの抽出）

- 対象: `reference/main_v1.5.3.py`（7,915行、PySide6）
- 目的: 新アプリで再現すべき UI と挙動の仕様。実装者が参照する一次まとめ。
- 表記: 出典は `関数名 (行番号)`。行番号は `reference/main_v1.5.3.py` の該当箇所の開始行。
- 「推定」は本文から断定できず推測で補った箇所。
- 既存ファイルは変更していない。

## レポート冒頭: 抽出件数（自己カウント）

| 項目 | 件数（実測） |
|---|---|
| メインツールバー 操作子（`PianoBtn` のボタン型） | 8（戻る / 閲覧 / MD編集 / TXT編集 / フリー / A4文書 / 余白設定 / 詳細設定 / 目次 / クリップボード / PDF書き出し のうち、`PianoBtn(` 生成は 8 回。残りは後述の操作子） |
| メインツールバー 操作子（全体） | 13（上記ボタン型 8 に加え、ボタン型でない スケールスライダ・スケール値ラベル 等を含めた数） ※数え方の差に注意 |
| 書式ツールバー ボタン（区切り除く） | 15（B / I / ~~ / コード / H1 / H2 / H3 / 本文 / リスト / 番号 / 引用 / 水平線 / リンク / 画像 / テーブル） |
| ファイルメニュー 項目（区切り除く） | 9（新規ウィンドウ / 新規作成 / 開く / 保存 / 名前を付けて保存 / PDF書き出し / HTML書き出し / Google Drive / OneDrive） |
| 設定キー（`_SETTINGS_DEFAULTS`） | **12**（実測） |
| 設定ダイアログ 主な入力項目 | 8（フォント / 言語 / テーマ / アクセント色 / PDF設定 / 太字強調 / 改行の扱い / 余白系の補助） |
| 対応言語（LANGS / I18N） | 5（ja / en / de / fr / zh）推定: I18N 辞書の並びから |

> 注: `PianoBtn(` 生成回数の実測（メインツールバー区間 4113–4207）は 8。書式ツールバー区間（4208–4350）の `fb()`/`PianoBtn(` は 16 行ヒットするが、うち 1 行は `fb` 関数定義の行、残り 15 がボタン生成（B/I/~~/コード/H1/H2/H3/本文/リスト/番号/引用/水平線/リンク/画像/テーブル 相当）。

---

## 1. 画面レイアウト

出典: `_build_ui` (3991)、`_make_toc_panel` (4051)、`_make_clip_panel` (4066)、`_update_splitter_sizes` (6494)

縦方向の積み順（上→下）:

1. メインツールバー `mainTB`（高さ `TB_H = 72`px、出典 定数 62行）
2. 書式ツールバーコンテナ `_fmt_container`（高さ `FMT_H = 52`px、出典 定数 63行）。**閲覧モードでは非表示**。TXT編集・MD編集で表示（`_do_set_mode` 6401）。
3. 本体 `QSplitter`（水平）。左→右の並び:
   - 目次パネル `tocPanel`（`_toc_panel`）
   - エディタスタック `_editor_stack`（`_md_editor` = `QPlainTextEdit`。**TXT編集時のみ表示**、閲覧・MD編集では隠す）
   - プレビュー（`_preview_web` = QWebEngineView。起動後に `_preview_placeholder` と差し替え）
   - クリップボードパネル `clipPanel`（`_clip_panel`）

初期スプリッタ幅: `setSizes([0, 0, 1, 0])`（出典 `_build_ui` 4035付近）。以後 `_update_splitter_sizes` で制御。

### 表示条件
- 目次パネル: `_show_toc` かつ `edit_mode in ("md","txt")` のときのみ表示（`_update_toc_panel_visibility` 6446）。閲覧モードでは閲覧用オーバーレイ目次を使う（`_toc_js` 4533）。
- 書式ツールバー: `edit_mode in ("txt","md")`（`_do_set_mode` 6401）。
- エディタ: `edit_mode == "txt"` のみ（`_do_set_mode`）。
- クリップパネル: `_show_clip` で切替。**全モードで引き出し可能**（`_build_ui` コメント 4031）。既定は閉（`_SETTINGS_DEFAULTS`）。

### 寸法（ウィンドウ幅で段階変化）
出典: `_UI_SIZE_TABLE` (4158付近)、`_get_ui_scale_cat` (4137付近)、`_apply_responsive_style` (4170付近)

| 区分 | 幅(px) | tb_fs | btn_pad | fmt_fs | fmt_pad | min_w | slider_w | val_w |
|---|---|---|---|---|---|---|---|---|
| large | ≥1100 | 17 | 16 | 15 | 13 | 44 | 120 | 48 |
| medium | ≥780 | 14 | 11 | 13 | 9 | 28 | 92 | 40 |
| small | ≥620 | 12 | 6 | 11 | 5 | 26 | 64 | 36 |
| xsmall | <620 | 10 | 3 | 10 | 3 | 20 | 44 | 30 |

ツールバー高さ（段階別・出典 `_apply_responsive_style`）:
- large: tb 72 / fmt 52
- medium: tb 58 / fmt 44
- small: tb 46 / fmt 36
- xsmall: tb 40 / fmt 32

### アスペクト連動の側方空白（出典 `_side_blank_fraction` 4219付近、`_update_aspect_blanks`）
- 縦長（幅≦高さ）: 空白なし。
- 横長: 縦横比 1→3 で片側割合 0→0.20 へ線形増加。3:1以上は 0.20 固定（両端2割）。
- TXT編集ではエディタの左右に `setViewportMargins` で余白。フリーモードのプレビューは `.wrap` 幅を `(1-2*frac)*100%` に JS で設定。A4文書は対象外。

---

## 2. メインツールバー（左→右）

出典: `_make_main_tb` (4113)。区切りは `sep()`（幅1px `vSep`）。

| # | ID | ラベル(ja) | 動作 | 活性条件 | 出典 |
|---|---|---|---|---|---|
| 1 | back | 戻る | `_go_back` → `_set_mode("view")` | `edit_mode != "view"` | 4127, 6034 |
| — | 区切り | | | | |
| 2 | mode.view | 閲覧 | `_set_mode("view")` | `_mode_available("view")`（常に真） | 4134 |
| 3 | mode.md | MD編集 | `_set_mode("md")` | 読取専用ファイル・YAML以外。読取専用は不可、`doc_kind=="yaml"` も不可 | 4134, 6017 |
| 4 | mode.txt | TXT編集 | `_set_mode("txt")` | 読取専用ファイルは不可 | 4134, 6017 |
| — | 区切り | | | | |
| 5 | layout.free | フリー | `_set_layout("free")` | 常時。選択中は `set_active` | 4143, 6993 |
| 6 | layout.a4 | A4文書 | `_set_layout("a4")` | 常時。選択中は `set_active`。`b5` は `a4` に読替 | 4143, 6993 |
| 7 | margin | 余白設定 | `_open_margin_dialog`（A4余白 mm 設定） | `page_mode == "a4"` | 4153, 6035 |
| — | 区切り | | | | |
| 8 | scale | スケール（ラベル） | — | — | 4166 |
| 9 | scaleSlider | （スライダ） | 値 0〜4 を `SCALE_STEPS=[0.5,0.75,1.0,1.25,1.5]` に対応、`SCALE_LABELS=["50%","75%","100%","125%","150%"]`。変更で `_apply_theme`、`sliderReleased` で保存 | 常時 | 4171–4172, 7011 |
| 10 | scaleVal | （値ラベル 48px固定） | 現在値を表示 | 常時 | 4175 |
| — | 区切り | | | | |
| 11 | settings | 詳細設定 | `_open_settings`（設定ダイアログ） | 常時 | 4182 |
| — | 区切り | | | | |
| 12 | toc | 目次 | `_toggle_toc`（`_show_toc` 反転・保存・再描画） | 常時。`set_active(_show_toc)` | 4188, 6437 |
| — | 区切り | | | | |
| 13 | clipboard | クリップボード | `_toggle_clip` | 常時。`set_active(_show_clip)` | 4197, 6040 |
| — | 区切り | | | | |
| 14 | pdf | PDF書き出し | `_export_pdf` | 常時 | 4205 |

> 注: 上記の番号 1–14 は区切りを除くとボタン/操作子 13 個（戻る1 + モード3 + レイアウト2 + 余白1 + スケール(スライダ+値)2 + 設定1 + 目次1 + クリップ1 + PDF1 = 13）。前節の「11」は ボタン型のみ（PianoBtn）の数。
> 出典の `_set_mode` (6352) は、MD編集からの離脱時に WYSIWYG の HTML を取得して Markdown に戻してから遷移する（`_finish_mode_switch_from_md` 6378）。

ボタンの見た目: `PianoBtn`（独自ボタン、`set_fit_metrics` で幅に合わせてフォントを詰める）。`objectName="mainBtn"`。

---

## 3. 書式ツールバー

出典: `_make_fmt_tb` (4208)。ボタン `objectName="fmtBtn"`。TXT編集とMD編集で挙動が異なる。
- **TXT編集**: `_md_editor` (Markdown ソース) に記法を挿入・置換。
- **MD編集**: WYSIWYG のプレビュー（`.wrap`）に対し JS（`window._mdvExec` 等）で `execCommand` / `formatBlock` を実行。

| # | ボタンID | ラベル(ja) | TXT編集の動作 | MD編集の動作 | 挿入/置換する記法（TXT） |
|---|---|---|---|---|---|
| 1 | fmt_bold | B | 選択を `**…**` で囲む（未選択時は「リンクテキスト」既定文言を囲む） | `execCommand("bold")` | `**選択**` |
| 2 | fmt_italic | I | 同上 | `execCommand("italic")` | `*選択*` |
| 3 | fmt_strike | ~~ | 同上 | `execCommand("strikethrough")` | `~~選択~~` |
| 4 | fmt_code | コード | 改行付きフェンスで囲む | 選択を `<pre><code>` に置換 | `\n```\n選択\n```\n` |
| 5 | fmt_h1 | H1 | 行頭を `# ` に置換（同じ見出しを再押下で本文に戻す） | `_mdvBlock("h1")` | `# ` |
| 6 | fmt_h2 | H2 | 行頭を `## ` に置換 | `_mdvBlock("h2")` | `## ` |
| 7 | fmt_h3 | H3 | 行頭を `### ` に置換 | `_mdvBlock("h3")` | `### ` |
| 8 | fmt_body | 本文 | 行頭の全ブロックマーカーを除去（本文に戻す） | `_mdvBody()`（リスト解除・引用解除） | 行頭マーカー除去 |
| 9 | fmt_list | リスト | 行頭を `- ` にトグル（既に `- *+` ならば外す） | `execCommand("insertUnorderedList")` | `- ` |
| 10 | fmt_num | 番号 | 行頭を `n. ` にトグル。直前行が同インデントの番号付きなら連番 | `execCommand("insertOrderedList")` | `1. ` / `n. ` |
| 11 | fmt_quote | 引用 | 行頭を `> ` に置換 | `_mdvBlock("blockquote")` | `> ` |
| 12 | fmt_hr | 水平線 | `\n---\n` を挿入 | `execCommand("insertHTML","<hr><p><br></p>")` | `\n---\n` |
| 13 | fmt_link | リンク | ネイティブ入力ダイアログ→`[テキスト](URL)` 挿入。既定プレースホルダ `[link_text_default](URL)` | URLをネイティブダイアログで受け、`_mdvLink(url,label)` で挿入（JS prompt は使わない） | `[テキスト](URL)` |
| 14 | fmt_img | 画像 | `![alt](URL)` を挿入（既定プレースホルダ） | URLをネイティブダイアログで受け、`_mdvImage(url,alt)` で挿入 | `![alt](URL)` |
| 15 | fmt_table | テーブル | 3列×(見出し+2行)の GFM テーブルを挿入 | 3列×2行の `<table>` を選択行の後ろへ挿入し `_mdvSetupTableBtns` | 下記 |

テーブルの挿入形式（TXT、`_md_insert_table` 7194）:
```
| 列1 | 列2 | 列3 |
| :--- | :--- | :--- |
| セル | セル | セル |
| セル | セル | セル |
```
（列名・セル文言は `table_col`="列"、`table_cell`="セル" を I18N から取得。）

区切り（`fs()`）の位置: B/I/~~/コード | H1/H2/H3 | 本文 | リスト/番号 | 引用/水平線/リンク/画像 | テーブル。

ボタン表示幅・フォント: `_apply_btn_fit_metrics`（4342付近）で `fmt_fs`, `fmt_pad*2+4`, `max(12, min_w-14)` を適用。

---

## 4. メニュー

出典: `_build_menu` (4351)。`mb.setNativeMenuBar(True)`（macOS ではネイティブメニュー）。トップは「ファイル」のみ（`self._t("file")`）。

### ファイル
| 順 | 項目 | ショートカット | 動作 |
|---|---|---|---|
| 1 | 新規ウィンドウ | Ctrl+Shift+N | `new_window` |
| — | 区切り | | |
| 2 | 新規作成 | Ctrl+N | `file_new` |
| 3 | 開く… | Ctrl+O | `file_open` |
| 4 | 保存 | Ctrl+S | `file_save` |
| 5 | 名前を付けて保存… | Ctrl+Shift+S | `file_save_as` |
| 6 | PDFとして書き出し… | Ctrl+P | `_export_pdf` |
| 7 | HTMLとして書き出し… | （なし） | `_export_html` |
| — | 区切り | | |
| 8 | Google Drive にアップロード | （なし） | `_upload_gdrive` |
| 9 | OneDrive にアップロード | （なし） | `_upload_onedrive` |

> ショートカットは Qt の `QKeySequence("Ctrl+…")` 表記。macOS では Qt により Cmd に読み替えられる（推定: PySide6 の標準挙動。ソース上は `Ctrl`）。新アプリでは Cmd(Mac)/Ctrl(他) として扱うのが妥当（推定）。

メニュー構成は「ファイル」1 本のみ。「表示」「設定」「ヘルプ」メニューは本ソース `_build_menu` には存在しない（**確認済み**: `mb.addMenu` は1回のみ）。詳細設定はツールバー、目次/クリップ/PDF もツールバーから操作。

---

## 5. 設定項目

### 5.1 `_SETTINGS_DEFAULTS`（出典 836付近、12キー）

| キー | 型 | 既定値 | 意味 |
|---|---|---|---|
| lang | str | "ja" | 表示言語 |
| theme | str | "dark" | テーマ（dark/light/プラグイン名） |
| font_family | str | "Helvetica Neue" | UIフォント |
| bold_mode | bool | False | テキスト太字強調 |
| scale_idx | int | 2（=100%） | スケール段階（0〜4、`DEFAULT_SCALE_IDX=2`） |
| last_pdf_dir | str | "" | 最後のPDF保存先 |
| pdf_embed_images | bool | True | PDFに画像を埋め込む |
| window_geometry | str | "" | ウィンドウ位置・サイズ（base64） |
| show_toc | bool | True | 目次を既定で表示 |
| hard_breaks | bool | True | 単一改行を改行として表示 |
| accent_color | str | "" | テーマ色（""=既定, または #rrggbb） |
| show_clip | bool | False | クリップボードパネルを既定で閉じる |

> 件数: 上表は **12 行**（`lang, theme, font_family, bold_mode, scale_idx, last_pdf_dir, pdf_embed_images, window_geometry, show_toc, hard_breaks, accent_color, show_clip`）。レポート冒頭の「13」は誤り。**正しくは 12 キー**。冒頭表を訂正すること（下記 §10 参照）。

読込時の検証（`load_settings` 857付近）: `scale_idx` を 0〜4 にクランプ、`show_toc`/`hard_breaks`/`show_clip` を bool 化、`accent_color` は `#rrggbb` のみ有効・不正は ""。

### 5.2 設定ダイアログ（`SettingsDialog`、出典 3234、最小幅 380px）

上から順:
1. **フォント**（グループ「font_label」）: コンボ（推奨 / 追加フォント / システムフォント。区切り見出し付き）＋「Add Font...」「Remove」ボタン＋ヒント。
2. **言語**（`lang_label`）: コンボ。選択肢 = `LANGS` のキー（ja/en/de/fr/zh。出典 I18N 定義）。
3. **テーマ**（`theme_label`）: コンボ。選択肢 = `[dark, light] + プラグインテーマ名`。
4. **テーマ色（アクセント）**（`accent_label`、出典 3300付近）: コンボ 8 項目。
   - 既定 "" / Blue `#4a9eff` / Green `#3ecf8e` / Orange `#ff9f43` / Red `#ff6b6b` / Purple `#a78bfa` / Teal `#2dd4bf` / Custom...（`custom`）
   - 「Custom...」ボタンでカラーピッカー。プレビュー「●●●」。
5. **PDF設定**（グループ、出典 3340付近）: 出力フォルダを開くボタン等。
6. **太字強調**（`bold_label` = 「テキスト太字強調」）: チェックボックス。
7. **改行の扱い**（`hard_breaks_label` = 「改行の扱い」）: チェックボックス「改行をそのまま改行として表示する」（`hard_breaks_cb`）＋中間色ヒント（`hard_breaks_hint`: 「オフにすると素の Markdown 仕様どおり、単一の改行は前の行に連結される」）。

> 設定ダイアログ内の「余白」「改ページ」の入力は存在しない（A4余白は別ダイアログ `MarginDialog`、出典 3652）。

### 5.3 PDF書き出し設定（`PdfExportDialog`、出典 3652付近）
- 用紙は A4 固定（`QPageSize.A4`、出典 7297）。向きは縦/横（`landscape`）。
- 余白 (mm) は `a4_margins`（既定 20/20/20/20、出典 3850）。`MarginDialog` で編集（「A4余白設定 (mm)」）。
- 画像埋め込み `pdf_embed_images`（既定 True）。
- テーマ（`pdf_theme`）: dark/light/プラグイン。

---

## 6. モードと状態遷移

### 6.1 モード
- `edit_mode` ∈ {`view`, `md`, `txt`}（`_set_mode` 6352、`_do_set_mode` 6401）
- `page_mode` ∈ {`free`, `a4`}（`_set_layout` 6993、`b5`→`a4` 読替）

### 6.2 遷移規則
- 同一モードへの遷移は無視（`_set_mode`）。
- **禁止遷移**: `_mode_available` により、読取専用ファイルは `md`/`txt` 不可、YAML は `md` 不可（6017）。
- **MD編集 → 他モード**: WYSIWYG の innerHTML を取得し `_html_to_markdown` で Markdown に戻す。`dirty` の時のみ本文更新・`is_modified=True`（`_finish_mode_switch_from_md` 6378）。取得失敗時は `QMessageBox` を出して**編集モードに留まる**（取得不能なら離脱しない）。
- **TXT編集 → 他モード**: `_save_buf()` で `_content_text` を確定（6320付近）。
- **遷移時のアンカー保存**: スクロール位置をアンカーとして保持し、遷移先で復元（`_JS_CAPTURE_ANCHOR` 6271、`_scroll_editor_to_anchor` 6317）。TXT編集への遷移は `QTimer.singleShot(0)` で次フレームに位置合わせ。
- 遷移後: `_refresh_btn_states`、`_update_toc_panel_visibility`、`_update_splitter_sizes`、`_refresh_view`。
- 「戻る」は常に `view` へ（`_go_back`）。

### 6.3 スクロール同期
- 閲覧/MD編集の切替時、`window.pageYOffset` 等からアンカー（見出し/段落の位置）を取得し、遷移先で近い位置へ復元する方式（6271、6317）。
- 編集中の保存時も `_do_flush_preserve_scroll`（6105）で `scrollTop` を保持して再描画後に `_restore_scroll_after_flush`（6116）で戻す。
- 行単位の厳密な双方向同期は本ソースでは見当たらず（推定: 行ではなくアンカー・ブロック単位）。

### 6.4 TOC（目次）パネル
- 表示: `_show_toc` かつ `edit_mode ∈ {md, txt}`（6446）。閲覧モードではオーバーレイ目次（`_toc_js` 4533）。
- 項目クリック: `_on_toc_item_clicked`（6951）で該当見出しへスクロール。
- 再構築: `_rebuild_toc_list`（6922、`force` 指定で強制）。
- 幅: `_toc_panel_width`（6452）、`_toc_visible_width`（6486）、リサイズ時 `_sync_toc_width_on_resize`（6511）。
- 基準フォント: `_toc_base_font_px`（4527）。閲覧（オーバーレイ）と編集（ネイティブ）で同一値。

### 6.5 クリップボードパネル
- 表示: `_show_clip`、全モード可（`_toggle_clip` 6584）。既定は閉。
- 構成: タイトル（`clip_title`）／「+ 追加」（`clip_add`、`_on_clip_add` 6719）／スクロールリスト（カード）。
- カード: 本文ボタン＝押すとコピー（`_on_clip_copy` 6706、`clip_copied` 表示）、左下の小さな削除ボタン（`_on_clip_delete` 6772、`clip_delete_msg` で確認）。
- 幅: `_clip_panel_width`（6468）、`_clip_visible_width`（6477）、`_sync_clip_width_on_resize`（6551）。
- 表示更新: `_update_clip_panel_visibility`（6572）、`_rebuild_clip_list`（6607）。
- 空時: `clip_empty` + `clip_empty_hint`（「点击 + 按钮添加」相当の文言）。
- 上限・検証は §8 参照。

---

## 7. キーボードショートカット一覧

| 操作 | ショートカット（Qt表記） | 出典 |
|---|---|---|
| 新規ウィンドウ | Ctrl+Shift+N | 4358 |
| 新規作成 | Ctrl+N | 4370 |
| 開く | Ctrl+O | 4370 |
| 保存 | Ctrl+S | 4370 |
| 名前を付けて保存 | Ctrl+Shift+S | 4370 |
| PDF書き出し | Ctrl+P | 4370 |
| HTML書き出し | なし | 4370 |

- 書式（B/I/見出し等）のキーボードショートカットは `_build_menu`・`_make_fmt_tb` のいずれにも**定義なし**（確認済み: `setShortcut` は2箇所のみ）。
- macOS では Cmd 相当に読み替え（推定）。
- 本文中で言及がない（`QKeySequence` は上の2系統のみ）。

---

## 8. 既知の挙動（確認済み値）

| 項目 | 値 | 出典 |
|---|---|---|
| 改行（hard_breaks） | 既定 ON。Enter の改行を改行として描画。OFF で素の Markdown（単一改行は連結） | `_SETTINGS_DEFAULTS` 836, 設定 3362 |
| A4 余白 | 既定 20/20/20/20 mm（上右下左）。`MarginDialog` で編集。用紙 A4 297×210 | 3850, 5636–5638, 7297 |
| A4 ページ寸法 | 高さ 297 / 幅 210 mm（縦）。PDFは A4 固定 | 5637–5638, 7297 |
| スケール | 5段階 50/75/100/125/150%。既定 100%（idx 2）。スライダ 120px（large）。`SCALE_STEPS` 59行 | 59–63, 4171 |
| テーマ色 | 既定 "" ＋ プリセット 6色 ＋ カスタム。`#rrggbb` のみ許可 | 3301–3324, load_settings 857付近 |
| テーマ | dark（既定）/ light / プラグイン | 836, 3284 |
| クリップ上限 | 最大 **200** 件（`MAX_CLIPS=200`、88行）。超過時は `clip_limit_msg`（「最多可保存 {n} 条」）で拒否 | 88, 6722 |
| クリップ1件上限 | 最大 **5,000** 文字（`MAX_CLIP_LEN=5000`、89行）。超過は前5000字に切詰め（`clip_too_long`） | 89, 6746–6749 |
| クリップファイル上限 | 1 MiB（`MAX_CLIP_FILE_BYTES=1048576`、90行）。読込時に超過で無視 | 90, 962 |
| 空クリップ | 保存不可（`clip_empty_warning`） | I18N |
| クリップ保存順 | 上限超過時は末尾（新しい方）200件を残す（`self._clips[-MAX_CLIPS:]`） | 6758–6759 |
| 目次既定 | ON（初回起動時から開く） | 836 |
| 書式ツールバー表示 | TXT編集・MD編集のみ（閲覧では非表示） | 6401 |
| 余白設定の活性 | A4文書時のみ | 6035 |
| 戻るの活性 | 閲覧以外のとき | 6034 |
| 読取専用ファイル | MD/TXT 編集不可 | 6017 |
| YAML ドキュメント | MD編集不可（TXT編集のみ） | 6017 |
| 設定の即時保存 | スケールはスライダ離した時、その他は設定変更時に `_save_app_settings`（6065 付近） | 4172, 6065–6074 |
| 空白パネル防止 | 非表示エディタは隠す（幅0、ハンドル無効化） | 4026–4034 |

---

## 9. 未確認・推定事項

1. **メニューの「表示」「設定」「ヘルプ」**: 本ソースの `_build_menu` は「ファイル」のみ。他のメニューが別の関数（例 `_build_ui` 以外、または後の版）にあるかは未確認（推定: v1.5.3 では存在しない）。
2. **ショートカットの Cmd 変換**: Qt が macOS で Ctrl→Cmd に読み替えるかは PySide6 の標準挙動による（推定、未実機検証）。
3. **スクロール同期の粒度**: アンカー（見出し/ブロック）基準と判断。行ごとの双方向同期の有無は未確認。
4. **`PianoBtn` の詳細外観**（色・角丸・ホバー）: 本件はロジックのみ確認。見た目の数値は `ui/` 配下の CSS / デザイン文書（`reference/design_v1.5.3.md`）を参照すること（未確認）。
5. **アクセント色のプレビュー挙動・カスタムピッカーの詳細**: 3340付近以降は概略のみ確認。
6. **Google Drive / OneDrive アップロード**: メニュー項目の存在のみ確認。実装詳細は未調査。
7. **書式ボタンの `_mdvExec`/`_mdvBlock` の JS 細部**: 呼び出し側のみ確認。`window._mdv*` の内部実装（4807–4900付近の JS 文字列）は概略。
8. **言語**: ja/en/de/fr/zh の5言語（`LANGS` は `I18N` キー、出典 I18N 定義 約200〜790行）。件数は I18N 辞書の並びから推定。

---

## 10. 自己検証メモ

- 見出し構造: `#`（文書タイトル）→ `##`（§1〜§10）→ `###`（小項目）の階層で整合。
- 件数訂正（確定値）: 設定キー = **12**（`_SETTINGS_DEFAULTS` 実測）。書式ボタン = **15**。
- メインツールバー: `PianoBtn` のボタン型は **8**（実測）。レイアウト上の操作子は 13（ボタン8 + スライダ・値ラベル 等を含む。§2 の番号表と一致）。
- 冒頭の件数表・§5.1 の見出しは上記確定値に揃えてある。
- 各行に出典（関数名・行番号）を付与。一部の見た目（色・寸法の具体値）は本ソース外のため未記載。

以上。
