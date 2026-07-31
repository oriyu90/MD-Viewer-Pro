"""v1.4.0 Qt ウィジェット層 自動テスト (オフスクリーン).

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

print("=" * 60)
print(f"PASS: {PASS}   FAIL: {len(FAIL)}")
for f in FAIL:
    print("  FAIL", f)
sys.exit(1 if FAIL else 0)
