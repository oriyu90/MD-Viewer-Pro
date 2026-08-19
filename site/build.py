#!/usr/bin/env python3
"""紹介サイトを site/content.json から生成する。

    python3 site/build.py

出力先は website/ で、Cloudflare Pages はそこをそのまま配信する
(共通ルール5-5: ビルド工程なしの静的サイト)。つまり生成物もコミットする。

文言を直すときは site/content.json だけを編集してこのスクリプトを流す。
以前は初期表示用の HTML と言語切替用の JS に同じ文言が二重にあり、
片方だけ直すと言語を切り替えた瞬間に古い文言へ戻る状態だった。
"""
import html
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "website")


def e(s):
    """HTML のテキスト/属性として安全にする。"""
    return html.escape(str(s), quote=True)


def build():
    c = json.load(open(os.path.join(SITE, "content.json"), encoding="utf-8"))
    lang = c["defaultLang"]
    t = c["languages"][lang]
    seo = c["seo"][lang]
    ver, dl, repo = c["version"], c["downloadUrl"], c["repoUrl"]

    def nav_links():
        # nav は [機能, 実際の画面, 導入] の3つで、リンク先は固定
        ids = ["#features", "#screen", "#download"]
        return "".join(f'<a href="{i}" data-t="nav.{n}">{e(v)}</a>'
                       for n, (i, v) in enumerate(zip(ids, t["nav"])))

    def lang_options():
        return "".join(
            f'<option value="{code}"{" selected" if code == lang else ""}>'
            f'{e(c["languages"][code]["language"])}</option>'
            for code in c["languages"])

    head = f"""<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title data-t="seo.title">{e(seo['title'])}</title>
<meta name="description" content="{e(seo['description'])}" data-t-attr="seo.description"/>
<meta name="keywords" content="{e(c['keywords'])}"/>
<meta name="author" content="{e(c['author'])}"/>
<link rel="author" href="https://github.com/oriyu90"/>
<meta name="creator" content="{e(c['author'])}"/>
<meta name="publisher" content="{e(c['author'])}"/>
<meta name="robots" content="index, follow"/>
<meta property="og:title" content="{e(seo['ogTitle'])}" data-t-attr="seo.ogTitle"/>
<meta property="og:description" content="{e(seo['ogDescription'])}" data-t-attr="seo.ogDescription"/>
<meta property="og:site_name" content="MD Viewer Pro"/>
<meta property="og:type" content="website"/>
<meta property="og:locale" content="{e(seo['locale'])}" data-t-attr="seo.locale"/>
<meta property="og:url" content="{e(c['siteUrl'])}"/>
<meta property="og:image" content="{e(c['siteUrl'])}md-viewer-pro-icon.jpeg"/>
<meta name="twitter:card" content="summary"/>
<meta name="twitter:title" content="{e(seo['twTitle'])}" data-t-attr="seo.twTitle"/>
<meta name="twitter:description" content="{e(seo['twDescription'])}" data-t-attr="seo.twDescription"/>
<link rel="canonical" href="{e(c['siteUrl'])}"/>
<link rel="shortcut icon" href="/md-viewer-pro-icon.jpeg"/>
<link rel="icon" href="/md-viewer-pro-icon.jpeg"/>
<link rel="apple-touch-icon" href="/md-viewer-pro-icon.jpeg"/>
<link rel="stylesheet" href="/site.css"/>"""

    ld = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": "MD Viewer Pro", "alternateName": "MDビューアー Pro",
        "operatingSystem": "macOS", "applicationCategory": "DeveloperApplication",
        "softwareVersion": ver, "downloadUrl": dl, "codeRepository": repo,
        "author": {"@type": "Person", "name": "Yuki Orita",
                   "alternateName": ["Yuki_Orita", "折田悠希", "おりたゆうき"]},
        "license": "https://opensource.org/license/mit",
    }

    cards = "".join(
        f'<article><span data-t="cards.{i}.0">{e(n)}</span>'
        f'<h3 data-t="cards.{i}.1">{e(h)}</h3>'
        f'<p data-t="cards.{i}.2">{e(b)}</p><i aria-hidden="true">↘</i></article>'
        for i, (n, h, b) in enumerate(t["cards"]))

    strip = "".join(f'<span data-t="strip.{i}">{e(v)}</span><b>✦</b>'
                    for i, v in enumerate(t["strip"])) * 2

    facts = "".join(
        f'<div><strong data-t="facts.{i}.0">{e(n)}</strong>'
        f'<span data-t="facts.{i}.1">{e(l)}</span></div>'
        for i, (n, l) in enumerate(t["facts"]))

    details = "".join(
        f'<article><span class="detail-number">{i + 1:02d}</span>'
        f'<code data-t="details.{i}.0">{e(code)}</code>'
        f'<h3 data-t="details.{i}.1">{e(h)}</h3>'
        f'<p data-t="details.{i}.2">{e(b)}</p></article>'
        for i, (code, h, b) in enumerate(t["details"]))

    wheel = "".join(f"<span>{e(v['language'])}</span>" for v in c["languages"].values())

    steps = "".join(
        f'<li><span>{i + 1:02d}</span><p data-t="steps.{i}">{e(s)}</p></li>'
        for i, s in enumerate(t["steps"]))

    title_lines = "".join(f'<span data-t="title.{i}">{e(v)}</span>'
                          for i, v in enumerate(t["title"]))

    body = f"""<main>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<header class="site-header">
<a class="brand" href="#top" aria-label="MD Viewer Pro home"><img src="/md-viewer-pro-icon.jpeg" alt=""/><span>MD Viewer Pro</span></a>
<nav aria-label="Primary navigation">{nav_links()}
<label class="language-picker"><span class="sr-only">Language</span><select>{lang_options()}</select></label></nav>
</header>
<section class="hero" id="top">
<div class="hero-copy"><p class="eyebrow" data-t="eyebrow">{e(t['eyebrow'])}</p>
<h1>{title_lines}</h1>
<p class="lead" data-t="lead">{e(t['lead'])}</p>
<div class="hero-actions"><a class="button button-primary" href="{e(dl)}"><span data-t="download">{e(t['download'])}</span><span aria-hidden="true">↓</span></a>
<a class="button button-secondary" href="{e(repo)}" target="_blank" rel="noreferrer"><span data-t="github">{e(t['github'])}</span><span aria-hidden="true">↗</span></a></div>
<p class="download-note" data-t="note">{e(t['note'])}</p></div>
<div class="hero-visual"><img class="app-icon" src="/md-viewer-pro-icon.jpeg" alt="MD Viewer Pro application icon"/>
<div class="hero-code" aria-hidden="true"><span># Welcome</span><br/><br/>Write naturally.<br/>Read beautifully.<br/><br/><i>$$ E = mc^2 $$</i></div>
<span class="version-stamp">v{e(ver)}</span></div>
</section>
<div class="feature-strip" aria-hidden="true">{strip}</div>
<section class="section features" id="features">
<div class="section-heading"><p class="kicker" data-t="featuresKicker">{e(t['featuresKicker'])}</p>
<h2 data-t="featuresTitle">{e(t['featuresTitle'])}</h2><p data-t="featuresLead">{e(t['featuresLead'])}</p></div>
<div class="feature-cards">{cards}</div>
</section>
<section class="screen-section" id="screen">
<div class="screen-intro"><p class="kicker" data-t="screenKicker">{e(t['screenKicker'])}</p>
<h2 data-t="screenTitle">{e(t['screenTitle'])}</h2><p data-t="screenBody">{e(t['screenBody'])}</p></div>
<figure><div class="screen-frame"><img src="/md-viewer-pro-screen.png" alt="MD Viewer Pro v{e(ver)}"/></div>
<figcaption data-t="screenCaption">{e(t['screenCaption'])}</figcaption></figure>
<div class="facts">{facts}</div>
</section>
<section class="section detail-section"><h2 data-t="detailTitle">{e(t['detailTitle'])}</h2>
<div class="detail-grid">{details}</div></section>
<section class="language-section"><div><p class="kicker" data-t="languagesLabel">{e(t['languagesLabel'])}</p>
<h2 data-t="languagesTitle">{e(t['languagesTitle'])}</h2><p data-t="languagesBody">{e(t['languagesBody'])}</p></div>
<div class="language-wheel">{wheel}</div></section>
<section class="download-section" id="download">
<div class="download-icon-wrap"><img src="/md-viewer-pro-icon.jpeg" alt="MD Viewer Pro icon"/></div>
<div class="download-content"><p class="kicker" data-t="downloadKicker">{e(t['downloadKicker'])}</p>
<h2><span data-t="downloadTitle">{e(t['downloadTitle'])}</span></h2>
<p data-t="downloadBody">{e(t['downloadBody'])}</p>
<div class="release-status"><div><small data-t="releaseLabel">{e(t['releaseLabel'])}</small><strong>v{e(ver)}</strong><span data-t="unsigned">{e(t['unsigned'])}</span></div>
<div><small data-t="sourceLabel">{e(t['sourceLabel'])}</small><strong>v{e(ver)}</strong><span>GitHub / main</span></div></div>
<div class="hero-actions"><a class="button button-light" href="{e(dl)}"><span data-t="downloadButton">{e(t['downloadButton'])}</span><span>↓</span></a>
<a class="button button-outline" href="{e(repo)}" target="_blank" rel="noreferrer"><span data-t="sourceButton">{e(t['sourceButton'])}</span><span>↗</span></a></div></div>
</section>
<section class="section install-section"><h2 data-t="installTitle">{e(t['installTitle'])}</h2>
<ol>{steps}</ol>
<aside><strong data-t="gatekeeperTitle">{e(t['gatekeeperTitle'])}</strong><p data-t="gatekeeperBody">{e(t['gatekeeperBody'])}</p></aside></section>
<footer>
<div class="footer-brand"><img src="/md-viewer-pro-icon.jpeg" alt=""/><div><strong>MD Viewer Pro</strong><span>A lightweight Markdown viewer for macOS.</span></div></div>
<div class="footer-links"><a href="{e(c['discordUrl'])}" target="_blank" rel="noreferrer"><span data-t="community">{e(t['community'])}</span> ↗</a>
<a href="{e(c['devSiteUrl'])}" target="_blank" rel="noreferrer"><span data-t="official">{e(t['official'])}</span> ↗</a>
<a href="{e(c['xUrl'])}" target="_blank" rel="noreferrer"><span data-t="x">{e(t['x'])}</span> ↗</a>
<a href="{e(repo)}" target="_blank" rel="noreferrer">GitHub ↗</a></div>
<div class="footer-bottom"><span data-t="creator">{e(t['creator'])}</span><span data-t="footerLine">{e(t['footerLine'])}</span>
<a href="#top"><span data-t="backTop">{e(t['backTop'])}</span> ↑</a></div>
</footer>
</main>"""

    # 言語切替 (React は使わない。data-t の指す文言を差し替えるだけ)
    switcher = """<script id="i18n" type="application/json">__DATA__</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById('i18n').textContent);
  var L = D.languages, S = D.seo, DEF = D.defaultLang;
  function pick(o, path) {
    return path.split('.').reduce(function (v, k) {
      return v == null ? v : v[/^\\d+$/.test(k) ? Number(k) : k];
    }, o);
  }
  function apply(code) {
    var t = L[code]; if (!t) return;
    document.documentElement.lang = code;
    document.querySelectorAll('[data-t]').forEach(function (el) {
      var p = el.getAttribute('data-t');
      var v = p.indexOf('seo.') === 0 ? pick(S[code], p.slice(4)) : pick(t, p);
      if (typeof v === 'string') el.textContent = v;
    });
    document.querySelectorAll('[data-t-attr]').forEach(function (el) {
      var p = el.getAttribute('data-t-attr');
      var v = p.indexOf('seo.') === 0 ? pick(S[code], p.slice(4)) : pick(t, p);
      if (typeof v === 'string') el.setAttribute('content', v);
    });
    var sel = document.querySelector('.language-picker select');
    if (sel && sel.value !== code) sel.value = code;
    try { localStorage.setItem('mdvp-lang', code); } catch (e) {}
  }
  // ブラウザの言語を自動判別 (保存済みの選択があればそれを優先)
  var saved = null;
  try { saved = localStorage.getItem('mdvp-lang'); } catch (e) {}
  var want = saved;
  if (!want) {
    var navs = navigator.languages || [navigator.language || ''];
    for (var i = 0; i < navs.length && !want; i++) {
      var base = String(navs[i]).toLowerCase().split('-')[0];
      if (L[base]) want = base;
    }
  }
  if (want && want !== DEF) apply(want);
  var sel = document.querySelector('.language-picker select');
  if (sel) sel.addEventListener('change', function () { apply(this.value); });
})();
</script>"""

    data = json.dumps({"languages": c["languages"], "seo": c["seo"],
                       "defaultLang": lang}, ensure_ascii=False, separators=(",", ":"))
    switcher = switcher.replace("__DATA__", data.replace("</", "<\\/"))

    page = (f'<!DOCTYPE html><html lang="{lang}"><head>\n{head}\n</head>\n'
            f'<body>\n{body}\n{switcher}\n</body></html>\n')

    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)

    # sitemap は生成時の日付にする
    from datetime import date
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url>\n    <loc>{c["siteUrl"]}</loc>\n'
        f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
        '    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n'
        '  </url>\n</urlset>\n')

    print(f"website/index.html を生成しました ({len(page):,} 文字, {len(c['languages'])} 言語)")


if __name__ == "__main__":
    build()
