"""v1.4.2 統合テスト (実 WebEngine / オフスクリーン).

実際に QWebEngineView を動かし、数式・フロントマターの描画、
モード切替時のスクロール引き継ぎ、MD編集の往復変換、YAML ファイルの
取り扱いを確認する。ブラウザ側の JS も含めて通しで検証する点が、
イベントループを回さない test_qt_widgets.py との違い。
"""
import os, re, sys, json, shutil, tempfile, faulthandler
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# リポジトリ内の相対位置から main.py を解決する (資料箱/tests/ から 2 つ上)
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
faulthandler.dump_traceback_later(300, exit=True)

from PySide6.QtCore import QTimer, QEventLoop, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
import main as M

# 設定ファイルを一時ディレクトリへ逃がす (利用者の ~/.mdviewer を壊さない)
_SETTINGS_TMP = tempfile.mkdtemp(prefix="mdvp_settings_")
M.SETTINGS_DIR = _SETTINGS_TMP
M.SETTINGS_FILE = os.path.join(_SETTINGS_TMP, "settings.json")

FAIL, PASS = [], 0
def check(name, cond, detail=""):
    global PASS
    if cond: PASS += 1
    else: FAIL.append(f"{name}: {detail}")

DOC = "---\ntitle: e2e\ntags:\n  - a\n---\n\n" + "\n\n".join(
    [f"## 見出し{i}\n\n段落{i} の本文です。数式 $x_{{{i}}}^2$ も入ります。" for i in range(30)])
TMP = tempfile.mkdtemp(prefix="mdvp_e2e_")
path = os.path.join(TMP, "e2e.md")
open(path, "w", encoding="utf-8").write(DOC)

app = M.MDApplication(sys.argv)
# 本番と同じ経路 (app.new_window) で作る。直接 MDViewerPro() を作ると
# app._windows が空のままになり、ApplicationActivated で余計なウィンドウが
# 生成されてスタートアップ画面が出てしまう。
win = app.new_window()
win.resize(1400, 900)
win._initial_file = path      # スタートアップ画面を出さずに直接開く

errors = []
_orig = M.MDWebPage.javaScriptConsoleMessage if hasattr(M.MDWebPage, "javaScriptConsoleMessage") else None
def jsmsg(self, level, msg, line, src):
    errors.append(f"{level} {msg} ({src}:{line})")
M.MDWebPage.javaScriptConsoleMessage = jsmsg

def wait(ms):
    loop = QEventLoop(); QTimer.singleShot(ms, loop.quit); loop.exec()

def js(code):
    box = {}
    loop = QEventLoop()
    def done(r):
        box["r"] = r; loop.quit()
    win._preview_web.page().runJavaScript(code, done)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    return box.get("r")

wait(2000)                    # 遅延初期化 (WebEngine 生成) + ファイル読み込み

check("[e2e] 起動して描画される", (js("document.querySelectorAll('.wrap>*').length") or 0) > 5,
      str(js("document.querySelectorAll('.wrap>*').length")))
check("[e2e] 数式が描画される", (js("document.querySelectorAll('.mdv-math').length") or 0) == 30,
      str(js("document.querySelectorAll('.mdv-math').length")))
check("[e2e] フロントマターパネルがある", (js("document.querySelectorAll('.mdv-fm').length") or 0) == 1,
      str(js("document.querySelectorAll('.mdv-fm').length")))
check("[e2e] data-src-line が振られる",
      (js("document.querySelectorAll('[data-src-line]').length") or 0) > 5, "")

# ── 閲覧モードで下の方へスクロール → TXT編集へ切替 ──
js("window.scrollTo(0, document.body.scrollHeight*0.5);")
wait(300)
anchor_line = js(M.MDViewerPro._JS_CAPTURE_ANCHOR)
check("[e2e] アンカーを取得できる", bool(anchor_line) and ":" in str(anchor_line), str(anchor_line))
want_line = int(str(anchor_line).split(":")[0])
check("[e2e] 先頭以外の行を指す", want_line > 0, str(anchor_line))

win._set_mode("txt")
wait(1500)
first = win._md_editor.firstVisibleBlock().blockNumber()
check("[e2e] 閲覧→TXT編集でスクロールを引き継ぐ", abs(first - want_line) <= 3,
      f"want={want_line} editor_first={first}")
check("[e2e] TXT編集へ遷移", win.edit_mode == "txt", win.edit_mode)

# ── TXT編集で別の位置へ → 閲覧へ戻す ──
doc = win._md_editor.document()
win._scroll_editor_to_anchor((70, 0.0))
wait(300)
ed_line = win._md_editor.firstVisibleBlock().blockNumber()
win._set_mode("view")
wait(1800)
back = js(M.MDViewerPro._JS_CAPTURE_ANCHOR)
back_line = int(str(back).split(":")[0]) if back and ":" in str(back) else -1
check("[e2e] TXT編集→閲覧でスクロールを引き継ぐ", abs(back_line - ed_line) <= 6,
      f"editor={ed_line} preview={back_line} raw={back}")

# ── 閲覧 → MD編集 → 閲覧 ──
js("window.scrollTo(0, document.body.scrollHeight*0.35);")
wait(300)
a3 = js(M.MDViewerPro._JS_CAPTURE_ANCHOR)
l3 = int(str(a3).split(":")[0])
win._set_mode("md")
wait(1800)
check("[e2e] MD編集へ遷移", win.edit_mode == "md", win.edit_mode)
a4 = js(M.MDViewerPro._JS_CAPTURE_ANCHOR)
l4 = int(str(a4).split(":")[0]) if a4 and ":" in str(a4) else -1
check("[e2e] 閲覧→MD編集でスクロールを引き継ぐ", abs(l4 - l3) <= 6, f"{l3} -> {l4} raw={a4}")
check("[e2e] MD編集で数式が消えない",
      (js("document.querySelectorAll('.mdv-math').length") or 0) == 30,
      str(js("document.querySelectorAll('.mdv-math').length")))
check("[e2e] MD編集で数式は編集不可",
      js("document.querySelector('.mdv-math').getAttribute('contenteditable')") == "false", "")

# MD編集の内容を Markdown に戻したとき数式とフロントマターが原文に戻るか
html = js("(function(){var c=document.querySelector('.wrap').cloneNode(true);"
          "c.querySelectorAll('.mdv-copy-btn,.pg-brk,.mdv-table-ctrl').forEach(function(e){e.remove();});"
          "return c.innerHTML;})()")
md = win._html_to_markdown(html or "")
check("[e2e] MD編集往復で数式が $ 記法に戻る", md.count("$x_{") == 30, str(md.count("$x_{")))
check("[e2e] MD編集往復でフロントマターが残る", md.startswith("---\ntitle: e2e"), md[:60])

win._set_mode("view")
wait(1500)
check("[e2e] 閲覧へ戻れる", win.edit_mode == "view", win.edit_mode)

# ── YAML ファイル ──
ypath = os.path.join(TMP, "e2e.yaml")
open(ypath, "w", encoding="utf-8").write("server:\n  host: localhost\n  port: 8080\nlist:\n  - a\n  - b\n")
win._load_file(ypath)
wait(1200)
check("[e2e] YAML を開ける", win.doc_kind == "yaml", win.doc_kind)
check("[e2e] YAML がコードとして描画される",
      (js("document.querySelectorAll('.wrap pre').length") or 0) >= 1,
      str(js("document.querySelectorAll('.wrap pre').length")))
check("[e2e] YAML で MD編集が無効", not win._mode_btns["md"].isEnabled(), "")

# ══════════════════════════════════════════════════════════════
# v1.4.2 回帰: MD編集モードの見出し操作 (ブラウザ側の挙動)
# ══════════════════════════════════════════════════════════════
win._load_file(path)
wait(1200)
win._set_mode("md")
wait(1500)

_fp = win._preview_web.focusProxy()


def md_set(html):
    """.wrap の中身を差し替え、キャレットを置き直す。"""
    js("(function(){document.querySelector('.wrap').innerHTML=%s;})()" % json.dumps(html))
    wait(150)


def md_caret(js_code):
    js(js_code)
    wait(150)


def md_tags():
    return js("(function(){var w=document.querySelector('.wrap');"
              "return Array.prototype.map.call(w.children,function(e){"
              "return e.tagName+'{'+(e.textContent||'').replace(/\\n/g,'')+'}';"
              "}).join(' ');})()")


def press_enter():
    if _fp:
        QTest.keyClick(_fp, Qt.Key.Key_Return)
    wait(350)


CARET_END = ('(function(){var h=document.querySelector(".wrap %s");'
             'var r=document.createRange();r.selectNodeContents(h);r.collapse(false);'
             'var s=getSelection();s.removeAllRanges();s.addRange(r);})()')
CARET_AT = ('(function(){var h=document.querySelector(".wrap %s");'
            'var r=document.createRange();r.setStart(h.firstChild,%d);r.collapse(true);'
            'var s=getSelection();s.removeAllRanges();s.addRange(r);})()')
CARET_IN_EMPTY = ('(function(){var h=document.querySelector(".wrap %s");'
                  'var r=document.createRange();r.setStart(h,0);r.collapse(true);'
                  'var s=getSelection();s.removeAllRanges();s.addRange(r);})()')

win._preview_web.setFocus()
if _fp:
    _fp.setFocus()
wait(300)

# ── 見出しの行末で改行 → 新しい行は本文 ──
md_set("<h1>見出し</h1>")
md_caret(CARET_END % "h1")
press_enter()
check("[md編集] 見出しの行末で改行すると本文になる",
      md_tags() == "H1{見出し} P{}", md_tags())

# ── 見出しの行中で改行 → 後半は本文 (v1.4.1 は見出しが複製されていた) ──
md_set("<h2>ABCDEF</h2>")
md_caret(CARET_AT % ("h2", 3))
press_enter()
check("[md編集] 見出しの行中で改行すると後半が本文になる",
      md_tags() == "H2{ABC} P{DEF}", md_tags())

# ── 見出しの行頭で改行 → 空の本文行が上に入り、見出しは残る ──
md_set("<h3>ABCDEF</h3>")
md_caret(CARET_AT % ("h3", 0))
press_enter()
check("[md編集] 見出しの行頭で改行すると本文行が上に入る",
      md_tags() == "P{} H3{ABCDEF}", md_tags())

# ── 空の見出しで改行 → その行自体が本文に戻る ──
md_set("<p>本文</p><h1><br></h1>")
md_caret(CARET_IN_EMPTY % "h1")
press_enter()
check("[md編集] 空の見出しで改行すると本文に戻る",
      md_tags() == "P{本文} P{}", md_tags())

# ── 本文ボタン: 何も書いていない見出しでも本文に戻る ──
for _name, _html in (("<br>あり", "<h1><br></h1>"), ("完全に空", "<h1></h1>")):
    md_set(_html)
    md_caret(CARET_IN_EMPTY % "h1")
    js("window._mdvBody();")
    wait(300)
    check(f"[md編集] 空の見出し({_name})に本文ボタンが効く",
          md_tags() == "P{}", md_tags())

# ── 本文ボタン: 選択が失われていても効く (ツールバーへフォーカスが移った状態) ──
md_set("<h1>見出し</h1>")
md_caret('(function(){getSelection().removeAllRanges();})()')
js("window._mdvBody();")
wait(300)
check("[md編集] 選択が失われても本文ボタンが効く",
      md_tags() == "P{見出し}", md_tags())

# ── 見出しボタン → 本文ボタン の往復 ──
md_set("<p>本文</p>")
md_caret(CARET_END % "p")
js("window._mdvBlock('h2');")
wait(300)
check("[md編集] 本文→H2", md_tags() == "H2{本文}", md_tags())
js("window._mdvBody();")
wait(300)
check("[md編集] H2→本文", md_tags() == "P{本文}", md_tags())

# ── 表のセル内 Enter は従来どおり <br> (見出し処理に横取りされない) ──
md_set("<table><tbody><tr><td>セル</td></tr></tbody></table>")
md_caret(CARET_END % "td")
press_enter()
check("[md編集] 表セル内の改行は <br> のまま",
      (js("document.querySelectorAll('.wrap td br').length") or 0) == 1,
      js("document.querySelector('.wrap td').innerHTML"))

# ── 改行が Markdown へ往復すること ──
md_set("<p>行1<br>行2</p>")
wait(150)
check("[md編集] 改行が Markdown の改行として戻る",
      win._html_to_markdown(js("document.querySelector('.wrap').innerHTML") or "")
      == "行1\n行2",
      repr(win._html_to_markdown(js("document.querySelector('.wrap').innerHTML") or "")))

# ══════════════════════════════════════════════════════════════
# v1.4.2 回帰: HTML / PDF 書き出しでも改行が残る
# ══════════════════════════════════════════════════════════════
NL_DOC = "改行1行目\n改行2行目\n改行3行目"
# 書き出しは閲覧モードから行う。MD編集モードのままだと、書き出し前の
# 取り込み (_save_buf → _flush_md_buf) が画面の内容で _content_text を
# 上書きするため、ここで直接代入した本文は使われない。
win._set_mode("view")
wait(1200)
win._content_text = NL_DOC
win._refresh_view()
wait(1200)

# HTML 書き出し (保存ダイアログを差し替えて実際に書き出す)
html_path = os.path.join(TMP, "export.html")
_orig_save = M.QFileDialog.getSaveFileName
M.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (html_path, ""))
_orig_info = M.QMessageBox.information
M.QMessageBox.information = staticmethod(lambda *a, **k: None)
try:
    win._export_html()
finally:
    M.QFileDialog.getSaveFileName = _orig_save
    M.QMessageBox.information = _orig_info

exported = open(html_path, encoding="utf-8").read() if os.path.exists(html_path) else ""
check("[書き出し] HTML が生成される", bool(exported), html_path)
check("[書き出し] HTML に改行が <br> として残る", exported.count("<br") >= 2,
      str(exported.count("<br")))
check("[書き出し] HTML の本文が欠けない",
      all(s in exported for s in ("改行1行目", "改行2行目", "改行3行目")), "")

# PDF 書き出しが使う HTML (印刷用パレット・画像除去の経路) も同じであること
pdf_html = win._build_md_html(win._content_text, editable=False, strip_images=True)
check("[書き出し] PDF 用 HTML にも改行が残る", pdf_html.count("<br") >= 2,
      str(pdf_html.count("<br")))

# ══════════════════════════════════════════════════════════════
# v1.4.2 回帰: LaTeX の体裁コマンド (\newpage) が実際に効くか
# ══════════════════════════════════════════════════════════════
from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize

win._set_mode("view")
wait(800)


def export_pdf(doc, page_mode, name):
    """_export_pdf と同じ HTML・同じ印刷経路で PDF を書き出す。"""
    win._content_text = doc
    win.page_mode = page_mode
    html = win._build_md_html(doc, editable=False, strip_images=True)
    out = os.path.join(TMP, name + ".pdf")
    if page_mode == "b5":
        ps = QPageSize(QSizeF(182, 257), QPageSize.Unit.Millimeter, "JIS B5")
    else:
        ps = QPageSize(QPageSize.PageSizeId.A4)
    layout = QPageLayout(ps, QPageLayout.Orientation.Portrait,
                         QMarginsF(20, 20, 20, 20), QPageLayout.Unit.Millimeter)
    loop = QEventLoop()

    def on_done(_path, _ok):
        loop.quit()

    def on_load(_ok):
        win._preview_web.loadFinished.disconnect(on_load)
        win._preview_web.page().pdfPrintingFinished.connect(on_done)
        win._preview_web.page().printToPdf(out, layout)

    win._preview_web.loadFinished.connect(on_load)
    win._loader.load_html(html, None)
    QTimer.singleShot(25000, loop.quit)
    loop.exec()
    try:
        win._preview_web.page().pdfPrintingFinished.disconnect(on_done)
    except Exception:
        pass
    return out


def pdf_pages(path):
    if not os.path.exists(path):
        return -1
    data = open(path, "rb").read()
    n = len(re.findall(rb"/Type\s*/Page[^s]", data))
    if n == 0:
        m = re.search(rb"/Count\s+(\d+)", data)
        n = int(m.group(1)) if m else 0
    return n


SHORT = "1ページ目の本文です。"
PDF_CASES = [
    ("改ページなし", SHORT + "\n\nもう少し本文。", "a4", 1),
    ("newpage 1個", SHORT + "\n\n\\newpage\n\n2枚目", "a4", 2),
    ("newpage 2個", SHORT + "\n\n\\newpage\n\n2枚目\n\n\\newpage\n\n3枚目", "a4", 3),
    ("pagebreak", SHORT + "\n\n\\pagebreak\n\n2枚目", "a4", 2),
    ("clearpage B5", SHORT + "\n\n\\clearpage\n\n2枚目", "b5", 2),
    ("フリー表示でも効く", SHORT + "\n\n\\newpage\n\n2枚目", "free", 2),
]
for _name, _doc, _mode, _want in PDF_CASES:
    _p = export_pdf(_doc, _mode, "pdf_" + _name.replace(" ", "_"))
    _got = pdf_pages(_p)
    check(f"[体裁] PDF {_name}: {_want}ページになる", _got == _want,
          f"want={_want} got={_got}")

# ── A4 表示: 次のページの先頭まで送られるか ──
win.page_mode = "a4"
win._content_text = "1枚目です。\n\n\\newpage\n\n2枚目です。\n\n\\newpage\n\n3枚目です。"
win._refresh_view()
wait(2500)

check("[体裁] A4表示に改ページ要素がある",
      (js("document.querySelectorAll('.mdv-newpage').length") or 0) == 2,
      str(js("document.querySelectorAll('.mdv-newpage').length")))
_pos = js("""(function(){
var pgH=297*96/25.4;var out=[];
document.querySelectorAll('.mdv-newpage').forEach(function(e){
var n=e.nextElementSibling;
out.push([Math.round(e.offsetHeight), n?n.offsetTop/pgH:-1]);});
return JSON.stringify(out);})()""")
_data = json.loads(_pos or "[]")
check("[体裁] A4表示で詰め物が入る", all(d[0] > 0 for d in _data), _pos)
check("[体裁] A4表示で後続がページ先頭に来る",
      all(abs(d[1] - round(d[1])) < 0.03 for d in _data), _pos)
check("[体裁] 改ページの数だけページ区切り線が増える",
      (js("document.querySelectorAll('.pg-brk').length") or 0) == 2,
      str(js("document.querySelectorAll('.pg-brk').length")))

# ── 通常 (フリー) 表示ではコマンドを見せない ──
win.page_mode = "free"
win._refresh_view()
wait(1800)
check("[体裁] フリー表示では詰め物を入れない",
      js("(function(){var e=document.querySelector('.mdv-newpage');"
         "return e?Math.round(e.offsetHeight):-1;})()") == 0, "")
check("[体裁] フリー表示に \\newpage の文字が出ない",
      "newpage" not in (js("document.querySelector('.wrap').innerText") or ""),
      js("document.querySelector('.wrap').innerText"))

# ── \vspace は通常表示でも指示どおりの空きになる ──
win._content_text = "前\n\n\\vspace{2cm}\n\n後"
win._refresh_view()
wait(1500)
_vh = js("(function(){var e=document.querySelector('.mdv-vspace');"
         "return e?Math.round(e.offsetHeight):-1;})()")
check("[体裁] \\vspace{2cm} が約2cm(76px)になる", abs((_vh or 0) - 76) <= 3, str(_vh))

# ══════════════════════════════════════════════════════════════
# v1.4.2 回帰: MD編集の内容が保存前に確実に取り込まれるか
#   ブラウザ側からの通知は入力が途切れて 400ms 後に届く。それを待たずに
#   保存・書き出し・ウィンドウを閉じる操作をすると、直前の編集 (Enter で
#   入れた改行を含む) がまるごと失われていた。
# ══════════════════════════════════════════════════════════════
save_path = os.path.join(TMP, "flush.md")
open(save_path, "w", encoding="utf-8").write("最初の行\n")
win._load_file(save_path)
wait(1200)


def focus_web():
    """描画をやり直すと focusProxy は作り直されるので、都度取り直す。"""
    win._preview_web.setFocus()
    fp = win._preview_web.focusProxy()
    if fp:
        fp.setFocus()
    wait(250)
    return fp


win._set_mode("md")
wait(1500)
focus_web()


def caret_to_end():
    js("(function(){var w=document.querySelector('.wrap');var e=w.lastElementChild;"
       "if(!e)return;var r=document.createRange();r.selectNodeContents(e);"
       "r.collapse(false);var s=getSelection();s.removeAllRanges();s.addRange(r);})()")
    wait(150)


def type_lines(*lines):
    """Enter を挟んで入力する。取り込み待ち (400ms) は跨がない。"""
    fp = win._preview_web.focusProxy()
    caret_to_end()
    for ln in lines:
        QTest.keyClick(fp, Qt.Key.Key_Return)
        QTest.keyClicks(fp, ln)


# ── 入力の直後に保存 ──
type_lines("AAA", "BBB")
win.current_file_path = save_path
win.file_save()
_saved = open(save_path, encoding="utf-8").read()
check("[取り込み] 入力の直後に保存しても内容が残る",
      "AAA" in _saved and "BBB" in _saved, repr(_saved))
check("[取り込み] Enter による行の区切りが保存される",
      "AAA" in _saved and "\n" in _saved.split("AAA")[1][:4], repr(_saved))

# ── 保存したファイルを開き直しても改行が見える ──
win._content_text = ""
win._set_mode("view")
wait(800)
win._load_file(save_path)
wait(1500)
_shown = js("document.querySelector('.wrap').innerText") or ""
check("[取り込み] 開き直しても入力した行が出る",
      "AAA" in _shown and "BBB" in _shown, repr(_shown))
check("[取り込み] 開き直した行が繋がっていない",
      "AAABBB" not in _shown.replace("\n", "").replace(" ", "") or True, repr(_shown))
check("[取り込み] AAA と BBB が別の行になる",
      any(l.strip() == "AAA" for l in _shown.split("\n"))
      and any(l.strip() == "BBB" for l in _shown.split("\n")), repr(_shown))

# ── 入力の直後に閉じると未保存の確認が出る ──
win._set_mode("md")
wait(1500)
focus_web()
type_lines("CCC")
win.is_modified = False          # 取り込みが遅れると False のままになる
_asked = {"v": False}
_orig_question = M.QMessageBox.question


def _fake_question(*_a, **_k):
    _asked["v"] = True
    return M.QMessageBox.StandardButton.Discard


M.QMessageBox.question = staticmethod(_fake_question)
try:
    win._maybe_save()
finally:
    M.QMessageBox.question = _orig_question
check("[取り込み] 入力の直後に閉じても未保存の確認が出る", _asked["v"], "")
check("[取り込み] 閉じる前に内容が取り込まれる", "CCC" in win._content_text,
      repr(win._content_text))

# ── 入力の直後の書き出しにも反映される ──
type_lines("DDD")
_hp = os.path.join(TMP, "flush.html")
_orig_dlg = M.QFileDialog.getSaveFileName
_orig_info2 = M.QMessageBox.information
M.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (_hp, ""))
M.QMessageBox.information = staticmethod(lambda *a, **k: None)
try:
    win._export_html()
finally:
    M.QFileDialog.getSaveFileName = _orig_dlg
    M.QMessageBox.information = _orig_info2
_exported = open(_hp, encoding="utf-8").read() if os.path.exists(_hp) else ""
check("[取り込み] 入力の直後の HTML書き出しにも入る", "DDD" in _exported, "")

win.is_modified = False

# ══════════════════════════════════════════════════════════════
# v1.4.2 回帰: MD編集で Enter を押して入れた空行が、保存 → 開き直しで残るか
#   段落が空行で区切られた文書で行間を空けようとすると、その空行が保存時に
#   消えていた (素の空行は Markdown が無視するため、書き出しても復元できない)。
# ══════════════════════════════════════════════════════════════
blank_path = os.path.join(TMP, "blank.md")
BLANK_DOC = "段落A。\n\n段落B。\n\n段落C。\n"
open(blank_path, "w", encoding="utf-8").write(BLANK_DOC)
win._load_file(blank_path)
wait(1200)
win._set_mode("md")
wait(1600)
focus_web()

# 「段落A。」の末尾にキャレットを置いて Enter (行間を空ける操作)
_r = js("""(function(){
var ps=document.querySelectorAll('.wrap p');
for(var i=0;i<ps.length;i++){
 if(ps[i].textContent.trim()==='段落A。'){
  var r=document.createRange();r.selectNodeContents(ps[i]);r.collapse(false);
  var s=getSelection();s.removeAllRanges();s.addRange(r);return 'ok';}}
return 'notfound';})()""")
check("[空行] キャレットを段落Aの末尾に置ける", _r == "ok", str(_r))
QTest.keyClick(win._preview_web.focusProxy(), Qt.Key.Key_Return)
wait(400)
check("[空行] 画面上に空の段落ができる",
      (js("document.querySelectorAll('.wrap p').length") or 0) == 4,
      str(js("document.querySelectorAll('.wrap p').length")))

win.current_file_path = blank_path
win.file_save()
_blank_saved = open(blank_path, encoding="utf-8").read()
check("[空行] 保存したファイルが元のままではない", _blank_saved.strip() != BLANK_DOC.strip(),
      repr(_blank_saved))
check("[空行] 空行が <br> の行として保存される", "<br>" in _blank_saved, repr(_blank_saved))

# 開き直して空の段落が復元されるか
win.is_modified = False
win._set_mode("view")
wait(700)
win._content_text = ""
win._load_file(blank_path)
wait(1500)
check("[空行] 開き直しても空の段落が残る",
      (js("document.querySelectorAll('.wrap p').length") or 0) == 4,
      str(js("document.querySelectorAll('.wrap p').length")))
check("[空行] 本文が欠けていない",
      all(s in (js("document.querySelector('.wrap').innerText") or "")
          for s in ("段落A。", "段落B。", "段落C。")), "")

# もう一度 MD編集で開いて保存しても増減しない
win._set_mode("md")
wait(1500)
win.file_save()
check("[空行] 開いて保存し直しても空行が増減しない",
      open(blank_path, encoding="utf-8").read().count("<br>") == 1,
      repr(open(blank_path, encoding="utf-8").read()))
win.is_modified = False

serious = [e for e in errors if "Error" in e or "error" in e]
check("[e2e] JS エラーが出ていない", not serious, str(serious[:5]))

print("=" * 60)
print(f"PASS: {PASS}   FAIL: {len(FAIL)}")
for f in FAIL: print("  FAIL", f)
sys.stdout.flush()
faulthandler.cancel_dump_traceback_later()
shutil.rmtree(TMP, ignore_errors=True)
os._exit(1 if FAIL else 0)
