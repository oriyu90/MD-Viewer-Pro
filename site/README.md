# 紹介サイトのソース

公開先: https://md-viewer-pro.pages.dev/

## 直し方

文言・バージョン・リンクは **`site/content.json` だけ** を編集し、生成し直す。

```bash
python3 site/build.py
```

`website/` の中身が作り直されるので、`site/` と `website/` の両方をコミットして
`main` へ push すると Cloudflare Pages が自動で反映する。

## なぜ生成物もコミットするのか

Cloudflare Pages は `website/` をビルドせずそのまま配信する設定
（共通ルール5-5: `build_command` は空、`destination_dir` は `website`）。
そのため生成結果をリポジトリに含める必要がある。

## 構成

| パス | 役割 |
| --- | --- |
| `site/content.json` | **唯一の情報源**。4言語の文言、バージョン、各種URL |
| `site/build.py` | `content.json` から `website/index.html` と `sitemap.xml` を生成 |
| `website/site.css` | デザイン。生成対象ではないので直接編集する |
| `website/index.html` | 生成物。直接編集しない（次のビルドで消える） |

## 仕組み

- 既定言語（日本語）の文言は HTML に直接書き出す。検索エンジンに
  JavaScript なしで読ませるため。
- 4言語ぶんの文言は `<script type="application/json">` に埋め込み、
  `data-t` 属性を持つ要素を書き換えて切り替える。`<title>` や
  `og:description` などのメタ情報も切り替わる。
- 初回表示はブラウザの言語設定から自動選択する。手動で選んだ場合は
  `localStorage` に覚えて次回もその言語で開く。

## 触るときの注意

- **見出しの `line-height` を 1.0 未満にしない。** 日本語・中国語は文字が
  全角を埋めるため、1.0 未満だと行同士が物理的に重なる。
- **`.hero-visual` の右上に要素を置かない。** `border-radius: 44%` の楕円
  コーナーに削られる。
- ファイル名にハッシュは付けていない。Cloudflare Pages が
  `max-age=0, must-revalidate` + ETag で配信するため、名前を変えなくても
  更新が反映される。
