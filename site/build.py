#!/usr/bin/env python3
"""MD Viewer Pro 紹介サイトを site/content.json から生成する。

    python3 site/build.py

- 情報源は site/content.json の1か所。直したらこのスクリプトで website/ を作り直し、
  site/ と website/ の両方をコミットする。詳細は site/README.md。
- 出力は 4言語の静的HTML (index.html + en/zh/pt/index.html)。各言語の題名・紹介文・
  主要本文を初期HTMLに出力し、相互 hreflang + 自己 canonical を持つ。同一URLの
  メタデータを JS だけで差し替える運用はしない (共通ルール3 / HOSTING 7)。
- 公開実体は oriyu90/studio-rizi の website/projects/md-viewer-pro/ であり、
  公開変更時は同じ作業内で中央へ同期する。website/sitemap.xml と robots.txt は
  旧 md-viewer-pro.pages.dev 用の残置であり、中央の sitemap には含めない。
"""
import html
import json
import os
import shutil
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "website")

LANGS = ["ja", "en", "zh", "pt"]
HTML_LANG = {"ja": "ja", "en": "en", "zh": "zh-CN", "pt": "pt"}
HREFLANG = {"ja": "ja", "en": "en", "zh": "zh-Hans", "pt": "pt"}
SUBDIR = {"ja": "", "en": "en", "zh": "zh", "pt": "pt"}
LOCALE_NAMES = {"ja": "日本語", "en": "English", "zh": "中文", "pt": "Português"}


def e(s):
    return html.escape(str(s), quote=True)


def page_url(site_url, code):
    base = site_url.rstrip("/") + "/"
    return base if code == "ja" else base + SUBDIR[code] + "/"


def build_page(c, code):
    t = c["languages"][code]
    seo = c["seo"][code]
    ver = c["version"]
    dl, dlwin, repo = c["downloadUrl"], c.get("downloadUrlWin", c["downloadUrl"]), c["repoUrl"]
    site_url = c["siteUrl"]
    canonical = page_url(site_url, code)
    hreflangs = "".join(
        f'<link rel="alternate" hreflang="{HREFLANG[k]}" href="{e(page_url(site_url, k))}"/>'
        for k in LANGS
    ) + f'<link rel="alternate" hreflang="x-default" href="{e(page_url(site_url, "ja"))}"/>'

    nav_ids = ["#features", "#screen", "#download"]
    nav = "".join(f'<a href="{i}">{e(v)}</a>' for i, v in zip(nav_ids, t["nav"]))
    switcher_links = "".join(
        f'<a href="/projects/md-viewer-pro/{"" if k == "ja" else SUBDIR[k] + "/"}" hreflang="{HREFLANG[k]}" lang="{HTML_LANG[k]}"'
        + (' aria-current="page"' if k == code else "") + f'>{e(LOCALE_NAMES[k])}</a>'
        for k in LANGS
    )
    title_lines = "".join(f"<span>{e(v)}</span>" for v in t["title"])
    strip = "".join(f"<span>{e(v)}</span><b>✦</b>" for v in t["strip"]) * 2
    cards = "".join(
        f"<article><span>{e(n)}</span><h3>{e(h)}</h3><p>{e(b)}</p></article>"
        for n, h, b in t["cards"]
    )
    facts = "".join(f"<div><strong>{e(n)}</strong><span>{e(l)}</span></div>" for n, l in t["facts"])
    details = "".join(
        f'<article><span class="detail-number">{i + 1:02d}</span><code>{e(cd)}</code><h3>{e(h)}</h3><p>{e(b)}</p></article>'
        for i, (cd, h, b) in enumerate(t["details"])
    )
    steps = "".join(f"<li><span>{i + 1:02d}</span><p>{e(s)}</p></li>" for i, s in enumerate(t["steps"]))
    steps_win = "".join(f"<li><span>{i + 1:02d}</span><p>{e(s)}</p></li>" for i, s in enumerate(t.get("stepsWin", [])))
    lang_dots = "".join(f"<span>{e(c['languages'][k]['language'])}</span>" for k in LANGS)

    ld = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": "MD Viewer Pro", "alternateName": ["MDビューアー Pro", "MD Viewer Pro"],
        "description": seo["description"],
        "operatingSystem": ["macOS", "Windows"],
        "applicationCategory": "DeveloperApplication",
        "softwareVersion": ver,
        "url": canonical,
        "downloadUrl": [dl, dlwin],
        "codeRepository": repo,
        "inLanguage": [HREFLANG[k] if k != "zh" else "zh-Hans" for k in LANGS],
        "author": {"@type": "Person", "name": "Yuki Orita",
                   "alternateName": ["Yuki_Orita", "折田悠希", "おりたゆうき"]},
        "license": "https://opensource.org/license/mit",
    }

    head = f"""<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{e(seo['title'])}</title>
<meta name="description" content="{e(seo['description'])}"/>
<meta name="keywords" content="{e(c['keywords'])}"/>
<meta name="author" content="{e(c['author'])}"/>
<link rel="author" href="https://github.com/oriyu90"/>
<meta name="robots" content="index, follow"/>
<meta name="theme-color" content="#f2efe6"/>
<link rel="canonical" href="{e(canonical)}"/>{hreflangs}<link rel="sitemap" type="application/xml" href="/sitemap.xml"/>
<meta property="og:type" content="website"/>
<meta property="og:site_name" content="MD Viewer Pro"/>
<meta property="og:locale" content="{e(seo['locale'])}"/>
<meta property="og:title" content="{e(seo['ogTitle'])}"/>
<meta property="og:description" content="{e(seo['ogDescription'])}"/>
<meta property="og:url" content="{e(canonical)}"/>
<meta property="og:image" content="{e(site_url.rstrip('/') + '/md-viewer-pro-icon.jpeg')}"/>
<meta name="twitter:card" content="summary"/>
<meta name="twitter:site" content="@InovateofRIZI"/>
<meta name="twitter:title" content="{e(seo['twTitle'])}"/>
<meta name="twitter:description" content="{e(seo['twDescription'])}"/>
<link rel="icon" href="/projects/md-viewer-pro/md-viewer-pro-icon.jpeg"/>
<link rel="apple-touch-icon" href="/projects/md-viewer-pro/md-viewer-pro-icon.jpeg"/>
<link rel="stylesheet" href="/projects/md-viewer-pro/tokens.css"/>
<link rel="stylesheet" href="/projects/md-viewer-pro/styles.css"/>"""

    body = f"""<a class="skip-link" href="#main">Skip</a>
<header class="site-header"><nav class="nav shell" aria-label="Primary">
<a class="brand" href="/projects/md-viewer-pro/{'' if code == 'ja' else SUBDIR[code] + '/'}" aria-label="MD Viewer Pro home"><img src="/projects/md-viewer-pro/md-viewer-pro-icon.jpeg" alt=""/> <span>MD Viewer Pro</span></a>
<div class="nav-links">{nav}
<a class="command-pill" href="{e(repo)}" target="_blank" rel="noreferrer">GitHub ↗</a>
<details class="language-switcher"><summary aria-label="Language">{code.upper()}</summary><div class="language-menu">{switcher_links}</div></details>
<a class="button button-primary" href="#download">↓</a></div></nav></header>
<main id="main">
<section class="hero"><div class="shell hero-grid"><div class="hero-copy">
<p class="eyebrow">{e(t['eyebrow'])}</p>
<h1>{title_lines}</h1>
<p class="hero-lede">{e(t['lead'])}</p>
<div class="hero-actions">
<a class="button button-primary" href="{e(dl)}"><span class="os-icon" aria-hidden="true">🍎</span><span>{e(t['downloadButton'])}<br/><small>macOS · DMG</small></span><span aria-hidden="true">↓</span></a>
<a class="button button-secondary" href="{e(dlwin)}"><span class="os-icon" aria-hidden="true">🪟</span><span>{e(t['downloadButtonWin'])}<br/><small>Windows · ZIP</small></span><span aria-hidden="true">↓</span></a>
</div>
<p class="hero-note">{e(t['note'])}</p>
<p><a class="button button-quiet" href="{e(repo)}" target="_blank" rel="noreferrer">{e(t['github'])} ↗</a></p>
</div>
<div class="hero-visual"><figure><div class="screen-frame"><img src="/projects/md-viewer-pro/md-viewer-pro-screen.png" alt="MD Viewer Pro v{e(ver)}"/></div>
<figcaption class="screen-caption">{e(t['screenCaption'])}</figcaption></figure>
<div class="version-row"><span class="version-stamp">v{e(ver)}</span><span class="version-stamp">{e(t['releaseLabel'])}</span></div>
</div></div></section>
<div class="feature-strip" aria-hidden="true">{strip}</div>
<section class="section" id="features"><div class="shell"><div class="section-header">
<p class="kicker">{e(t['featuresKicker'])}</p><h2>{e(t['featuresTitle'])}</h2><p>{e(t['featuresLead'])}</p></div>
<div class="feature-cards">{cards}</div></div></section>
<section class="screen-section" id="screen"><div class="shell"><div class="screen-intro">
<div><p class="kicker">{e(t['screenKicker'])}</p><h2>{e(t['screenTitle'])}</h2></div><p>{e(t['screenBody'])}</p></div>
<div class="facts">{facts}</div></div></section>
<section class="section detail-section"><div class="shell"><div class="section-header"><h2>{e(t['detailTitle'])}</h2></div>
<div class="detail-grid">{details}</div></div></section>
<section class="language-section"><div class="shell language-panel"><div>
<p class="kicker">{e(t['languagesLabel'])}</p><h2>{e(t['languagesTitle'])}</h2><p>{e(t['languagesBody'])}</p></div>
<div class="language-dots">{lang_dots}</div></div></section>
<section class="section" id="download"><div class="shell download-panel"><div class="download-content">
<p class="kicker">{e(t['downloadKicker'])}</p>
<h2>{e(t['downloadTitle']).replace(chr(10), '<br/>')}</h2>
<p>{e(t['downloadBody'])}</p>
<div class="release-meta"><div><small>{e(t['releaseLabel'])}</small><strong>v{e(ver)}</strong><span>{e(t['unsigned'])}</span></div>
<div><small>{e(t['sourceLabel'])}</small><strong>v{e(ver)}</strong><span>GitHub / main</span></div></div>
<div class="os-grid">
<div class="os-card"><h3><span class="os-icon" aria-hidden="true">🍎</span>{e(t.get('osMac', 'macOS'))}</h3>
<p class="os-file">{e(t.get('macFile', ''))}</p><p class="os-req">{e(t.get('macReq', ''))}</p>
<a class="button button-primary" href="{e(dl)}"><span>{e(t['downloadButton'])}</span><span aria-hidden="true">↓</span></a>
<div class="os-steps"><p><strong>{e(t['installTitle'])}</strong></p><ol>{steps}</ol></div>
<div class="os-note"><strong>{e(t['gatekeeperTitle'])}</strong><p>{e(t['gatekeeperBody'])}</p></div></div>
<div class="os-card"><h3><span class="os-icon" aria-hidden="true">🪟</span>{e(t.get('osWin', 'Windows'))}</h3>
<p class="os-file">{e(t.get('winFile', ''))}</p><p class="os-req">{e(t.get('winReq', ''))}</p>
<a class="button button-secondary" href="{e(dlwin)}"><span>{e(t['downloadButtonWin'])}</span><span aria-hidden="true">↓</span></a>
<p>{e(t.get('winBody', ''))}</p>
<div class="os-steps"><p><strong>{e(t.get('installTitleWin', ''))}</strong></p><ol>{steps_win}</ol></div>
<div class="os-note"><strong>{e(t.get('smartscreenTitle', ''))}</strong><p>{e(t.get('smartscreenBody', ''))}</p></div></div>
</div>
<div class="source-row"><a class="button button-quiet" href="{e(repo)}" target="_blank" rel="noreferrer">{e(t['sourceButton'])} ↗</a>
<a class="button button-quiet" href="{e(c['discordUrl'])}" target="_blank" rel="noreferrer">{e(t['community'])} ↗</a></div>
</div></div></section>
</main>
<footer class="site-footer"><div class="shell footer-line">
<a class="brand" href="/projects/md-viewer-pro/{'' if code == 'ja' else SUBDIR[code] + '/'}"><img src="/projects/md-viewer-pro/md-viewer-pro-icon.jpeg" alt=""/> <span>MD Viewer Pro</span></a>
<span>© 2026 {e(c['author'])}</span>
<a href="{e(repo)}" target="_blank" rel="noreferrer">GitHub</a>
<a href="{e(c['discordUrl'])}" target="_blank" rel="noreferrer">Discord</a>
<a href="{e(c['xUrl'])}" target="_blank" rel="noreferrer">X</a>
<a href="{e(c['devSiteUrl'])}" target="_blank" rel="noreferrer">Studio RIZI</a>
</div>
<div class="shell footer-meta"><span>{e(t['creator'])}</span><span>{e(t['footerLine'])}</span><a href="#main">{e(t['backTop'])} ↑</a></div></footer>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>"""
    return f'<!doctype html>\n<html lang="{HTML_LANG[code]}">\n<head>\n{head}\n</head>\n<body>\n{body}\n</body>\n</html>\n'


def build():
    c = json.load(open(os.path.join(SITE, "content.json"), encoding="utf-8"))
    # 共有CSSを website/ へ複製 (生成対象外の site.css 旧運用は廃止)
    for name in ("tokens.css", "styles.css"):
        src = os.path.join(SITE, name)
        if os.path.exists(src):
            os.makedirs(OUT, exist_ok=True)
            shutil.copyfile(src, os.path.join(OUT, name))
    # 旧 site.css が残っていれば削除 (二重読込防止)
    old = os.path.join(OUT, "site.css")
    if os.path.exists(old):
        os.remove(old)
    total = 0
    for code in LANGS:
        html_text = build_page(c, code)
        if code == "ja":
            out_path = os.path.join(OUT, "index.html")
        else:
            out_dir = os.path.join(OUT, SUBDIR[code])
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "index.html")
        open(out_path, "w", encoding="utf-8").write(html_text)
        total += len(html_text)
        print(f"  {out_path} ({len(html_text):,} chars)")
    # 旧リダイレクト専用 sitemap は最終更新日だけ更新 (中央 sitemap は studio-rizi 側で管理)
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{c["siteUrl"]}</loc><lastmod>{date.today().isoformat()}</lastmod>'
        '<changefreq>weekly</changefreq><priority>1.0</priority></url>\n</urlset>\n')
    print(f"website/ 4言語を生成しました (合計 {total:,} 文字)")


if __name__ == "__main__":
    build()
