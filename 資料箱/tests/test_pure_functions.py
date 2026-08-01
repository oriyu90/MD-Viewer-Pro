"""v1.4.1 純粋関数 回帰テストハーネス.

main.py から対象関数のソースを抽出して実行し、markdown ライブラリの
実出力と突き合わせる。Qt に依存しない部分のみを対象とする。
"""
import re
import sys
import html as _html_mod
from html.parser import HTMLParser
from typing import Optional, Dict, List

import os

# リポジトリ内の相対位置から main.py を解決する (資料箱/tests/ から 2 つ上)
MAIN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "main.py")
src = open(MAIN, encoding="utf-8").read()

import markdown

# ── main.py から純粋関数群を切り出して exec する ──────────────────
def extract(start_marker, end_marker):
    i = src.index(start_marker)
    j = src.index(end_marker, i)
    return src[i:j]

ns = {"re": re, "HTMLParser": HTMLParser, "List": List,
      "Optional": Optional, "Dict": Dict, "markdown": markdown,
      "_html_mod": _html_mod}

# サニタイザ (アプリの実パイプラインと同じものを使う)
_i = src.index("_SAN_ALLOWED_TAGS = {")
exec(src[_i:src.index("# ════", _i)], ns)
_sanitize_html = ns["_sanitize_html"]

# _HTML2MD クラス + _html_to_md
exec(extract("class _HTML2MD(HTMLParser):", "# ════"), ns)
_html_to_md = ns["_html_to_md"]

# LaTeX 数式レンダラ + YAML フロントマター (v1.4.1)
exec(extract("# 数式退避用プレースホルダ", "#  SafeWebLoader"), ns)
_render_tex        = ns["_render_tex"]
_extract_math      = ns["_extract_math"]
_restore_math      = ns["_restore_math"]
_split_front_matter = ns["_split_front_matter"]
_parse_simple_yaml = ns["_parse_simple_yaml"]
_front_matter_html = ns["_front_matter_html"]

# _extract_headings (staticmethod 本体をインデント除去して取り込む)
_eh = extract("    def _extract_headings(text):", "    def _rebuild_toc_list")
_eh = "\n".join(l[4:] if l.startswith("    ") else l for l in _eh.split("\n"))
exec(_eh, ns)
_extract_headings = ns["_extract_headings"]

# _split_source_blocks
_LIST_ITEM_RE = re.compile(r'^\s*(?:[-*+]\s+|\d+[.)]\s+)')
ns["_LIST_ITEM_RE"] = _LIST_ITEM_RE
_ssb = extract("    def _split_source_blocks(text):", "    @staticmethod\n    def _tag_src_lines")
_ssb = "\n".join(l[4:] if l.startswith("    ") else l for l in _ssb.split("\n"))
exec(_ssb, ns)
_split_source_blocks = ns["_split_source_blocks"]

# _tag_src_lines
_tsl = extract("    def _tag_src_lines(body: str", "    @staticmethod\n    def _line_sync_js")
_tsl = "\n".join(l[4:] if l.startswith("    ") else l for l in _tsl.split("\n"))
exec(_tsl, ns)
_tag_src_lines = ns["_tag_src_lines"]


# ── 検証ヘルパ ────────────────────────────────────────────────
class TopLevelHeadings(HTMLParser):
    """markdown 出力の .wrap 直下 (トップレベル) 見出しだけを拾う。
    _on_toc_item_clicked の `.wrap>h1..h6` セレクタと同じ集合。"""
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.items = []
        self.cur = None
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if self.depth == 0 and re.fullmatch(r"h[1-6]", tag):
            self.cur, self.buf = tag, []
        self.depth += 1

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        self.depth -= 1
        if self.depth == 0 and self.cur == tag:
            self.items.append((int(tag[1]), "".join(self.buf)))
            self.cur = None

    def handle_data(self, data):
        if self.cur:
            self.buf.append(data)


def dom_top_headings(md_text):
    """アプリと同じパイプライン (markdown → サニタイズ) を通した結果から
    トップレベル見出しを拾う。サニタイズを通さないと、見出し内の生 HTML が
    パーサの深さ計算を狂わせて誤検出になる。"""
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html = _sanitize_html(html)
    p = TopLevelHeadings()
    p.feed(html)
    return p.items


FAIL = []
PASS = 0


def check(name, cond, detail=""):
    global PASS
    if cond:
        PASS += 1
    else:
        FAIL.append(f"{name}: {detail}")


# ══════════════════════════════════════════════════════════════
# 1. _extract_headings が実レンダリング結果と一致するか
# ══════════════════════════════════════════════════════════════
HEADING_CASES = [
    ("ATX基本", "# A\n\ntext\n\n## B\n\n### C\n"),
    ("スペースなしATX", "#A\n\ntext\n\n##B\n"),
    ("Setext H1", "Title\n=====\n\ntext\n"),
    ("Setext H2", "Title\n-----\n\ntext\n"),
    ("Setext混在", "# A\n\nSet1\n====\n\n## B\n\nSet2\n----\n"),
    ("引用内見出し(除外対象)", "# A\n\n> # inner\n\n## B\n"),
    ("リスト内見出し(除外対象)", "# A\n\n- item\n\n## B\n"),
    ("フェンス内の#", "# A\n\n```\n# not heading\n```\n\n## B\n"),
    ("チルダフェンス内の#", "# A\n\n~~~\n# not heading\n~~~\n\n## B\n"),
    ("末尾#付き", "## Trailing ##\n\ntext\n"),
    ("H6", "###### six\n\ntext\n"),
    ("7個の#", "####### seven\n\ntext\n"),
    ("空見出し", "#\n\ntext\n"),
    ("テーブル直後", "| A | B |\n|---|---|\n| 1 | 2 |\n\n## After\n"),
    ("HR直後", "para\n\n---\n\n## After\n"),
    ("リスト直後のダッシュ", "- item\n---\n\n## After\n"),
    ("インデントATX(段落扱い)", "  # indented\n\n## Real\n"),
    ("連続見出し", "# A\n## B\n### C\n"),
    ("日本語見出し", "# 見出し壱\n\n本文\n\n## 見出し弐\n"),
    ("記号入り見出し", "# A & B <c> \"d\"\n\ntext\n"),
    ("空文書", ""),
    ("見出しなし", "just text\n\nmore text\n"),
    ("フェンス未閉鎖", "# A\n\n```\n# inside unterminated\n"),
    ("Setext候補が最終行", "# A\n\nTrailing\n===\n"),
    ("フェンス未閉鎖(チルダ)", "# A\n\n~~~\n# inside\n"),
    ("フェンス open3 close4 (閉じない)", "# A\n\n```\ncode\n````\n\n# after\n"),
    ("フェンス open4 close3 (閉じない)", "# A\n\n````\ncode\n```\n\n# after\n"),
    ("フェンス open4 close4", "# A\n\n````\n# code\n````\n\n# after\n"),
    ("フェンス記号混在(閉じない)", "# A\n\n~~~\n# code\n```\n\n# after\n"),
    ("閉じフェンスに末尾空白", "# A\n\n```\n# code\n```   \n\n# after\n"),
    ("フェンス複数(2つ目未閉鎖)", "```\n# c1\n```\n\n# B\n\n```\n# c2 unterminated\n"),
    ("フェンス言語指定", "# A\n\n```python\n# comment\n```\n\n# after\n"),
    ("インデントされたフェンス", "# A\n\n  ```\n# code\n  ```\n\n# after\n"),
    # 字下げコードブロック (4スペース) 内は見出しにならない
    ("字下げコード内の#", "# A\n\n    # not a heading\n\n# after\n"),
    ("字下げコード内のSetext", "# A\n\n    title: x\n    ---\n\n# after\n"),
    ("字下げコード内のSetextH1", "# A\n\n    title: x\n    ===\n\n# after\n"),
    ("字下げコード(タブ)", "# A\n\n\t# not a heading\n\n# after\n"),
    ("字下げコードに空行を含む", "# A\n\n    code1\n\n    code2\n\n# after\n"),
    ("段落直後の字下げ行(継続行)", "# A\n\npara\n    continued\n\n# after\n"),
    ("字下げコードが文書先頭", "    # code\n\n# after\n"),
    ("3スペースは見出しのまま", "   # indented three\n\n# after\n"),
]

for name, doc in HEADING_CASES:
    got = [(lv, t) for lv, t, _ in _extract_headings(doc)]
    want = dom_top_headings(doc)
    check(f"[heading] {name}",
          [lv for lv, _ in got] == [lv for lv, _ in want],
          f"got={got} want={want}")

# 行番号が実在する行を指しているか
for name, doc in HEADING_CASES:
    lines = doc.split("\n")
    for lv, t, ln in _extract_headings(doc):
        check(f"[heading-lineno] {name}", 0 <= ln < len(lines),
              f"line {ln} out of range (len={len(lines)})")


# ══════════════════════════════════════════════════════════════
# 2. HTML → Markdown 変換 (MD編集モードの往復)
# ══════════════════════════════════════════════════════════════
H2M_CASES = [
    ("正常なOL", '<p>Intro</p><ol><li>A</li><li>B</li></ol><p>After</p>',
     ["1. A", "2. B"]),
    ("正常なUL", '<p>Intro</p><ul><li>A</li><li>B</li></ul><p>After</p>',
     ["- A", "- B"]),
    ("p内にOL(不正入れ子)", '<p><ol><li>A</li><li>B</li></ol></p><p>After</p>',
     ["1. A", "2. B"]),
    ("p入れ子+OL", '<p><ol><li>Only</li></ol><p>After</p></p>',
     ["1. Only", "After"]),
    ("孤立br", '<ol><li>A</li></ol><p>B</p><br><p>C</p>', ["1. A"]),
    ("見出し", '<h1>A</h1><p>x</p><h2>B</h2>', ["# A", "## B"]),
    ("強調", '<p><strong>b</strong> <em>i</em> <s>s</s></p>', ["**b**", "*i*", "~~s~~"]),
    ("コードブロック言語付き", '<pre><code class="language-python">x=1\n</code></pre>',
     ["```python"]),
    ("テーブル", '<table><thead><tr><th>A</th><th>B</th></tr></thead>'
                 '<tbody><tr><td>1</td><td>2</td></tr></tbody></table>',
     ["| A | B |", "| --- | --- |"]),
    ("リンク", '<p><a href="https://x.test">t</a></p>', ["[t](https://x.test)"]),
    ("画像", '<p><img src="a.png" alt="alt"></p>', ["![alt](a.png)"]),
    ("引用", '<blockquote><p>q</p></blockquote>', ["> "]),
    ("HR", '<p>a</p><hr><p>b</p>', ["---"]),
    ("ネストOL", '<ol><li>A<ol><li>A1</li></ol></li></ol>', ["1. A", "1. A1"]),
]

for name, html, expects in H2M_CASES:
    out = _html_to_md(html)
    for e in expects:
        check(f"[html2md] {name}", e in out, f"expected {e!r} in {out!r}")

# 往復: HTML → MD → HTML でリスト項目数が保たれるか
ROUNDTRIP = [
    '<ol><li>A</li><li>B</li><li>C</li></ol>',
    '<p><ol><li>A</li><li>B</li><li>C</li></ol></p>',
    '<ul><li>A</li><li>B</li></ul>',
    '<h1>T</h1><ol><li>A</li><li>B</li></ol><p>tail</p>',
]
for html in ROUNDTRIP:
    md = _html_to_md(html)
    back = markdown.markdown(md, extensions=["tables", "fenced_code"])
    n_in = html.count("<li>")
    n_out = back.count("<li>")
    check("[roundtrip] li count", n_in == n_out,
          f"{html!r} -> md={md!r} -> {back!r} ({n_in} vs {n_out})")

# 番号が 1,2,3 と振られるか (1. のまま止まらないか)
md = _html_to_md('<ol><li>A</li><li>B</li><li>C</li></ol>')
check("[roundtrip] OL採番", "1. A" in md and "2. B" in md and "3. C" in md,
      f"md={md!r}")


# ══════════════════════════════════════════════════════════════
# 3. TXT編集プレビュー同期 (行 ⇔ ブロック対応)
# ══════════════════════════════════════════════════════════════
SYNC_CASES = [
    "# H\n\npara one\n\npara two\n",
    "- a\n- b\n\npara\n",
    "1. a\n2. b\n\npara\n",
    "```\ncode\n```\n\npara\n",
    "| A | B |\n|---|---|\n| 1 | 2 |\n\npara\n",
    "> quote\n\npara\n",
    "para\n\n---\n\npara2\n",
    "",
    "single line",
    "# H\n\n```\nunterminated fence\n",
    "# H\n\n  ```\nindented fence\n  ```\n\npara\n",
    "# H\n\npara with ``` inline\n\npara2\n",
    "```\ncode\n```\n\n# H2\n\npara\n",
]


def dom_top_element_count(md_text):
    """レンダリング結果のトップレベル要素数 (data-src-line が振られる対象数)。"""
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html = _sanitize_html(html)

    class Counter(HTMLParser):
        def __init__(self):
            super().__init__()
            self.depth = 0
            self.n = 0

        def handle_starttag(self, tag, attrs):
            if self.depth == 0:
                self.n += 1
            self.depth += 1

        def handle_startendtag(self, tag, attrs):
            if self.depth == 0:
                self.n += 1

        def handle_endtag(self, tag):
            self.depth = max(0, self.depth - 1)

    c = Counter()
    c.feed(html)
    return c.n


for doc in SYNC_CASES:
    starts = _split_source_blocks(doc)
    n_dom = dom_top_element_count(doc)
    # ブロック数が DOM のトップレベル要素数と一致しないと、data-src-line の
    # 割り当てが順にずれ、TXT編集モードのハイライトが別の段落に当たる
    check("[sync] ブロック数=DOM要素数", len(starts) == n_dom,
          f"doc={doc!r} blocks={len(starts)} dom={n_dom} starts={starts}")
for doc in SYNC_CASES:
    starts = _split_source_blocks(doc)
    lines = doc.split("\n")
    check("[sync] 行番号が範囲内", all(0 <= s < max(1, len(lines)) for s in starts),
          f"doc={doc!r} starts={starts}")
    check("[sync] 単調増加", starts == sorted(starts), f"starts={starts}")
    body = markdown.markdown(doc, extensions=["tables", "fenced_code"])
    tagged = _tag_src_lines(body, starts)
    check("[sync] タグ付けで本文が壊れない",
          tagged.count("<") >= body.count("<"),
          f"body={body!r} tagged={tagged!r}")
    # data-src-line の値がすべて有効な行番号か
    for m in re.finditer(r'data-src-line="(\d+)"', tagged):
        check("[sync] data-src-line 範囲", 0 <= int(m.group(1)) < max(1, len(lines)),
              f"{m.group(1)} out of range for {doc!r}")


# ══════════════════════════════════════════════════════════════
# 4. TXT編集モードのリストトグル (main.py の正規表現をそのまま検証)
# ══════════════════════════════════════════════════════════════
def toggle_ordered(line, prev_line=None):
    m = re.match(r'^(\s*)\d+\.\s+(.*)$', line)
    if m:
        return m.group(1) + m.group(2)
    indent = re.match(r'^(\s*)', line).group(1)
    content = line[len(indent):]
    n = 1
    if prev_line is not None:
        pm = re.match(r'^(\s*)(\d+)\.\s+', prev_line)
        if pm and pm.group(1) == indent:
            n = int(pm.group(2)) + 1
    return f"{indent}{n}. {content}"


def toggle_unordered(line):
    m = re.match(r'^(\s*)[-*+]\s+(.*)$', line)
    if m:
        return m.group(1) + m.group(2)
    indent = re.match(r'^(\s*)', line).group(1)
    return f"{indent}- {line[len(indent):]}"


check("[toggle] 番号付与", toggle_ordered("Alpha") == "1. Alpha", toggle_ordered("Alpha"))
check("[toggle] 連番", toggle_ordered("Beta", "1. Alpha") == "2. Beta",
      toggle_ordered("Beta", "1. Alpha"))
check("[toggle] 連番(10以上)", toggle_ordered("K", "9. J") == "10. K",
      toggle_ordered("K", "9. J"))
check("[toggle] 番号解除", toggle_ordered("1. Alpha") == "Alpha", toggle_ordered("1. Alpha"))
check("[toggle] 番号解除(2桁)", toggle_ordered("12. Alpha") == "Alpha",
      toggle_ordered("12. Alpha"))
check("[toggle] インデント保持", toggle_ordered("  Alpha") == "  1. Alpha",
      toggle_ordered("  Alpha"))
check("[toggle] インデント違いは連番にしない",
      toggle_ordered("  Beta", "1. Alpha") == "  1. Beta",
      toggle_ordered("  Beta", "1. Alpha"))
check("[toggle] 空行に番号", toggle_ordered("") == "1. ", repr(toggle_ordered("")))
check("[toggle] トグル往復", toggle_ordered(toggle_ordered("Alpha")) == "Alpha",
      toggle_ordered(toggle_ordered("Alpha")))
check("[toggle] 箇条書き付与", toggle_unordered("Alpha") == "- Alpha", toggle_unordered("Alpha"))
check("[toggle] 箇条書き解除", toggle_unordered("- Alpha") == "Alpha", toggle_unordered("- Alpha"))
check("[toggle] 箇条書き解除(*)", toggle_unordered("* Alpha") == "Alpha",
      toggle_unordered("* Alpha"))
check("[toggle] 箇条書き往復", toggle_unordered(toggle_unordered("A")) == "A",
      toggle_unordered(toggle_unordered("A")))
# 生成した Markdown が実際にリストとして描画されるか
for line in ["1. Alpha", "- Alpha", "  1. Alpha"]:
    check("[toggle] 生成MDがリストになる", "<li>" in markdown.markdown(line),
          f"{line!r} -> {markdown.markdown(line)!r}")


# ══════════════════════════════════════════════════════════════
# 5. LaTeX 数式 (v1.4.1)
# ══════════════════════════════════════════════════════════════
TEX_CASES = [
    ("上下付き",        r"x^2 + y_1",                      ["mdv-sup", "mdv-sub"]),
    ("分数",            r"\frac{a}{b}",                    ["mdv-frac-n", "mdv-frac-d"]),
    ("総和(display)",   r"\sum_{i=1}^{n} i",               ["mdv-lim-up", "mdv-lim-lo"]),
    ("積分",            r"\int_0^\infty e^{-x}\,dx",       ["mdv-bigop-int", "∞"]),
    ("根号",            r"\sqrt{x}",                       ["mdv-sqrt-body"]),
    ("n乗根",           r"\sqrt[3]{x}",                    ["mdv-sqrt-idx"]),
    ("行列",            r"\begin{pmatrix}a&b\\c&d\end{pmatrix}",
                                                           ["mdv-mtx", "mdv-d-lparen"]),
    ("場合分け",        r"\begin{cases}1&x>0\\0&x\le 0\end{cases}", ["mdv-mtx"]),
    ("伸縮括弧",        r"\left(\frac{1}{2}\right)",       ["mdv-fence", "mdv-d-rparen"]),
    ("ギリシャ文字",    r"\alpha\beta\Gamma",              ["α", "β", "Γ"]),
    ("黒板太字",        r"\mathbb{R}",                     ["ℝ"]),
    ("アクセント",      r"\hat{x}\vec{v}\bar{y}",          ["mdv-acc"]),
    ("立体関数名",      r"\sin x + \log y",                ["mdv-fn"]),
    ("極限",            r"\lim_{x\to 0}",                  ["mdv-lim"]),
    ("二項係数",        r"\binom{n}{k}",                   ["mdv-frac-nb"]),
    ("整列環境",        r"\begin{aligned}a&=b\\&=c\end{aligned}", ["mdv-mtx"]),
    ("角括弧は式の一部", r"[0,1]",                          ["[", "]"]),
    ("テキスト",        r"\text{hello world}",             ["hello world"]),
]
for name, tex, expects in TEX_CASES:
    html = _render_tex(tex, True)
    check(f"[tex] {name} 未フォールバック", "mdv-tex-raw" not in html, f"{tex} -> {html}")
    for e in expects:
        check(f"[tex] {name}", e in html, f"expected {e!r} in {html!r}")

# 生成 HTML のタグ対応が取れているか (壊れた HTML を吐かない)
class TagBalance(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.ok = True

    def handle_starttag(self, tag, attrs):
        if tag not in ("br", "hr", "img", "input"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.ok = False


for name, tex, _ in TEX_CASES:
    for disp in (True, False):
        p = TagBalance()
        p.feed(_render_tex(tex, disp))
        check(f"[tex] {name} タグ対応", p.ok and not p.stack,
              f"unbalanced: {tex!r} display={disp}")

# 未対応コマンドでも原文が残る (黙って消えない)
check("[tex] 未対応コマンドを残す", "unknowncmd" in _render_tex(r"\unknowncmd", False),
      _render_tex(r"\unknowncmd", False))
# 空/壊れた入力でも例外を出さない
for bad in ["", "   ", r"\frac{", r"\begin{pmatrix}", "}" * 50, "^" * 50, r"\left("]:
    try:
        _render_tex(bad, False)
        check("[tex] 異常入力で例外なし", True)
    except Exception as e:
        check("[tex] 異常入力で例外なし", False, f"{bad!r}: {e}")

# ─── 数式の抽出 (Markdown 変換前の退避) ───
MATH_DOC = (
    "# T\n\n"
    "Inline $a^2+b^2=c^2$ text.\n\n"
    "Cost is $5 and $10 total.\n\n"
    "$$\nE = mc^2\n$$\n\n"
    "```python\nx = \"$notmath$\"\n```\n\n"
    "Span `$a$` kept.\n"
)
out, store = _extract_math(MATH_DOC)
check("[math] 抽出数", len(store) == 2, f"store={store}")
check("[math] 通貨は数式にしない", "$5 and $10" in out, out)
check("[math] フェンス内は対象外", '"$notmath$"' in out, out)
check("[math] コードスパンは対象外", "`$a$`" in out, out)
check("[math] display 判定", store[1][0] is True and "mc^2" in store[1][1], f"{store}")
check("[math] inline 判定", store[0][0] is False, f"{store}")
# 退避 → Markdown → サニタイズ → 復元 で数式が戻るか
_body = _sanitize_html(markdown.markdown(out, extensions=["tables", "fenced_code"]))
_body = _restore_math(_body, store)
check("[math] 復元後に数式HTMLがある", _body.count('data-tex="') == 2, _body)
check("[math] display 用クラスが付く", _body.count("mdv-math-display") == 1, _body)
check("[math] プレースホルダが残らない", "\ue000" not in _body and "\ue001" not in _body, _body)

# 数式なしの文書は素通し
_o, _s = _extract_math("# no math here\n\njust text\n")
check("[math] 数式なしで無変更", _o == "# no math here\n\njust text\n" and _s == [], repr(_o))

# 通貨表記の直後にコードスパンがあっても巻き込まない
_o2, _s2 = _extract_math("金額の $5 と $10 です。`$x$` も同様。\n")
check("[math] コードスパンの $ を閉じ記号にしない", _s2 == [], f"{_s2}")
check("[math] 本文が変わらない", _o2 == "金額の $5 と $10 です。`$x$` も同様。\n", repr(_o2))
# 単独の $ が閉じないまま行末に来ても本文を壊さない
_o3, _s3 = _extract_math("価格は $100 でした。\n\n次の段落。\n")
check("[math] 閉じない $ は素通し", _s3 == [], f"{_s3}")

# MD編集モードの逆変換: data-tex から $...$ を復元する
_md_back = _html_to_md('<p>a ' + _render_tex("x^2", False) + ' b</p>')
check("[math] HTML→MD で $ 記法に戻る", "$x^2$" in _md_back, _md_back)
_md_back2 = _html_to_md(_render_tex("E=mc^2", True))
check("[math] display は $$ に戻る", "$$E=mc^2$$" in _md_back2, _md_back2)


# ══════════════════════════════════════════════════════════════
# 6. YAML フロントマター (v1.4.1)
# ══════════════════════════════════════════════════════════════
FM_DOC = "---\ntitle: Hello\ntags:\n  - a\n  - b\n---\n\n# Body\n\ntext\n"
fm, body, off = _split_front_matter(FM_DOC)
check("[yaml] フロントマター抽出", fm is not None and "title: Hello" in fm, repr(fm))
check("[yaml] 本文の切り出し", body.lstrip().startswith("# Body"), repr(body))
check("[yaml] 本文開始行", FM_DOC.split("\n")[off] == "", f"off={off}")
check("[yaml] フロントマターなしは素通し",
      _split_front_matter("# A\n\ntext")[0] is None)
check("[yaml] 閉じないブロックは素通し",
      _split_front_matter("---\ntitle: x\n\n# A")[0] is None)
check("[yaml] 水平線だけの行は誤検出しない",
      _split_front_matter("---\n\ntext")[0] is None)

parsed = _parse_simple_yaml("title: Hello\ncount: 3\ntags:\n  - a\n  - b\n")
check("[yaml] マッピング解析", parsed.get("title") == "Hello", parsed)
check("[yaml] 並び解析", parsed.get("tags") == ["a", "b"], parsed)
parsed2 = _parse_simple_yaml('name: "quoted: value"\n# comment\nother: 1\n')
check("[yaml] 引用文字列", parsed2.get("name") == "quoted: value", parsed2)
check("[yaml] コメント無視", "# comment" not in parsed2, parsed2)
nested = _parse_simple_yaml("author:\n  name: Y\n  mail: a@b.test\n")
check("[yaml] ネスト", isinstance(nested.get("author"), dict)
      and nested["author"].get("name") == "Y", nested)
for bad in ["", ":::", "- - -", "a:\n b:\n  c:\n", "\t\t\n"]:
    try:
        _parse_simple_yaml(bad)
        check("[yaml] 異常入力で例外なし", True)
    except Exception as e:
        check("[yaml] 異常入力で例外なし", False, f"{bad!r}: {e}")

_fm_html = _front_matter_html("title: Hello\ntags:\n  - a\n", "Front matter")
_p = TagBalance()
_p.feed(_fm_html)
check("[yaml] パネルHTMLのタグ対応", _p.ok and not _p.stack, _fm_html)
check("[yaml] 原文を data-fm に保持", 'data-fm="' in _fm_html, _fm_html)
check("[yaml] HTML→MD でブロックが戻る",
      _html_to_md(_fm_html).startswith("---\ntitle: Hello"), _html_to_md(_fm_html))

# フロントマターの `---` を Setext 見出しと誤検出しない (v1.4.0 の不具合)
_heads = _extract_headings(FM_DOC)
check("[yaml] 目次にフロントマターが混ざらない",
      [t for _, t, _ in _heads] == ["Body"], _heads)


# ══════════════════════════════════════════════════════════════
print("=" * 60)
print(f"PASS: {PASS}   FAIL: {len(FAIL)}")
if FAIL:
    print("-" * 60)
    for f in FAIL:
        print("  FAIL", f)
    sys.exit(1)
print("すべて成功")
