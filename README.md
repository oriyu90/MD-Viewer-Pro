# MD Viewer Pro

A simple and fast Markdown viewer built with Python and PyQt6.

---

## 日本語

### 概要

MD Viewer Pro は、Python と PyQt6 で開発された軽量な Markdown ビューアです。
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
| TXT編集    | 左エディタ + 右リアルタイムプレビュー                  |
| A4文書     | 印刷向けA4レイアウト・余白設定                      |
| 詳細設定     | フォント・言語・テーマ・表示設定の変更                   |
| プラグインテーマ | `~/.mdviewer/themes/` にJSONを配置してテーマ追加 |

---

### 対応機能

* Markdown 表示
* リアルタイムプレビュー
* コードブロックのコピーボタン
* PDF / HTML 書き出し
* プラグインテーマ対応

---

## English

### Overview

MD Viewer Pro is a lightweight Markdown viewer built with Python and PyQt6.
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
| TXT Editing       | Split editor with live preview               |
| A4 Document       | Print-ready A4 layout with margins           |
| Advanced Settings | Customize fonts, language, and themes        |
| Plugin Themes     | Add themes via JSON in `~/.mdviewer/themes/` |

---

### Supported Features

* Markdown rendering
* Real-time preview
* Copy button for code blocks
* Export to PDF / HTML
* Plugin theme support

---

## For Developers

### Setup

```bash
git clone https://github.com/oriyu90/MD-Viewer-Pro.git
cd MD-Viewer-Pro
python3 -m pip install -r requirements.txt
```

### Run

```bash
python main.py
```

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
