# MD Viewer Pro

A simple and fast Markdown viewer built with Python and PySide6 (Qt for Python).

**Current version / 現在のバージョン: v1.4.1**
See [RELEASE_NOTES.md](RELEASE_NOTES.md) for what's new (v1.3.0–v1.4.1).
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
| 詳細設定     | フォント・言語・テーマ・表示設定の変更                   |
| フォント追加   | TTF/OTF を取り込んで本文フォントに追加（削除も可）         |
| プラグインテーマ | `~/.mdviewer/themes/` にJSONを配置してテーマ追加 |

---

### 対応機能

* Markdown 表示
* リアルタイムプレビュー
* コードブロックのコピーボタン
* LaTeX 数式表示（オフライン・追加インストール不要）
* YAML フロントマター / YAML ファイル表示
* ユーザーフォントの追加・削除
* PDF / HTML 書き出し
* プラグインテーマ対応

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
| Advanced Settings | Customize fonts, language, and themes        |
| Custom Fonts      | Add TTF/OTF files as body fonts (and remove them) |
| Plugin Themes     | Add themes via JSON in `~/.mdviewer/themes/` |

---

### Supported Features

* Markdown rendering
* Real-time preview
* Copy button for code blocks
* LaTeX math rendering (offline, no extra install)
* YAML front matter / YAML files
* Add and remove your own fonts
* Export to PDF / HTML
* Plugin theme support

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
