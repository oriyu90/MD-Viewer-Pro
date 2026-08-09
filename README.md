# MD Viewer Pro

A simple and fast Markdown viewer built with Python and PySide6 (Qt for Python).

**Current version / 現在のバージョン: v1.4.3**
See [RELEASE_NOTES.md](RELEASE_NOTES.md) for what's new (v1.3.0–v1.4.3).
更新履歴は [RELEASE_NOTES.md](RELEASE_NOTES.md) をご覧ください。

---

## 日本語

### 概要

MD Viewer Pro は、Python で開発された軽量な Markdown ビューアです。
シンプルで直感的なUIにより、Markdownの閲覧・編集・書き出しを快適に行えます。

---

### ダウンロード（Mac）

最新版は以下からダウンロードできます。
https://github.com/oriyu90/MD-Viewer-Pro/releases

#### インストール手順

1. `.dmg` ファイルをダウンロード
2. ファイルを開く
3. **MDViewerPro.app** を Applications フォルダへドラッグ
4. アプリを起動

---

### 初回起動について

本アプリは未署名のため、macOS によって警告が表示される場合があります。

その場合は以下の手順で起動してください：

1. アプリを右クリック
2. 「開く」を選択
3. 再度「開く」を選択

---

## 機能

### 機能一覧

| 機能       | 説明                                    |
| -------- | ------------------------------------- |
| 閲覧モード    | Markdown をきれいにレンダリング                  |
| MD編集     | レンダリング形式のまま直接編集                       |
| TXT編集    | 左エディタ + 右リアルタイムプレビュー（編集行を自動ハイライト・追従スクロール） |
| 見出し(TOC)パネル | 見出し一覧を表示し、クリックでジャンプ（**標準でオン**） |
| LaTeX 数式 | `$…$` / `$$…$$` の数式を組版して表示             |
| YAML 対応  | フロントマターをメタ情報として表示、`.yml`/`.yaml` も閲覧可 |
| A4文書     | 印刷向けA4レイアウト・余白設定                      |
| 詳細設定     | フォント・言語・テーマ・表示設定の変更（日本語 / 英語 / ドイツ語 / フランス語 / 中国語） |
| フォント追加   | TTF/OTF を取り込んで本文フォントに追加（削除も可）         |
| プラグインテーマ | `~/.mdviewer/themes/` にJSONを配置してテーマ追加 |

---

### 対応機能

* Markdown 表示
* リアルタイムプレビュー
* コードブロックのコピーボタン
* LaTeX 数式表示（オフライン・追加インストール不要）
* LaTeX の体裁コマンド（`\newpage` 等）の解釈
* YAML フロントマター / YAML ファイル表示
* 5 言語の表示（日本語 / English / Deutsch / Français / 简体中文）
* ユーザーフォントの追加・削除
* PDF / HTML 書き出し
* プラグインテーマ対応

---

### 改行の扱い

本アプリは **Enter で入れた改行を、そのまま改行として表示します**（v1.4.2 以降）。

素の Markdown では、単一の改行は無視されて前の行につながり、改行するには
行末に半角スペースを 2 つ置くか空行を入れる必要があります。文章を書くときの
感覚と合わないため、書いたとおりに表示する方式にしています。
Obsidian や Typora などのエディタと同じ考え方です。

* 空行を 1 行入れると、これまでどおり段落の区切りになります。
* コードブロック・表の中は Markdown の記法どおりで、変わりません。
* 閲覧モード・MD編集・TXT編集のプレビュー・PDF / HTML 書き出しのすべてで
  同じように表示されます。

素の Markdown の挙動が必要な場合は、**詳細設定 →「改行の扱い」** の
「改行をそのまま改行として表示する」をオフにすると、v1.4.1 までと同じ
（単一の改行は前の行につながり、改行には行末の半角スペース 2 個または空行が
必要）動作に戻せます。設定は次回起動時にも引き継がれます。

---

### 書式ボタンの動き

見出し・引用・箇条書き・番号付きのボタンは、**いま付いている書式を置き換えます**。
H1 の行で H2 を押すと H2 になり、記号が積み重なることはありません。
同じボタンをもう一度押すと本文に戻ります。「本文」ボタンは、行頭に付いている
書式をすべて外して本文に戻します。

MD編集モードで見出しの行を改行すると、新しくできる行は必ず本文になります。

---

### LaTeX 数式

本文中に `$…$`（インライン）または `$$…$$`（別行立て）で数式を書くと、
Computer Modern 系の書体で組版して表示します。`\(…\)` / `\[…\]` も使えます。
外部ライブラリやネットワーク接続は不要で、PDF / HTML 書き出しにもそのまま反映されます。

```markdown
アインシュタインの式 $E = mc^2$ は有名です。

$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$
```

対応している主な記法:

| 種類     | 例                                                             |
| ------ | ------------------------------------------------------------- |
| 添字     | `x^2`, `a_{ij}`, `\sum_{i=1}^{n}`                              |
| 分数・根号  | `\frac{a}{b}`, `\dfrac`, `\binom{n}{k}`, `\sqrt{x}`, `\sqrt[3]{x}` |
| 大型演算子  | `\sum`, `\prod`, `\int`, `\oint`, `\bigcup`, `\lim`           |
| 括弧     | `\left( … \right)`, `\left\{ … \right.`（高さに合わせて伸縮）            |
| 環境     | `pmatrix`, `bmatrix`, `vmatrix`, `cases`, `aligned`, `array`  |
| 書体     | `\mathbb{R}`, `\mathcal{L}`, `\mathbf`, `\mathrm`, `\text{…}` |
| アクセント  | `\hat{x}`, `\bar{x}`, `\vec{v}`, `\overline{AB}`              |
| 記号     | `\alpha`, `\le`, `\to`, `\infty`, `\partial` ほか多数             |

* コードブロック / インラインコード内の `$` は数式として扱いません。
  `$5 と $10` のような通貨表記もそのまま表示されます。
* 未対応のコマンドは消さずにそのまま表示するので、書いた内容が失われることはありません。
* MD編集モードでは数式は 1 つのまとまりとして扱われます（式そのものの編集は TXT編集モードで行ってください）。

---

### LaTeX の体裁コマンド（改ページなど）

`\newpage` のような「文書の体裁を指示する」コマンドは、**文字列としては表示せず、
指示として解釈して表示に反映します**（v1.4.2 以降）。

| コマンド | 動作 |
| ---- | ---- |
| `\newpage` `\pagebreak` `\clearpage` `\cleardoublepage` | 改ページ |
| `\vspace{1cm}` `\vspace*{…}` | 指定した高さの縦の空き |
| `\bigskip` `\medskip` `\smallskip` | 大・中・小の縦の空き |
| `\newline` `\linebreak` | 改行 |
| `\par` | 段落の区切り |
| `\noindent` `\indent` `\centering` `\raggedright` `\raggedleft` `\hfill` | 表示には反映できないため隠すだけ |

改ページの見え方はモードによって変わります。

* **PDF 書き出し**: 実際にそこでページが分かれます（A4文書 / B5文書 / フリーのいずれでも）。
* **A4文書 / B5文書 表示**: 次のページの先頭まで送られ、ページ区切り線が入ります。
* **フリー表示**: ページという概念がないため、何も表示しません（段落の区切りとしてだけ働きます）。
* **MD編集モード**: 場所が分かるよう破線とコマンド名を薄く表示します（削除・移動できます）。

* コードブロック / インラインコード内のコマンドは対象外です。説明として
  `` `\newpage` `` と書いたものが消えることはありません。
* 数式（`$…$`）の中のコマンドも対象外です。
* 対応していないコマンドは消さずにそのまま表示します。
* MD編集モードで開いて保存しても、元のコマンドの記述はそのまま残ります。

---

### YAML 対応

* **フロントマター**: 文書の先頭を `---` で囲んだ YAML は、本文とは別のメタ情報
  パネルとして表示します（従来は水平線と本文に化けていました）。
* **YAML ファイル**: `.yml` / `.yaml` を開くと YAML として構文強調表示します。
  この場合 MD編集は使えません（TXT編集で編集できます）。
* **コードブロック**: ` ```yaml ` を付けたコードブロックは従来どおり構文強調されます。

---

### フォントの追加

詳細設定の「フォント」から、推奨フォント・追加したフォント・システムフォントを選べます。

* **フォントを追加...**: TTF / OTF / TTC ファイルを選ぶと `~/.mdviewer/fonts/` に
  取り込まれ、次回以降も使えるようになります。
* **選択中のフォントを削除**: 自分で追加したフォントのみ削除できます
  （システムに元から入っているフォントは削除されません）。
* IPAmj明朝 / Source Han Serif は推奨フォントとして一覧に出ます。未インストールの
  場合は「（未インストール）」と表示されるので、TTF/OTF を上記の手順で追加してください。

---

## English

### Overview

MD Viewer Pro is a lightweight Markdown viewer built with Python.
It provides fast rendering, editing, and exporting with a clean interface.

---

### Download (Mac)

Download the latest version here:
https://github.com/oriyu90/MD-Viewer-Pro/releases

#### Installation

1. Download the `.dmg` file
2. Open it
3. Drag **MDViewerPro.app** into the Applications folder
4. Launch the application

---

### First Launch

macOS may block the application because it is not signed.

To open the app:

1. Right-click the application
2. Click "Open"
3. Click "Open" again

---

## Features

### Feature List

| Feature           | Description                                  |
| ----------------- | -------------------------------------------- |
| View Mode         | Clean Markdown rendering                     |
| MD Editing        | Edit directly in rendered format             |
| TXT Editing       | Split editor with live preview (auto-highlights and scrolls to the edited line) |
| TOC Panel         | Headings sidebar, click to jump (**on by default**) |
| LaTeX Math        | Typesets `$…$` / `$$…$$` formulas            |
| YAML Support      | Front matter shown as a metadata panel; opens `.yml`/`.yaml` |
| A4 Document       | Print-ready A4 layout with margins           |
| Advanced Settings | Fonts, language (JA / EN / DE / FR / ZH), and themes |
| Custom Fonts      | Add TTF/OTF files as body fonts (and remove them) |
| Plugin Themes     | Add themes via JSON in `~/.mdviewer/themes/` |

---

### Supported Features

* Markdown rendering
* Real-time preview
* Copy button for code blocks
* LaTeX math rendering (offline, no extra install)
* LaTeX layout commands (`\newpage`, …)
* YAML front matter / YAML files
* Five UI languages (日本語 / English / Deutsch / Français / 简体中文)
* Add and remove your own fonts
* Export to PDF / HTML
* Plugin theme support

---

### How line breaks are handled

**A line break you type with Enter is rendered as a line break** (since v1.4.2).

In plain Markdown a single newline is ignored and joined onto the previous line;
breaking a line requires two trailing spaces or a blank line. That does not match
how people actually write, so the app renders what you typed — the same convention
used by editors such as Obsidian and Typora.

* A blank line still starts a new paragraph, as before.
* Code blocks and tables follow standard Markdown and are unchanged.
* View mode, MD Edit, the TXT Edit preview, and PDF / HTML export all render
  identically.

If you need standard Markdown behaviour, turn off **Settings → Line Breaks →
"Render a single newline as a line break"**. That restores the pre-v1.4.2
behaviour (a single newline joins onto the previous line; breaking a line needs
two trailing spaces or a blank line). The choice is remembered between launches.

---

### How the format buttons behave

The heading, quote, bullet and numbered-list buttons **replace** the current block
format. Pressing H2 on an H1 line gives you an H2 — markers never stack up.
Pressing the same button again returns the line to body text. The Body button
strips every marker at the start of the line.

In MD Edit, pressing Enter inside a heading always produces a body-text line.

---

### LaTeX Math

Write `$…$` (inline) or `$$…$$` (display) in your document and it is typeset in a
Computer Modern style serif face. `\(…\)` and `\[…\]` work too. No external library
and no network access are required, and the result carries over to PDF/HTML export.

```markdown
Einstein's $E = mc^2$ is well known.

$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$
```

Supported notation includes:

| Category      | Examples                                                       |
| ------------- | -------------------------------------------------------------- |
| Scripts       | `x^2`, `a_{ij}`, `\sum_{i=1}^{n}`                               |
| Fractions/roots | `\frac{a}{b}`, `\dfrac`, `\binom{n}{k}`, `\sqrt{x}`, `\sqrt[3]{x}` |
| Big operators | `\sum`, `\prod`, `\int`, `\oint`, `\bigcup`, `\lim`            |
| Delimiters    | `\left( … \right)`, `\left\{ … \right.` (auto-stretching)      |
| Environments  | `pmatrix`, `bmatrix`, `vmatrix`, `cases`, `aligned`, `array`   |
| Styles        | `\mathbb{R}`, `\mathcal{L}`, `\mathbf`, `\mathrm`, `\text{…}`  |
| Accents       | `\hat{x}`, `\bar{x}`, `\vec{v}`, `\overline{AB}`               |
| Symbols       | `\alpha`, `\le`, `\to`, `\infty`, `\partial`, and many more     |

* A `$` inside a code block or code span is never treated as math, and currency
  such as `$5 and $10` is left alone.
* Unsupported commands are shown verbatim instead of being dropped, so nothing
  you wrote is lost.
* In MD Edit mode a formula behaves as a single unit; edit the formula itself in
  TXT Edit mode.

---

### LaTeX layout commands (page breaks and friends)

Commands that describe document layout, such as `\newpage`, are **not shown as
text — they are interpreted and applied to the rendering** (since v1.4.2).

| Command | Effect |
| ---- | ---- |
| `\newpage` `\pagebreak` `\clearpage` `\cleardoublepage` | Page break |
| `\vspace{1cm}` `\vspace*{…}` | Vertical space of the given length |
| `\bigskip` `\medskip` `\smallskip` | Large / medium / small vertical space |
| `\newline` `\linebreak` | Line break |
| `\par` | Paragraph break |
| `\noindent` `\indent` `\centering` `\raggedright` `\raggedleft` `\hfill` | Cannot be reflected in the rendering, so simply hidden |

How a page break looks depends on the mode:

* **PDF export**: a real page break (in A4 Document, B5 Document and Free alike).
* **A4 / B5 Document view**: content is pushed to the top of the next page and a
  page separator line is drawn.
* **Free view**: nothing is shown — there are no pages — it just acts as a
  paragraph separator.
* **MD Edit**: a faint dashed line with the command name, so you can see and
  delete or move it.

* Commands inside code blocks and code spans are left alone, so writing
  `` `\newpage` `` as an example never disappears.
* Commands inside math (`$…$`) are left alone too.
* Unsupported commands are shown verbatim rather than dropped.
* Opening a document in MD Edit and saving it keeps the original commands intact.

---

### YAML Support

* **Front matter**: a `---` delimited YAML block at the top of the document is
  rendered as a separate metadata panel (previously it turned into a horizontal
  rule plus body text).
* **YAML files**: opening `.yml` / `.yaml` shows the file with YAML syntax
  highlighting. MD Edit is unavailable for these; use TXT Edit instead.
* **Code blocks**: ` ```yaml ` fenced blocks are highlighted as before.

---

### Adding Fonts

Settings → Font lets you pick from recommended fonts, added fonts, and system fonts.

* **Add Font...**: choose a TTF / OTF / TTC file; it is copied into
  `~/.mdviewer/fonts/` and stays available on future launches.
* **Remove selected font**: only fonts you added can be removed; fonts installed
  on the system are never touched.
* IPAmj Mincho and Source Han Serif are listed as recommended fonts. If they are
  not installed they are shown as "(not installed)" — add the TTF/OTF as above.

---

## Author

Yuki Orita
LinkedIn: https://www.linkedin.com/in/%E6%82%A0%E5%B8%8C-%E6%8A%98%E7%94%B0-746b84383/

---

## License

MIT License

Copyright (c) 2026 Yuki_Orita

This software is released under the MIT License.
You retain full copyright ownership while allowing others to use, modify, and distribute the software under the license terms.
