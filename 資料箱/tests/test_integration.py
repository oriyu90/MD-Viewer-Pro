"""v1.4.1 統合テスト (実 WebEngine / オフスクリーン).

実際に QWebEngineView を動かし、数式・フロントマターの描画、
モード切替時のスクロール引き継ぎ、MD編集の往復変換、YAML ファイルの
取り扱いを確認する。ブラウザ側の JS も含めて通しで検証する点が、
イベントループを回さない test_qt_widgets.py との違い。
"""
import os, sys, shutil, tempfile, faulthandler
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# リポジトリ内の相対位置から main.py を解決する (資料箱/tests/ から 2 つ上)
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
faulthandler.dump_traceback_later(120, exit=True)

from PySide6.QtCore import QTimer, QEventLoop
from PySide6.QtWidgets import QApplication
import main as M

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

serious = [e for e in errors if "Error" in e or "error" in e]
check("[e2e] JS エラーが出ていない", not serious, str(serious[:5]))

print("=" * 60)
print(f"PASS: {PASS}   FAIL: {len(FAIL)}")
for f in FAIL: print("  FAIL", f)
sys.stdout.flush()
faulthandler.cancel_dump_traceback_later()
shutil.rmtree(TMP, ignore_errors=True)
os._exit(1 if FAIL else 0)
