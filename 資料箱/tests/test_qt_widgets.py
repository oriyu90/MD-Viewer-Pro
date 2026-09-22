"""v1.4.3 Qt ウィジェット層 自動テスト (オフスクリーン).

実際の MDViewerPro を生成し、目次パネル・スプリッター・書式ヘルパ等の
振る舞いを画面なしで検証する。QWebEngineView は遅延生成のため、
イベントループを回さないことで生成前の状態のまま Qt 側だけを検証する。
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
# リポジトリ内の相対位置から main.py を解決する (資料箱/tests/ から 2 つ上)
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextCursor

import main as M

# 設定ファイルを一時ディレクトリへ逃がす。テストは設定を書き換えるため、
# そのままだと利用者の ~/.mdviewer/settings.json を壊してしまう。
import tempfile
_SETTINGS_TMP = tempfile.mkdtemp(prefix="mdvp_settings_")
M.SETTINGS_DIR = _SETTINGS_TMP
M.SETTINGS_FILE = os.path.join(_SETTINGS_TMP, "settings.json")
import atexit
import shutil
atexit.register(shutil.rmtree, _SETTINGS_TMP, True)

FAIL, PASS = [], 0


def check(name, cond, detail=""):
    global PASS
    if cond:
        PASS += 1
    else:
        FAIL.append(f"{name}: {detail}")


app = QApplication.instance() or QApplication(sys.argv)
win = M.MDViewerPro()
win.resize(1400, 900)

DOC = """# 見出し壱

本文A

## 見出し弐

本文B

### 見出し参

```
# コード内 (見出しではない)
```

# フェンス後

```
# 未閉鎖フェンス内の見出し

###### H6
"""

# ══════════════════════════════════════════════════
# 1. 目次パネル: 項目数・フォントサイズ
# ══════════════════════════════════════════════════
win._content_text = DOC
win._show_toc = True
win.edit_mode = "md"
win._rebuild_toc_list(force=True)

n_items = win._toc_list.count()
heads = win._extract_headings(DOC)
check("[toc] 項目数が抽出結果と一致", n_items == len(heads),
      f"items={n_items} heads={len(heads)}")
check("[toc] 未閉鎖フェンス内の見出しも拾う", n_items == 6,
      f"items={n_items} " + str([h[1] for h in heads]))

base = win._toc_base_font_px()
check("[toc] 基準フォント >= 16px", base >= 16, f"base={base}")
sizes = []
for i in range(win._toc_list.count()):
    it = win._toc_list.item(i)
    sizes.append(it.font().pixelSize())
check("[toc] 全項目 >= 16px", all(s >= 16 for s in sizes), f"sizes={sizes}")
check("[toc] 全項目 <= 基準値", all(s <= base for s in sizes), f"sizes={sizes} base={base}")

# 見出しレベルが深いほど小さい(ただし16px下限)
lv_size = {}
for i, (lv, _t, _l) in enumerate(heads):
    lv_size.setdefault(lv, win._toc_list.item(i).font().pixelSize())
for a in sorted(lv_size):
    for b in sorted(lv_size):
        if a < b:
            check("[toc] レベル順にサイズが非増加", lv_size[a] >= lv_size[b],
                  f"H{a}={lv_size[a]} H{b}={lv_size[b]}")

# 項目に紐づく行番号が実在するか
lines = DOC.split("\n")
for i in range(win._toc_list.count()):
    ln = win._toc_list.item(i).data(M.Qt.ItemDataRole.UserRole + 1)
    check("[toc] 行番号が範囲内", ln is not None and 0 <= ln < len(lines), f"ln={ln}")

# ══════════════════════════════════════════════════
# 2. 目次キャッシュ: 内容不変なら作り直さない / 変化時は更新
# ══════════════════════════════════════════════════
first_item = win._toc_list.item(0)
win._rebuild_toc_list()
check("[toc] 内容不変なら再構築しない", win._toc_list.item(0) is first_item,
      "item が作り直されている(ちらつきの原因)")

win._content_text = DOC + "\n\n## 追加された見出し\n"
win._rebuild_toc_list()
check("[toc] 見出し追加で更新される", win._toc_list.count() == n_items + 1,
      f"{win._toc_list.count()} vs {n_items + 1}")

win._content_text = "見出しなし本文のみ\n"
win._rebuild_toc_list()
check("[toc] 見出しゼロで空表示", win._toc_list.count() == 1, str(win._toc_list.count()))
check("[toc] 空表示は選択不可",
      not (win._toc_list.item(0).flags() & M.Qt.ItemFlag.ItemIsSelectable), "")

# 言語切替でキャッシュが効きすぎないか
win.lang = "en"
win._rebuild_toc_list()
check("[toc] 言語切替で空表示が翻訳される",
      win._toc_list.item(0).text() == M.I18N["en"]["toc_empty"],
      win._toc_list.item(0).text())
win.lang = "ja"

# ══════════════════════════════════════════════════
# 3. スプリッター: 目次幅と手動調整の保持
# ══════════════════════════════════════════════════
win._content_text = DOC
# 実レイアウトを模して splitter に実幅を与える
win._splitter.resize(win.width(), 800)
for mode in ("md", "txt"):
    win.edit_mode = mode
    win._show_toc = True
    # _do_set_mode と同じ順序で可視状態を確定させてからサイズを決める
    win._editor_stack.setVisible(mode == "txt")
    win._update_toc_panel_visibility()
    win._update_splitter_sizes()
    s = win._splitter.sizes()
    check(f"[splitter/{mode}] 目次幅が指定どおり",
          abs(s[0] - win._toc_panel_width()) <= 2, f"sizes={s} want={win._toc_panel_width()}")
    check(f"[splitter/{mode}] 合計が幅と一致",
          abs(sum(s) - win._splitter_total_width()) <= 3,
          f"sum={sum(s)} width={win._splitter_total_width()}")

# 目次OFFなら幅0
win._show_toc = False
win._update_toc_panel_visibility()
win._update_splitter_sizes()
check("[splitter] 目次OFFで幅0", win._splitter.sizes()[0] == 0, str(win._splitter.sizes()))

# 手動でドラッグした比率がリサイズで保持されるか
win._show_toc = True
win.edit_mode = "txt"
win._update_toc_panel_visibility()
win._update_splitter_sizes()
total = win._splitter_total_width()
toc0 = win._toc_panel_width()
manual = [toc0, int((total - toc0) * 0.8), (total - toc0) - int((total - toc0) * 0.8)]
win._splitter.setSizes(manual)
before = win._splitter.sizes()
ratio_before = before[1] / max(1, before[1] + before[2])
win.resize(1700, 900)
win._sync_toc_width_on_resize()
after = win._splitter.sizes()
ratio_after = after[1] / max(1, after[1] + after[2])
check("[splitter] リサイズでエディタ/プレビュー比率を保持",
      abs(ratio_before - ratio_after) < 0.05,
      f"before={ratio_before:.3f} after={ratio_after:.3f} ({before} -> {after})")
check("[splitter] リサイズで目次幅が追従",
      abs(after[0] - win._toc_panel_width()) <= 2,
      f"after={after} want={win._toc_panel_width()}")

# 目次幅の範囲
for w in (600, 900, 1200, 1600, 2400, 3200):
    win.resize(w, 900)
    tw = win._toc_panel_width()
    check("[splitter] 目次幅が 220..420 の範囲", 220 <= tw <= 420, f"width={w} toc={tw}")
win.resize(1400, 900)

# ══════════════════════════════════════════════════
# 4. TXT編集モードの書式ヘルパ (実 QPlainTextEdit 上で)
# ══════════════════════════════════════════════════
win.edit_mode = "txt"
ed = win._md_editor


def set_text(t, line=0, col=0):
    ed.blockSignals(True)
    ed.setPlainText(t)
    ed.blockSignals(False)
    c = ed.textCursor()
    b = ed.document().findBlockByNumber(line)
    c.setPosition(b.position() + col)
    ed.setTextCursor(c)


set_text("Alpha")
win._md_toggle_ordered()
check("[txt] 番号付与", ed.toPlainText() == "1. Alpha", repr(ed.toPlainText()))
win._md_toggle_ordered()
check("[txt] 番号解除", ed.toPlainText() == "Alpha", repr(ed.toPlainText()))

set_text("1. Alpha\nBeta", line=1)
win._md_toggle_ordered()
check("[txt] 直前行を見て連番", ed.toPlainText() == "1. Alpha\n2. Beta", repr(ed.toPlainText()))

set_text("9. I\nJ", line=1)
win._md_toggle_ordered()
check("[txt] 2桁への繰り上がり", ed.toPlainText() == "9. I\n10. J", repr(ed.toPlainText()))

set_text("Alpha")
win._md_toggle_unordered()
check("[txt] 箇条書き付与", ed.toPlainText() == "- Alpha", repr(ed.toPlainText()))
win._md_toggle_unordered()
check("[txt] 箇条書き解除", ed.toPlainText() == "Alpha", repr(ed.toPlainText()))

# 本文ボタン: 各種マーカーの除去
for src, want in [
    ("# 見出し", "見出し"),
    ("### 見出し", "見出し"),
    ("- 箇条書き", "箇条書き"),
    ("1. 番号", "番号"),
    ("> 引用", "引用"),
    ("- [ ] チェック", "チェック"),
    ("普通の本文", "普通の本文"),
]:
    set_text(src)
    win._md_body()
    check("[txt] 本文化", ed.toPlainText() == want, f"{src!r} -> {ed.toPlainText()!r} (want {want!r})")

# 日本語・マルチバイトでも壊れないか
set_text("日本語の見出し")
win._md_toggle_ordered()
check("[txt] 日本語で番号付与", ed.toPlainText() == "1. 日本語の見出し", repr(ed.toPlainText()))

# ══════════════════════════════════════════════════
# 5. 翻訳ヘルパ _t()
# ══════════════════════════════════════════════════
for lang in ("ja", "en", "de", "fr"):
    win.lang = lang
    check(f"[i18n/{lang}] 空文字の翻訳が失われない",
          win._t("page_label_prefix") == M.I18N[lang]["page_label_prefix"],
          repr(win._t("page_label_prefix")))
    check(f"[i18n/{lang}] toc_title が翻訳される",
          win._t("toc_title") == M.I18N[lang]["toc_title"], win._t("toc_title"))
check("[i18n] 未知キーはキー名を返す", win._t("__nonexistent__") == "__nonexistent__", "")
win.lang = "ja"

# ══════════════════════════════════════════════════
# 6. モード遷移でウィジェットの可視状態が破綻しないか
# ══════════════════════════════════════════════════
for mode in ("view", "md", "txt", "view", "txt", "md", "view"):
    win.edit_mode = mode
    win._editor_stack.setVisible(mode == "txt")
    win._update_toc_panel_visibility()
    win._update_splitter_sizes()
    vis = [win._toc_panel.isVisible(), win._editor_stack.isVisible()]
    check(f"[mode/{mode}] 閲覧では目次パネル非表示(オーバーレイ側を使う)",
          not (mode == "view" and win._toc_panel.isVisible()), str(vis))
    check(f"[mode/{mode}] TXT以外でエディタ非表示",
          not (mode != "txt" and win._editor_stack.isVisible()), str(vis))
    s = win._splitter.sizes()
    check(f"[mode/{mode}] スプリッター幅が負にならない", all(x >= 0 for x in s), str(s))

# ══════════════════════════════════════════════════
# 7. 目次は既定でオン (v1.4.1)
# ══════════════════════════════════════════════════
check("[toc-default] 設定の既定値がオン", M._SETTINGS_DEFAULTS["show_toc"] is True,
      str(M._SETTINGS_DEFAULTS.get("show_toc")))
# 設定ファイルが無い状態 (初回起動) を再現する
_saved_settings_file = M.SETTINGS_FILE
M.SETTINGS_FILE = os.path.join(os.path.dirname(_saved_settings_file),
                               "__no_such_settings__.json")
check("[toc-default] 設定ファイルなしでオン", M.load_settings()["show_toc"] is True,
      str(M.load_settings()["show_toc"]))
_fresh = M.MDViewerPro()
M.SETTINGS_FILE = _saved_settings_file
check("[toc-default] 新規ウィンドウで目次オン", _fresh._show_toc is True,
      str(_fresh._show_toc))
_fresh.edit_mode = "md"
_fresh._update_toc_panel_visibility()
_fresh._refresh_btn_states()
check("[toc-default] MD編集で目次パネルが出る", not _fresh._toc_panel.isHidden(),
      "パネルが非表示")
check("[toc-default] 目次ボタンが押下状態", _fresh._toc_btn.property("active") is True,
      str(_fresh._toc_btn.property("active")))

# ══════════════════════════════════════════════════
# 8. ボタン文字の自動縮小 (v1.4.1)
# ══════════════════════════════════════════════════
def fit_now(tb):
    """レイアウトを確定させ、各ボタンに幅合わせをやり直させる。
    非表示ウィジェットへの QResizeEvent は show() まで遅延するため、
    オフスクリーンのテストでは明示的に呼ぶ必要がある。"""
    tb.layout().activate()
    for b in tb.findChildren(M.PianoBtn):
        b._applied_px = -1
        b._fit_text()


BTN_ATTRS = ["_back_btn", "_settings_btn", "_toc_btn", "_pdf_btn", "_margin_btn"]
prev_px = {}
for w in (1600, 1200, 900, 700, 520, 480):
    win.resize(w, 900)
    win._last_ui_scale_cat = ""      # リサイズタイマーを待たずに反映させる
    win._apply_responsive_style()
    win._main_tb.resize(w, win._main_tb.height())
    fit_now(win._main_tb)
    for name in BTN_ATTRS:
        b = getattr(win, name)
        px = b._applied_px
        check(f"[btnfit/{w}] {name} フォントが決まっている", px > 0, f"px={px}")
        check(f"[btnfit/{w}] {name} 下限を下回らない", px >= M.PianoBtn.MIN_FONT_PX,
              f"px={px}")
        # 実測でボタン幅に収まっているか
        f = M.QFont(b.font()); f.setBold(True); f.setPixelSize(px)
        adv = M.QFontMetrics(f).horizontalAdvance(b.text())
        check(f"[btnfit/{w}] {name} 文字が枠内に収まる", adv <= b.width(),
              f"text={b.text()!r} adv={adv} btn_w={b.width()} px={px}")
        if name in prev_px:
            check(f"[btnfit/{w}] {name} 幅が狭いほど大きくならない",
                  px <= prev_px[name], f"{prev_px[name]} -> {px}")
        prev_px[name] = px
    # ツールバー全体がウィンドウ幅を超えない (超えると文字が切れる)
    need = win._main_tb.minimumSizeHint().width()
    check(f"[btnfit/{w}] ツールバー最小幅 <= ウィンドウ幅", need <= w,
          f"need={need} window={w}")
win.resize(1400, 900)
win._last_ui_scale_cat = ""
win._apply_responsive_style()

# ボタンごとに文字量が違えば、必要なときは別々のサイズになりうる
win.resize(500, 900)
win._last_ui_scale_cat = ""
win._apply_responsive_style()
win._main_tb.resize(500, win._main_tb.height())
fit_now(win._main_tb)
_sizes = {n: getattr(win, n)._applied_px for n in BTN_ATTRS}
check("[btnfit] 短いラベルは長いラベルより小さくならない",
      _sizes["_back_btn"] >= _sizes["_pdf_btn"], str(_sizes))
win.resize(1400, 900)
win._last_ui_scale_cat = ""
win._apply_responsive_style()

# ══════════════════════════════════════════════════
# 9. LaTeX / YAML を含む HTML 生成 (v1.4.1)
# ══════════════════════════════════════════════════
MATH_DOC = ("---\ntitle: 数式\ntags:\n  - math\n---\n\n"
            "# 数式\n\n"
            "インライン $E=mc^2$ です。\n\n"
            "$$\n\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}\n$$\n")
win._content_text = MATH_DOC
for mode, kw in [("view", {}), ("md", {"editable": True}),
                 ("txt", {"sync_lines": True})]:
    html = win._build_md_html(MATH_DOC, **kw)
    check(f"[render/{mode}] 数式が組版される", html.count('data-tex="') == 2, mode)
    check(f"[render/{mode}] プレースホルダが残らない",
          "\ue000" not in html and "\ue001" not in html, mode)
    check(f"[render/{mode}] フロントマターがパネルになる", 'class="mdv-fm"' in html, mode)
    check(f"[render/{mode}] フロントマターが本文に漏れない",
          "<hr" not in html.split('class="mdv-fm"')[0], mode)
    check(f"[render/{mode}] 数式CSSが入る", ".mdv-frac" in html, mode)
    check(f"[render/{mode}] 行対応が全モードで付く", "data-src-line" in html, mode)

# YAML ドキュメントモード
win.doc_kind = "yaml"
yhtml = win._build_md_html("key: value\nlist:\n  - a\n")
check("[render/yaml] YAML はコードブロックとして描画", "<pre" in yhtml, yhtml[:200])
check("[render/yaml] MD編集は選べない", not win._mode_available("md"), "")
check("[render/yaml] TXT編集は選べる", win._mode_available("txt"), "")
win.doc_kind = "md"
check("[render/md] MD編集に戻る", win._mode_available("md"), "")

# 数式が無い文書でも従来どおり動く
# (data-tex は体裁コマンドの CSS にも現れるため、本文の中身だけを見る)
plain = win._build_md_html("# A\n\ntext\n")
_pi = plain.index('class="wrap"')
_pj = plain.find('<script', _pi)
plain_body = plain[_pi:_pj if _pj != -1 else len(plain)]
check("[render] 数式なしでも生成できる",
      "<h1" in plain_body and "data-tex" not in plain_body, plain_body)

# ══════════════════════════════════════════════════
# 10. スクロールアンカー (v1.4.1)
# ══════════════════════════════════════════════════
check("[anchor] 解析", win._parse_anchor("42:0.2500") == (42, 0.25),
      str(win._parse_anchor("42:0.2500")))
check("[anchor] 空文字は None", win._parse_anchor("") is None, "")
check("[anchor] 不正文字列は None", win._parse_anchor("abc") is None, "")
check("[anchor] JS に行番号が埋め込まれる", "var line=42" in win._js_restore_anchor(42, 0.5),
      win._js_restore_anchor(42, 0.5)[:120])

ANCHOR_DOC = "\n\n".join(f"段落{i}" for i in range(40))
win.doc_kind = "md"
win._content_text = ANCHOR_DOC
win.edit_mode = "txt"
win._md_editor.blockSignals(True)
win._md_editor.setPlainText(ANCHOR_DOC)
win._md_editor.blockSignals(False)
win._md_editor.resize(400, 300)
for target in (0, 10, 30):
    win._scroll_editor_to_anchor((target, 0.0))
    first = win._md_editor.firstVisibleBlock().blockNumber()
    # 末尾付近は最終行までしかスクロールできないため許容幅を持たせる
    check("[anchor] エディタが指定行付近へ移動", abs(first - target) <= 2,
          f"target={target} first={first}")

# 折り返しのある長い行でも、狙った行がぴったり最上部に来るか。
# スクロールバーの1目盛りは「表示行」なので、折り返しがあると
# ピクセル換算だけでは数行ずれる (v1.4.1 で補正ループを追加)。
WRAP_DOC = "\n\n".join(
    f"段落{i} の本文です。これは折り返しが起きる程度に長い日本語の行で、"
    f"エディタの幅によっては複数の表示行にまたがります。" for i in range(40))
win._md_editor.blockSignals(True)
win._md_editor.setPlainText(WRAP_DOC)
win._md_editor.blockSignals(False)
for w in (300, 420, 700, 1000):
    win._md_editor.resize(w, 300)
    over, exact = [], 0
    for target in range(0, 76, 2):
        win._scroll_editor_to_anchor((target, 0.0))
        got = win._md_editor.firstVisibleBlock().blockNumber()
        if got == target:
            exact += 1
        if got > target:
            over.append((target, got))
    # 行き過ぎ(狙いより下に行く)は起きてはならない。
    # 届かない(-)のは文末でスクロールしきれない場合のみ許容。
    check(f"[anchor/{w}px] 折り返し行で行き過ぎない", not over, f"over={over[:5]}")
    check(f"[anchor/{w}px] 狙った行が最上部に来る", exact == 38, f"exact={exact}/38")

# リサイズ直後 (レイアウト未確定) でもずれないか
win._md_editor.resize(380, 260)
win._scroll_editor_to_anchor((50, 0.0))
check("[anchor] レイアウト確定前でも正確",
      win._md_editor.firstVisibleBlock().blockNumber() == 50,
      str(win._md_editor.firstVisibleBlock().blockNumber()))

# 補正ループが必ず止まるか (文末を狙っても無限ループしない)
win._scroll_editor_to_anchor((10 ** 6, 0.0))
check("[anchor] 範囲外の行でも停止する", True)
win._md_editor.blockSignals(True)
win._md_editor.setPlainText(ANCHOR_DOC)
win._md_editor.blockSignals(False)
check("[anchor] None を渡しても落ちない",
      win._scroll_editor_to_anchor(None) is None, "")

# ══════════════════════════════════════════════════════════════
# v1.4.2 回帰: TXT編集モードの書式ボタン (エディタ操作を通した確認)
# ══════════════════════════════════════════════════════════════
win.edit_mode = "txt"
ed = win._md_editor


def txt_line(text, line=0, to_end=False):
    """エディタに text を入れ、指定行にカーソルを置く。"""
    ed.blockSignals(True)
    ed.setPlainText(text)
    ed.blockSignals(False)
    cur = ed.textCursor()
    cur.movePosition(QTextCursor.MoveOperation.Start)
    for _ in range(line):
        cur.movePosition(QTextCursor.MoveOperation.NextBlock)
    if to_end:
        cur.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    ed.setTextCursor(cur)


def txt_apply(text, ops, line=0, to_end=False):
    txt_line(text, line, to_end)
    for op in ops:
        op()
    return ed.toPlainText()


H1 = lambda: win._md_set_block("# ")          # noqa: E731
H2 = lambda: win._md_set_block("## ")         # noqa: E731
H3 = lambda: win._md_set_block("### ")        # noqa: E731
QT = lambda: win._md_set_block("> ")          # noqa: E731
BODY = win._md_body
LIST = win._md_toggle_unordered
NUM = win._md_toggle_ordered

TXT_CASES = [
    ("見出しを付ける", "本文\n", [H1], "# 本文\n"),
    ("H1→H2 は置き換わる", "本文\n", [H1, H2], "## 本文\n"),
    ("押し続けても積み重ならない", "本文\n", [H1, H2, H3, QT, H2], "## 本文\n"),
    ("同じ書式でトグル解除", "本文\n", [H1, H1], "本文\n"),
    ("見出しの後に本文で戻る", "本文\n", [H1, H2, H3, BODY], "本文\n"),
    ("何も書かずに見出し→本文", "\n", [H1, BODY], "\n"),
    ("何も書かずに見出し→見出し→本文", "\n", [H1, H2, BODY], "\n"),
    ("積み上がった行も一度で戻る", "## # 本文\n", [BODY], "本文\n"),
    ("見出しから箇条書きへ", "本文\n", [H1, LIST], "- 本文\n"),
    ("見出しから番号付きへ", "本文\n", [H1, NUM], "1. 本文\n"),
    ("箇条書きから本文へ", "本文\n", [LIST, BODY], "本文\n"),
    ("チェックボックスから本文へ", "- [x] やること\n", [BODY], "やること\n"),
    ("インデントを保つ", "    本文\n", [H2], "    ## 本文\n"),
]
for _name, _src, _ops, _want in TXT_CASES:
    _got = txt_apply(_src, _ops)
    check(f"[txt書式] {_name}", _got == _want, f"{_src!r} -> {_got!r} (期待 {_want!r})")

# 2 行目に適用しても他の行を壊さない
check("[txt書式] 対象は現在行だけ",
      txt_apply("1行目\n2行目\n", [H2], line=1) == "1行目\n## 2行目\n",
      txt_apply("1行目\n2行目\n", [H2], line=1))

# 折り返しのある長い行でも行頭に付く (StartOfLine は見た目の行を指すため
# v1.4.1 では行の途中に "# " が入ることがあった)
ed.setLineWrapMode(ed.LineWrapMode.WidgetWidth)
ed.resize(300, 200)
_long = "あ" * 400
_res = txt_apply(_long + "\n", [H1], to_end=True)
check("[txt書式] 折り返した行でも行頭に付く",
      _res.startswith("# ") and "#" not in _res[2:], _res[:40])

# 番号付きリストは直前の行を見て連番になる
check("[txt書式] 番号が連番になる",
      txt_apply("1. one\n次\n", [NUM], line=1) == "1. one\n2. 次\n",
      txt_apply("1. one\n次\n", [NUM], line=1))

# ══════════════════════════════════════════════════════════════
# v1.4.2 回帰: 改行の扱いの切り替え設定 (hard_breaks)
# ══════════════════════════════════════════════════════════════
check("[設定] hard_breaks の既定はオン", M._SETTINGS_DEFAULTS["hard_breaks"] is True,
      str(M._SETTINGS_DEFAULTS["hard_breaks"]))
check("[設定] 起動時に設定が読み込まれる", isinstance(win.hard_breaks, bool),
      repr(win.hard_breaks))

NL_DOC = "行1\n行2\n行3"
_was = win.hard_breaks


def wrap_html(doc, editable=False):
    """描画された本文 (.wrap の中身) だけを取り出す。

    編集モードの HTML には書式操作用の JS が付き、その中にも "<br>" という
    文字列が現れるため、ドキュメント全体を数えると判定を誤る。"""
    h = win._build_md_html(doc, editable=editable)
    i = h.index('class="wrap"')
    j = h.find('<script', i)
    return h[i:j if j != -1 else len(h)]


win.hard_breaks = True
check("[設定] オンなら改行が <br> になる", wrap_html(NL_DOC).count("<br") >= 2,
      wrap_html(NL_DOC))
check("[設定] MD編集でも <br> になる",
      wrap_html(NL_DOC, editable=True).count("<br") >= 2,
      wrap_html(NL_DOC, editable=True))

win.hard_breaks = False
_off = wrap_html(NL_DOC)
check("[設定] オフなら素の Markdown どおり連結する", "<br" not in _off, _off)
check("[設定] オフでも本文は失われない",
      all(s in _off for s in ("行1", "行2", "行3")), _off)
check("[設定] オフは MD編集にも効く",
      "<br" not in wrap_html(NL_DOC, editable=True),
      wrap_html(NL_DOC, editable=True))

# 行末2スペースの明示的な改行は、オフでも従来どおり効く
check("[設定] オフでも行末2スペースの改行は残る",
      wrap_html("行1  \n行2").count("<br") >= 1, wrap_html("行1  \n行2"))

# 設定は保存され、読み直せる
win.hard_breaks = False
win._save_app_settings()
check("[設定] オフが保存される", M.load_settings()["hard_breaks"] is False,
      str(M.load_settings()["hard_breaks"]))
win.hard_breaks = True
win._save_app_settings()
check("[設定] オンが保存される", M.load_settings()["hard_breaks"] is True,
      str(M.load_settings()["hard_breaks"]))
win.hard_breaks = _was
win._save_app_settings()

# ダイアログが値を往復できるか (全言語で文言が揃っているかも見る)
for _lang in ("ja", "en", "de", "fr"):
    _t = M.I18N[_lang]
    for _k in ("hard_breaks_label", "hard_breaks_cb", "hard_breaks_hint"):
        check(f"[設定] {_lang} に {_k} がある", bool(_t.get(_k)), _lang)
    _dlg = M.SettingsDialog(win, "Helvetica Neue", _lang, "dark", False, _t, {},
                            hard_breaks=False)
    check(f"[設定] {_lang} ダイアログがオフを反映", _dlg.get_result()[4] is False,
          str(_dlg.get_result()))
    _dlg._hard_breaks_cb.setChecked(True)
    check(f"[設定] {_lang} ダイアログがオンを返す", _dlg.get_result()[4] is True,
          str(_dlg.get_result()))
    _dlg.deleteLater()

# ══════════════════════════════════════════════════════════════
# v1.4.3 回帰: 対応言語 (中国語の追加)
# ══════════════════════════════════════════════════════════════
EXPECTED_LANGS = ["ja", "en", "de", "fr", "zh"]
check("[言語] LANGS に 5 言語ある", sorted(M.LANGS.values()) == sorted(EXPECTED_LANGS),
      str(M.LANGS))
check("[言語] 简体中文 が選べる", M.LANGS.get("简体中文") == "zh", str(M.LANGS))

# 全言語で文言のキーが揃っているか (どれか一つでも欠けると実行時に KeyError)
_base = set(M.I18N["ja"])
for _lg in EXPECTED_LANGS:
    check(f"[言語] {_lg} が I18N にある", _lg in M.I18N, str(list(M.I18N)))
    if _lg in M.I18N:
        _missing = sorted(_base - set(M.I18N[_lg]))
        _extra = sorted(set(M.I18N[_lg]) - _base)
        check(f"[言語] {_lg} のキーが揃っている", not _missing and not _extra,
              f"不足={_missing} 余分={_extra}")
        # ページ番号の前後の語は語順で片方が空になるのが正しい
        # (日本語「2 ページ目」/ 中国語「第 2 页」/ 英語「Page 2」)。
        _page_keys = {"page_label_prefix", "page_label_suffix"}
        _empty = [k for k, v in M.I18N[_lg].items()
                  if isinstance(v, str) and not v and k not in _page_keys]
        check(f"[言語] {_lg} に空の文言がない", not _empty, str(_empty))
        check(f"[言語] {_lg} のページ番号に語が付く",
              bool(M.I18N[_lg]["page_label_prefix"]
                   or M.I18N[_lg]["page_label_suffix"]),
              f"{M.I18N[_lg]['page_label_prefix']!r} / "
              f"{M.I18N[_lg]['page_label_suffix']!r}")

# 設定として保存・復元できるか
for _lg in EXPECTED_LANGS:
    win.lang = _lg
    win._save_app_settings()
    check(f"[言語] {_lg} が設定に保存される", M.load_settings()["lang"] == _lg,
          M.load_settings()["lang"])
# 未知の言語は既定へ落とす
M.save_settings({**M.load_settings(), "lang": "xx"})
check("[言語] 未知の言語は日本語に戻す", M.load_settings()["lang"] == "ja",
      M.load_settings()["lang"])
win.lang = "ja"
win._save_app_settings()

# 中国語でツールバーとダイアログが組み立てられるか
for _lg in EXPECTED_LANGS:
    win.lang = _lg
    win._sync_tb_labels()
    win._rebuild_fmt_tb()
    check(f"[言語] {_lg} でツールバーを組み立てられる",
          bool(win._back_btn.text()) and bool(win._mode_btns["view"].text()), _lg)
    _d = M.SettingsDialog(win, "Helvetica Neue", _lg, "dark", False,
                          M.I18N[_lg], {}, hard_breaks=True)
    _items = [_d._lang_cb.itemText(i) for i in range(_d._lang_cb.count())]
    check(f"[言語] {_lg} の設定に 5 言語が並ぶ", len(_items) == 5, str(_items))
    _d.deleteLater()
win.lang = "ja"
win._sync_tb_labels()
win._rebuild_fmt_tb()

# 起動時サンプルとガイドが全言語で用意されているか
# (v1.4.7: 同梱ファイル名はASCIIのみ。非ASCII名はコピー時のUnicode正規化で
#  署名シールを壊すため sample_<lang>.md に統一)
_guide_dir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "資料箱")
_guide_files = {"ja": "sample_ja.md", "en": "sample_en.md",
                "de": "sample_de.md", "fr": "sample_fr.md",
                "zh": "sample_zh.md"}
for _lg, _fn in _guide_files.items():
    check(f"[言語] {_lg} のガイドがある",
          os.path.exists(os.path.join(_guide_dir, _fn)), _fn)
    win.lang = _lg
    win._set_sample()
    check(f"[言語] {_lg} のサンプルが用意されている",
          len(win._content_text) > 50, repr(win._content_text[:30]))
win.lang = "ja"


# ══════════════════════════════════════════════════════════════
# v1.4.3 回帰: 水平線を見やすく (太さ 4px・コントラスト増)
# ══════════════════════════════════════════════════════════════
def _luminance(hexcol):
    h = hexcol.lstrip("#")

    def ch(v):
        v = int(v, 16) / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(h[0:2]) + 0.7152 * ch(h[2:4]) + 0.0722 * ch(h[4:6])


def _contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


for _theme, _pal in (("dark", M.DARK_PALETTE), ("light", M.LIGHT_PALETTE)):
    win.current_theme = _theme
    win._palette = _pal
    _css = win._css(16)
    check(f"[水平線] {_theme}: 太さ 4px", "height:4px" in _css.replace(" ", ""),
          [s for s in _css.split("}") if s.startswith("hr{")][:1])
    _hr = M._mix_hex(_pal["border"], _pal["text_dim"], 0.5)
    check(f"[水平線] {_theme}: 色が CSS に入る", _hr in _css, _hr)
    check(f"[水平線] {_theme}: 枠線色よりコントラストが高い",
          _contrast(_hr, _pal["bg2"]) > _contrast(_pal["border"], _pal["bg2"]),
          f"{_contrast(_hr, _pal['bg2']):.2f} vs {_contrast(_pal['border'], _pal['bg2']):.2f}")
win.current_theme = "dark"
win._palette = M.DARK_PALETTE

# 色の混合そのもの
check("[水平線] 混合の両端", M._mix_hex("#000000", "#ffffff", 0.0) == "#000000"
      and M._mix_hex("#000000", "#ffffff", 1.0) == "#ffffff", "")
check("[水平線] 中間色", M._mix_hex("#000000", "#ffffff", 0.5) == "#808080",
      M._mix_hex("#000000", "#ffffff", 0.5))
check("[水平線] 3桁表記を扱える", M._mix_hex("#fff", "#000", 0.0) == "#ffffff",
      M._mix_hex("#fff", "#000", 0.0))
check("[水平線] 16進以外はそのまま返す",
      M._mix_hex("rgba(1,2,3,.5)", "#000000", 0.5) == "rgba(1,2,3,.5)", "")
check("[水平線] 不正な値でも落ちない", M._mix_hex("#zzzzzz", "#000000", 0.5) == "#zzzzzz",
      "")

# ══════════════════════════════════════════════════
# v1.4.7 回帰: リンク挿入・PDF独立化・プレビュー横溢れ防止
# ══════════════════════════════════════════════════
import inspect as _inspect

# 全言語のキー数が一致する (言語追加時の検査と同様。新規キーは5言語すべてへ)。
_key_sets = {lg: set(M.I18N[lg].keys()) for lg in M.I18N}
check("[言語] 全言語のキー集合が一致",
      len({frozenset(s) for s in _key_sets.values()}) == 1,
      str({lg: len(s) for lg, s in _key_sets.items()}))
for _lg in M.I18N:
    for _k in ("link_dialog_title", "link_url_label", "link_invalid_url",
               "img_dialog_title", "img_invalid_url"):
        check(f"[言語] {_lg} に {_k} がある", _k in M.I18N[_lg], _k)

# MD編集のリンク・画像はネイティブダイアログ + _mdvLink/_mdvImage 経路。
# QWebEngine では JS prompt() が出ないため prompt() 依存は禁止。
_fmt_js = win._md_edit_fmt_js()
check("[リンク] 書式JSに prompt() が残っていない", "prompt(" not in _fmt_js, "")
for _fn in ("window._mdvLink=", "window._mdvImage=", "window._mdvSavedRange",
            "window._mdvSafeUrl=", "window._mdvRestoreRange="):
    check(f"[リンク] 書式JSに {_fn} がある", _fn in _fmt_js, _fn)
check("[リンク] Python側リンク挿入がある", hasattr(win, "_on_md_link_button"), "")
check("[リンク] Python側画像挿入がある", hasattr(win, "_on_md_image_button"), "")

# プレビュー横溢れ防止 (閲覧/MD編集/TXT編集の共通CSS)。
for _theme, _pal in (("dark", M.DARK_PALETTE), ("light", M.LIGHT_PALETTE)):
    win.current_theme = _theme
    win._palette = _pal
    _css2 = win._css(16)
    check(f"[余白] {_theme}: body横溢れ防止", "overflow-x:hidden" in _css2.replace(" ", ""), "")
    check(f"[余白] {_theme}: リンク・コード折返し",
          "overflow-wrap:anywhere" in _css2.replace(" ", ""), "")
    check(f"[余白] {_theme}: 表セル折返し", "word-break:break-word" in _css2.replace(" ", ""), "")
    check(f"[余白] {_theme}: svg上限", "svg{max-width:100%" in _css2.replace(" ", ""), "")
win.current_theme = "dark"
win._palette = M.DARK_PALETTE

# free モードの .wrap はビューポート追従 (右側の広い空白・誤スクロール防止)。
win.page_mode = "free"
_free_html = win._build_md_html("# t\n\n本文\n", editable=False)
check("[余白] freeの.wrapが幅追従する", "width:100%" in _free_html.replace(" ", ""), "")
check("[余白] 印刷CSSに切断防止がある", "break-inside:avoid" in _free_html, "")
check("[余白] 印刷CSSに背景保持がある", "print-color-adjust:exact" in _free_html, "")

# PDF書き出しは表示とは別のオフスクリーンViewで行う (表示の状態保持)。
_pdf_src = _inspect.getsource(M.MDViewerPro._export_pdf)
check("[PDF] 専用Viewで印刷する", "QWebEngineView()" in _pdf_src, "")
check("[PDF] 印刷後にViewを破棄する", "deleteLater" in _pdf_src, "")
check("[PDF] 表示ViewにPDF用HTMLを載せない",
      "_preview_web.loadFinished.connect(_do_print)" not in _pdf_src, "")
check("[PDF] 表示の復元処理が残っていない", "_restore_original" not in _pdf_src, "")

# v1.4.7 回帰: 同梱ファイル名はASCIIのみにする
# (非ASCII名はコピー時のUnicode正規化で別名になり署名シールが壊れる。
#  実際に sample_français.md の ç が NFD 化して Gatekeeper に
#  「壊れている」と判定された)
import unicodedata as _unicodedata
_sample_files = sorted(f for f in os.listdir(_guide_dir)
                      if f.startswith("sample_") and f.endswith(".md"))
check("[同梱名] sampleガイドが5言語分ある", len(_sample_files) == 5,
      repr(_sample_files))
check("[同梱名] sampleガイド名はASCIIのみ",
      all(all(ord(c) < 128 for c in f) for f in _sample_files),
      repr(_sample_files))
check("[同梱名] 資料箱内の全ファイル名がNFD安定",
      all(_unicodedata.normalize("NFD", f) == f for f in os.listdir(_guide_dir)),
      repr([f for f in os.listdir(_guide_dir)
            if _unicodedata.normalize("NFD", f) != f]))
_guide_src = _inspect.getsource(M.MDViewerPro._open_guide)
for _gf in ("sample_ja.md", "sample_en.md", "sample_de.md",
            "sample_fr.md", "sample_zh.md"):
    check(f"[同梱名] ガイド参照に {_gf} がある", _gf in _guide_src, _gf)
check("[同梱名] 旧非ASCII名の参照が残っていない",
      "sample_日本語" not in _guide_src and "sample_fran" not in _guide_src
      and "sample_中文" not in _guide_src, "")

print("=" * 60)
print(f"PASS: {PASS}   FAIL: {len(FAIL)}")
for f in FAIL:
    print("  FAIL", f)
sys.exit(1 if FAIL else 0)
