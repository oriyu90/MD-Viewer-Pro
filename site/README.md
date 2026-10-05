# 紹介サイトのソース

公開先: https://studio-rizi.pages.dev/projects/md-viewer-pro/ (+ `/en/` `/zh/` `/pt/`)

## 直し方

文言・バージョン・リンクは **`site/content.json` だけ** を編集し、生成し直す。

```bash
python3 site/build.py
```

`website/index.html` と `website/en|zh|pt/index.html`、`website/tokens.css`、`website/styles.css`
が作り直されるので、`site/` と `website/` の両方をコミットして `main` へ push し、
同じ作業内で `oriyu90/studio-rizi` の `website/projects/md-viewer-pro/` へ同期する。

## 構成

| パス | 役割 |
| --- | --- |
| `site/content.json` | **唯一の情報源**。4言語の文言、バージョン、各種URL、OS別カード文言 |
| `site/build.py` | `content.json` から4言語の静的HTMLを生成（各言語の題名・本文を初期HTMLに出力） |
| `site/tokens.css` | Hallmarkトークン（色・ spacing・radius）。生成で `website/` へ複製 |
| `site/styles.css` | デザイン本体。直接編集可（生成で `website/` へ複製） |
| `website/index.html` | 日本語版（正規・x-default）。直接編集しない |
| `website/en|zh|pt/index.html` | 英語・中文・葡語版。直接編集しない |

## 仕組み

- 各言語ページは自己 canonical + 相互 hreflang（ja/en/zh-Hans/pt + x-default）を持つ。
  同一URLのメタデータを JS で差し替える運用はしない。
- ヒーローとダウンロード欄の macOS / Windows ボタンは横並び（flex wrap、狭幅で縦積み）。
- 旧 `website/site.css` と旧単一ファイルJS切替は廃止。CSSは `tokens.css` + `styles.css`。
- 旧 `website/sitemap.xml`・`robots.txt`・`_redirects` は旧 `md-viewer-pro.pages.dev`
  リダイレクト用の残置。中央のサイトマップは `studio-rizi` 側で管理する。

## 触るときの注意

- **見出しの `line-height` を 1.0 未満にしない。** 日本語・中国語は全角を埋めるため重なる。
- ダウンロードカードは2列→1列に崩れることを確認する（42rem以下で縦積み）。
- ファイル名にハッシュは付けない（Pages は `max-age=0, must-revalidate` + ETag）。
