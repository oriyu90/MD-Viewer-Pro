"""v1.4.3 純粋関数 回帰テストハーネス.

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

# mermaid ダイアグラム抽出/復元 (同じ範囲に含まれる)
_extract_mermaid = ns["_extract_mermaid"]
_restore_mermaid = ns["_restore_mermaid"]
_hex_is_dark     = ns["_hex_is_dark"]

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
# v1.4.2 回帰: 改行の保持 と HTML→Markdown 往復
# ══════════════════════════════════════════════════════════════
# アプリ本体と同じ拡張構成 (_build_md_html 参照)
MD_EXTS = ["tables", "fenced_code", "nl2br"]


def render(md_text):
    """閲覧 / HTML書き出し / PDF書き出しと同じ描画パイプライン。"""
    return _sanitize_html(markdown.markdown(md_text, extensions=MD_EXTS))


def roundtrip(md_text):
    """MD編集モードの往復 (Markdown → HTML → Markdown)。"""
    return _html_to_md(render(md_text))


# ── 単一改行が本文として保持されるか (v1.4.1 では消えていた) ──
_nl_doc = "こんにちは\n今日はいい天気です\nさようなら"
_nl_html = render(_nl_doc)
check("[改行] 単一改行が <br> になる", _nl_html.count("<br") == 2, _nl_html)
check("[改行] 段落が分割されない", _nl_html.count("<p>") == 1, _nl_html)
check("[改行] 本文が失われない",
      all(s in _nl_html for s in ("こんにちは", "今日はいい天気です", "さようなら")), _nl_html)

# 見出し・コード・表の中では改行を <br> にしない
check("[改行] コードブロック内は <br> にしない",
      "<br" not in render("```\na\nb\n```"), render("```\na\nb\n```"))
_tbl_html = render("| a | b |\n| --- | --- |\n| 1 | 2 |")
check("[改行] 表の行を <br> で壊さない",
      "<br" not in _tbl_html and "<table>" in _tbl_html, _tbl_html)

# ── 往復が安定し、書式が失われないか ──
ROUNDTRIP_CASES = [
    ("改行", "行1\n行2\n行3"),
    ("段落", "段落A\n\n段落B"),
    ("見出しと本文", "# 見出し\n\n本文1\n本文2"),
    ("箇条書き", "- a\n- b\n- c"),
    ("番号付き", "1. one\n2. two"),
    ("入れ子の箇条書き", "- a\n    - a1\n    - a2\n- b"),
    ("チェックボックス", "- [ ] todo\n- [x] done"),
    ("引用", "> 引用1\n> 引用2"),
    ("複数段落の引用", "> 引用1\n> 引用2\n\n> 別の引用"),
    ("表", "| a | b |\n| --- | --- |\n| 1 | 2 |"),
    ("コード", "```python\nx = 1\ny = 2\n```"),
    ("水平線", "1. a\n2. b\n\n---\n\n最後"),
    ("強調とリンク", "- [リンク](http://example.com) と *強調*\n- 次"),
    ("混在", "# H\n\n本文1\n本文2\n\n- x\n    - y\n- z\n\n> 引用\n\n| a | b |\n"
             "| --- | --- |\n| 1 | 2 |"),
]
for _name, _src in ROUNDTRIP_CASES:
    _r1 = roundtrip(_src)
    _r2 = roundtrip(_r1)
    check(f"[往復] {_name}: 2周目で変化しない", _r1 == _r2, f"{_r1!r} -> {_r2!r}")

# ── Enter で入れた空行が保存され、開き直しても残るか ──
#    素の空行は Markdown が無視するため、<br> だけの行として書き出す。
EMPTY_P_CASES = [
    ("Enter 1回", '<p>行A</p><p><br></p><p>行B</p>', "行A\n\n<br>\n\n行B"),
    ("Enter 2回", '<p>行A</p><p><br></p><p><br></p><p>行B</p>',
     "行A\n\n<br>\n\n<br>\n\n行B"),
    ("空の div", '<p>行A</p><div><br></div><p>行B</p>', "行A\n\n<br>\n\n行B"),
    ("完全に空の p", '<p>行A</p><p></p><p>行B</p>', "行A\n\n<br>\n\n行B"),
]
for _name, _html, _want in EMPTY_P_CASES:
    _got = _html_to_md(_html)
    check(f"[空行] {_name}: 空行が保存される", _got == _want,
          f"{_got!r} (期待 {_want!r})")

# 書き出した空行が、開き直したときに実際に空の段落として描画されるか
_blank_html = render("行A\n\n<br>\n\n行B")
check("[空行] 開き直すと空の段落になる", _blank_html.count("<p>") == 3, _blank_html)
check("[空行] 素の空行を増やしても Markdown は無視する",
      render("行A\n\n\n\n行B").count("<p>") == 2, render("行A\n\n\n\n行B"))
# 往復しても増えたり消えたりしない
for _name, _src in [("空行1つ", "行A\n\n<br>\n\n行B"),
                    ("空行2つ", "行A\n\n<br>\n\n<br>\n\n行B")]:
    _r1 = roundtrip(_src)
    _r2 = roundtrip(_r1)
    check(f"[空行] {_name}: 往復で変化しない", _r1 == _r2 == _src,
          f"{_src!r} -> {_r1!r} -> {_r2!r}")

# 中身のある段落を空行と誤判定しない
for _name, _html in [("文字", '<p>あ</p>'), ("画像", '<p><img src="x.png" alt=""></p>'),
                     ("強調のみ", '<p><strong>太字</strong></p>')]:
    check(f"[空行] {_name}のある段落は <br> にしない",
          "<br>" not in _html_to_md(_html), _html_to_md(_html))

# 個別に「壊れていないこと」を明示的に押さえる
check("[往復] 改行が段落に化けない", roundtrip("行1\n行2") == "行1\n行2",
      repr(roundtrip("行1\n行2")))
check("[往復] 箇条書きが loose 化しない", roundtrip("- a\n- b") == "- a\n- b",
      repr(roundtrip("- a\n- b")))
check("[往復] 引用符が各行に残る", roundtrip("> 引用1\n> 引用2") == "> 引用1\n> 引用2",
      repr(roundtrip("> 引用1\n> 引用2")))
check("[往復] 入れ子リストの階層が保たれる",
      roundtrip("- a\n    - a1\n- b") == "- a\n    - a1\n- b",
      repr(roundtrip("- a\n    - a1\n- b")))
check("[往復] 表がそのまま戻る",
      roundtrip("| a | b |\n| --- | --- |\n| 1 | 2 |")
      == "| a | b |\n| --- | --- |\n| 1 | 2 |",
      repr(roundtrip("| a | b |\n| --- | --- |\n| 1 | 2 |")))
check("[往復] コードの言語指定が残る",
      roundtrip("```python\nx = 1\n```") == "```python\nx = 1\n```",
      repr(roundtrip("```python\nx = 1\n```")))
# 表セル内の改行は <br> のまま (Markdown の表は複数行にできないため)
check("[往復] 表セル内の <br> を保持",
      "<br>" in roundtrip("| a | b |\n| --- | --- |\n| 1<br>2 | 3 |"),
      repr(roundtrip("| a | b |\n| --- | --- |\n| 1<br>2 | 3 |")))

# data-src-line の付与が <br> で狂わないこと (行同期 / スクロール引き継ぎ用)
_tagged = _tag_src_lines(render("行1\n行2\n\n次の段落\n続き"), [0, 3])
check("[改行] <br> があっても data-src-line が全ブロックに付く",
      _tagged.count('data-src-line=') == 2, _tagged)

# ══════════════════════════════════════════════════════════════
# v1.4.5 回帰: コード内の空行が保存で失われないこと
#   逆変換後の全文圧縮 (\n{3,} → \n\n) がフェンス内にも効いていたため、
#   コードの中の連続空行が往復のたびに 1 行に詰まっていた。
#   圧縮は段落境界の正規化が目的なので、コード区間は素通しする。
# ══════════════════════════════════════════════════════════════
check("[往復] コード内の連続空行が残る",
      roundtrip("```python\na = 1\n\n\n\nb = 2\n```")
      == "```python\na = 1\n\n\n\nb = 2\n```",
      repr(roundtrip("```python\na = 1\n\n\n\nb = 2\n```")))
check("[往復] コード先頭の空行が残る",
      roundtrip("```python\n\nx = 1\n```") == "```python\n\nx = 1\n```",
      repr(roundtrip("```python\n\nx = 1\n```")))
check("[往復] コード末尾の空行が残る",
      roundtrip("```python\nx = 1\n\n```") == "```python\nx = 1\n\n```",
      repr(roundtrip("```python\nx = 1\n\n```")))
check("[往復] 全行が空行のコードが残る",
      roundtrip("```\n\n\n```") == "```\n\n\n```",
      repr(roundtrip("```\n\n\n```")))
# コード以外 (段落間) の 3 連以上は従来どおり 2 連へ正規化する
check("[空行] 段落間の 3 連以上は 2 連へ正規化される",
      roundtrip("A\n\n\n\nB") == "A\n\nB",
      repr(roundtrip("A\n\n\n\nB")))


# ══════════════════════════════════════════════════════════════
# v1.4.2 回帰: TXT編集モードの行頭マーカー処理
# ══════════════════════════════════════════════════════════════
_bm = extract("_BLOCK_MARKER_RE = re.compile(", "\nI18N = {")
exec(_bm, ns)
_sbm_src = extract("    def _split_block_markers(line: str):", "    def _current_line(self):")
_sbm_src = "\n".join(l[4:] if l.startswith("    ") else l
                     for l in _sbm_src.split("\n"))
exec(_sbm_src, ns)
_split_block_markers = ns["_split_block_markers"]


def body_of(line):
    """本文ボタン (_md_body) と同じ結果を返す。"""
    indent, _markers, rest = _split_block_markers(line)
    return indent + rest


def set_block(line, prefix):
    """見出し/引用ボタン (_md_set_block) と同じ結果を返す。"""
    indent, markers, rest = _split_block_markers(line)
    same = (len(markers) == 1 and markers[0].rstrip() == prefix.rstrip())
    return indent + rest if same else indent + prefix + rest


BODY_CASES = [
    ("見出し", "# 見出し", "見出し"),
    ("深い見出し", "###### 見出し", "見出し"),
    ("引用", "> 引用", "引用"),
    ("箇条書き", "- 項目", "項目"),
    ("番号付き", "1. 項目", "項目"),
    ("チェック済み", "- [x] やること", "やること"),
    ("未チェック", "- [ ] やること", "やること"),
    ("積み重なった書式", "## # 本文", "本文"),
    ("引用の中の見出し", "> # 見出し", "見出し"),
    ("インデント保持", "    ## 本文", "    本文"),
    ("空の見出し", "# ", ""),
    ("本文はそのまま", "ただの本文", "ただの本文"),
    # markdown は空白なしの "#" も見出しとして描画するので本文ボタンでも外す
    ("空白なしの見出し", "#見出し", "見出し"),
    ("空白なしの引用", ">引用", "引用"),
    # 逆に空白のない "-" や "1." は markdown もリストにしないので触らない
    ("空白なしのハイフンは本文", "-ハイフン", "-ハイフン"),
    ("空白なしの番号は本文", "1.番号", "1.番号"),
]
for _name, _src, _want in BODY_CASES:
    check(f"[本文] {_name}", body_of(_src) == _want,
          f"{_src!r} -> {body_of(_src)!r} (期待 {_want!r})")

SET_BLOCK_CASES = [
    ("本文に H1", "本文", "# ", "# 本文"),
    ("H1 を H2 に置き換え", "# 本文", "## ", "## 本文"),
    ("H2 を H1 に置き換え", "## 本文", "# ", "# 本文"),
    ("同じ書式でトグル解除", "# 本文", "# ", "本文"),
    ("引用を見出しに置き換え", "> 本文", "## ", "## 本文"),
    ("見出しを引用に置き換え", "### 本文", "> ", "> 本文"),
    ("積み重なった書式を1つに", "## # 本文", "# ", "# 本文"),
    ("インデント保持", "    本文", "## ", "    ## 本文"),
    ("空行に見出し", "", "# ", "# "),
]
for _name, _src, _pre, _want in SET_BLOCK_CASES:
    check(f"[書式] {_name}", set_block(_src, _pre) == _want,
          f"{_src!r} +{_pre!r} -> {set_block(_src, _pre)!r} (期待 {_want!r})")

# 書式ボタンを続けて押しても積み重ならない
_line = "本文"
for _pre in ("# ", "## ", "### ", "> ", "## "):
    _line = set_block(_line, _pre)
check("[書式] 連打しても積み重ならない", _line == "## 本文", repr(_line))
check("[書式] その後 本文 で必ず戻る", body_of(_line) == "本文", repr(body_of(_line)))


# ══════════════════════════════════════════════════════════════
# v1.4.2 回帰: LaTeX の体裁コマンド (\newpage 等)
# ══════════════════════════════════════════════════════════════
_extract_tex_layout = ns["_extract_tex_layout"]
_restore_tex_layout = ns["_restore_tex_layout"]
_tex_length_to_css  = ns["_tex_length_to_css"]


def render_layout(md_text):
    """アプリと同じ順序 (数式 → 体裁コマンド) で描画する。"""
    s, mstore = _extract_math(md_text)
    s, lstore = _extract_tex_layout(s)
    body = _sanitize_html(markdown.markdown(s, extensions=MD_EXTS))
    return _restore_tex_layout(_restore_math(body, mstore), lstore)


def layout_roundtrip(md_text):
    return _html_to_md(render_layout(md_text))


# ── 改ページとして解釈されるコマンド ──
for _cmd in ("\\newpage", "\\pagebreak", "\\clearpage", "\\cleardoublepage",
             "\\pagebreak[4]"):
    _h = render_layout("前\n\n" + _cmd + "\n\n後")
    check(f"[体裁] {_cmd} が改ページ要素になる", 'class="mdv-texcmd mdv-newpage"' in _h, _h)
    check(f"[体裁] {_cmd} の文字列が残らない",
          _cmd.split("[")[0][1:] not in _h.replace("mdv-newpage", "")
          .replace(f'data-tex="{_cmd}"', ""), _h)
    check(f"[体裁] {_cmd} が <p> に包まれない", "<p><div" not in _h, _h)

# ── 縦の空き ──
_h = render_layout("前\n\n\\vspace{1cm}\n\n後")
check("[体裁] \\vspace が高さを持つ", 'style="height:1cm"' in _h, _h)
for _cmd, _px in (("\\bigskip", "12pt"), ("\\medskip", "6pt"), ("\\smallskip", "3pt")):
    _h = render_layout(_cmd + "\n\n本文")
    check(f"[体裁] {_cmd} の空き", f'style="height:{_px}"' in _h, _h)

LEN_CASES = [("1cm", "1cm"), ("0.5in", "0.5in"), ("12pt", "12pt"), ("2em", "2em"),
             ("10px", "10px"), ("1\\baselineskip", "1.5em"), ("3", "0"),
             ("bogus", "0"), ("", "0")]
for _src, _want in LEN_CASES:
    check(f"[体裁] 長さ {_src!r} → {_want}", _tex_length_to_css(_src) == _want,
          f"{_src!r} -> {_tex_length_to_css(_src)!r}")

# ── 改行系 ──
for _cmd in ("\\newline", "\\linebreak"):
    _h = render_layout("行1" + _cmd + "行2")
    check(f"[体裁] {_cmd} が改行になる", "mdv-texbr" in _h and "<br/>" in _h, _h)
    check(f"[体裁] {_cmd} の後ろの本文が残る", "行2" in _h, _h)

# ── 表示に反映できないコマンドは隠すだけ ──
_h = render_layout("\\noindent 字下げなし")
check("[体裁] \\noindent は隠れる", 'class="mdv-texcmd"' in _h and "noindent" not in
      _h.replace('data-tex="\\noindent"', ""), _h)
check("[体裁] \\noindent の後ろの本文が残る", "字下げなし" in _h, _h)

# ── 対象外にすべきもの ──
_h = render_layout("説明: `\\newpage` と書きます")
check("[体裁] インラインコード内は触らない",
      "<code>\\newpage</code>" in _h and "mdv-newpage" not in _h, _h)
_h = render_layout("```\n\\newpage\n```")
check("[体裁] コードブロック内は触らない",
      "\\newpage" in _h and "mdv-newpage" not in _h, _h)
_h = render_layout("数式 $\\newpage$ です")
check("[体裁] 数式の中は数式のまま", "mdv-math" in _h and "mdv-newpage" not in _h, _h)
_h = render_layout("\\parbox は別コマンド")
check("[体裁] \\parbox を \\par と誤認しない", "mdv-texcmd" not in _h, _h)
_h = render_layout("未対応の \\unknowncmd はそのまま")
check("[体裁] 未対応コマンドは消さずに残す",
      "\\unknowncmd" in _h and "mdv-texcmd" not in _h, _h)

# ── MD編集モードの往復で原文に戻る ──
LAYOUT_RT = [
    "本文1\n\n\\newpage\n\n本文2",
    "行1\\newline行2",
    "前\n\n\\vspace{1cm}\n\n後",
    "\\bigskip\n\n本文\n\n\\newpage\n\n続き",
    "\\noindent 字下げなし",
    "A\\newline B\\newline C",
    "前\\par後",
    "説明: `\\newpage` と書きます",
]
for _src in LAYOUT_RT:
    _r1 = layout_roundtrip(_src)
    _r2 = layout_roundtrip(_r1)
    check(f"[体裁] 往復で変化しない {_src[:16]!r}", _r1 == _r2, f"{_r1!r} -> {_r2!r}")
check("[体裁] 往復で \\newpage が原文に戻る",
      layout_roundtrip("本文1\n\n\\newpage\n\n本文2") == "本文1\n\n\\newpage\n\n本文2",
      repr(layout_roundtrip("本文1\n\n\\newpage\n\n本文2")))
check("[体裁] 往復で改行コマンドの後ろが消えない",
      layout_roundtrip("行1\\newline行2") == "行1\\newline行2",
      repr(layout_roundtrip("行1\\newline行2")))

# 改ページを挟んでも行 ⇔ 表示要素の対応がずれない
_doc = "段落1\n\n\\newpage\n\n段落2"
_starts = _split_source_blocks(_doc)
check("[体裁] 改ページも 1 ブロックとして数える", _starts == [0, 2, 4], str(_starts))
_tagged = _tag_src_lines(render_layout(_doc), _starts)
check("[体裁] 改ページを挟んでも data-src-line が全ブロックに付く",
      _tagged.count("data-src-line=") == 3, _tagged)


# ══════════════════════════════════════════════════════════════
# 8. mermaid ダイアグラム抽出/復元 (v1.4.4)
# ══════════════════════════════════════════════════════════════
def mermaid_pipeline(md_text):
    """_build_md_html のプレビュー用パイプラインを模倣する
    (mermaid抽出 → markdown変換 → サニタイズ → 復元)。"""
    src, store = _extract_mermaid(md_text)
    html = markdown.markdown(src, extensions=["tables", "fenced_code"])
    html = _sanitize_html(html)
    return _restore_mermaid(html, store)


_MMD_DOC = "前\n\n```mermaid\nflowchart LR\n A --> B\n```\n\n後"
_mmd_src, _mmd_store = _extract_mermaid(_MMD_DOC)
check("[mermaid] 抽出でフェンスの中身が退避される",
      _mmd_store == ["flowchart LR\n A --> B"], repr(_mmd_store))
check("[mermaid] 抽出後の本文にコードフェンスが残らない",
      "```" not in _mmd_src, repr(_mmd_src))

_mmd_html = mermaid_pipeline(_MMD_DOC)
check("[mermaid] 復元後に <pre class=\"mermaid\"> が出力される",
      '<pre class="mermaid">' in _mmd_html, _mmd_html)
check("[mermaid] ダイアグラム本文がHTMLエスケープされて埋め込まれる",
      "flowchart LR\n A --&gt; B" in _mmd_html, _mmd_html)
check("[mermaid] 前後の本文はそのまま残る",
      "<p>前</p>" in _mmd_html and "<p>後</p>" in _mmd_html, _mmd_html)

# 通常のコードフェンス (mermaid以外) は影響を受けない
_OTHER_DOC = "```python\nprint('mermaid')\n```\n"
_other_src, _other_store = _extract_mermaid(_OTHER_DOC)
check("[mermaid] mermaid以外の言語フェンスは抽出されない",
      _other_store == [] and _other_src == _OTHER_DOC, repr((_other_src, _other_store)))

# 複数ダイアグラムが正しい順序で復元される
_MULTI_DOC = "```mermaid\nA\n```\n\n中間テキスト\n\n```mermaid\nB\n```\n"
_multi_html = mermaid_pipeline(_MULTI_DOC)
check("[mermaid] 複数ブロックが両方とも復元される",
      _multi_html.count('<pre class="mermaid">') == 2, _multi_html)
check("[mermaid] 複数ブロックの順序が保たれる",
      _multi_html.index(">A<") < _multi_html.index("中間テキスト")
      < _multi_html.index(">B<"), _multi_html)

# 行番号同期用の _split_source_blocks は「抽出前の原文」に対して呼ばれるため、
# mermaidフェンスを含んでいてもブロック数・開始行が変わってはいけない
# (main.py の _build_md_html は md_text 自体を書き換えず、_extract_mermaid の
#  結果は別変数 md_source に入れている点の回帰確認)。
_sync_doc = "前\n\n```mermaid\nA-->B\n```\n\n後"
_sync_starts = _split_source_blocks(_sync_doc)
check("[mermaid] 行番号同期: フェンスは1ブロックとして数えられる (抽出前の原文基準)",
      _sync_starts == [0, 2, 6], str(_sync_starts))

# _hex_is_dark: パレット色から mermaid の dark/default テーマを選ぶための判定
check("[mermaid] 黒背景は暗色と判定される", _hex_is_dark("#000000") is True)
check("[mermaid] 白背景は暗色でないと判定される", _hex_is_dark("#ffffff") is False)
check("[mermaid] アプリのダークパレット背景は暗色と判定される", _hex_is_dark("#111111") is True)
check("[mermaid] アプリのライトパレット背景は暗色でないと判定される", _hex_is_dark("#ffffff") is False)
check("[mermaid] 不正な色文字列はデフォルトで暗色扱い", _hex_is_dark("not-a-color") is True)


# ══════════════════════════════════════════════════════════════
print("=" * 60)
print(f"PASS: {PASS}   FAIL: {len(FAIL)}")
if FAIL:
    print("-" * 60)
    for f in FAIL:
        print("  FAIL", f)
    sys.exit(1)
print("すべて成功")
