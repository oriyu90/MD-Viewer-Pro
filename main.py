# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Yuki_Orita
# See LICENSE and NOTICE.md for details.
# Third-party libraries (PySide6/Qt) are used under LGPL-3.0.

import sys
import os
import re
import json
import glob as glob_mod
import shutil
import socket
import ipaddress
import tempfile
import webbrowser
import base64
import urllib.request
import urllib.error
import http.client
from urllib.parse import urlparse
from typing import Optional, Dict, List
import markdown
from html.parser import HTMLParser

# QtWebEngine の sandbox は既定で有効のまま動かす（セキュリティ上の隔離を維持）。
# 開発環境で sandbox が原因で起動しない場合のみ、明示的に
#   MDVP_DISABLE_SANDBOX=1
# を設定して無効化できる。配布ビルドでは設定しないこと。
if os.environ.get("MDVP_DISABLE_SANDBOX") == "1":
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
if sys.platform == "darwin":
    # macOS固有: レイヤーベース描画の有効化。Windows/Linuxでは設定しない。
    os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QFileDialog,
    QSplitter, QMessageBox, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QSpinBox, QDialog, QDialogButtonBox, QFormLayout,
    QStackedWidget, QPushButton, QSizePolicy, QSlider,
    QComboBox, QGroupBox, QCheckBox,
    QListWidget, QListWidgetItem, QInputDialog,
)
from PySide6.QtGui import (
    QAction, QKeySequence, QTextCursor,
    QPageLayout, QPageSize, QFont, QColor, QDesktopServices,
    QFileOpenEvent, QFontMetrics, QFontDatabase, QIcon,
)
from PySide6.QtCore import (
    Qt, QMarginsF, QTimer, QUrl, QSizeF, QObject, Slot, QEvent, Signal, QEventLoop,
    QByteArray, QThread, QSize, QLockFile, QDir,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtNetwork import QLocalServer, QLocalSocket

# ════════════════════════════════════════════════
#  定数
# ════════════════════════════════════════════════
SCALE_STEPS  = [0.5, 0.75, 1.0, 1.25, 1.5]
SCALE_LABELS = ["50%", "75%", "100%", "125%", "150%"]
DEFAULT_SCALE_IDX = 2  # 100%
TB_H  = 72
FMT_H = 52
LANGS = {"日本語": "ja", "English": "en", "Deutsch": "de", "Français": "fr",
         "简体中文": "zh"}
PLUGIN_DIR    = os.path.expanduser("~/.mdviewer/themes")
SETTINGS_DIR  = os.path.expanduser("~/.mdviewer")


def _default_settings_dir() -> str:
    """プラットフォーム既定の設定ディレクトリ。
    Windowsでは %APPDATA%/MDViewerPro を正とし、旧 ~/.mdviewer があれば
    初回に中身を引き継ぐ (macOS/Linuxは従来どおり ~/.mdviewer)。"""
    if sys.platform != "win32":
        return os.path.expanduser("~/.mdviewer")
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    new_dir = os.path.join(appdata, "MDViewerPro")
    old_dir = os.path.expanduser("~/.mdviewer")
    if os.path.isdir(old_dir) and not os.path.isdir(new_dir):
        try:
            os.makedirs(new_dir, exist_ok=True)
            for name in ("settings.json",):
                src = os.path.join(old_dir, name)
                if os.path.isfile(src):
                    import shutil as _sh
                    _sh.copy2(src, os.path.join(new_dir, name))
            for sub in ("themes", "fonts"):
                sdir, ddir = os.path.join(old_dir, sub), os.path.join(new_dir, sub)
                if os.path.isdir(sdir) and not os.path.isdir(ddir):
                    import shutil as _sh
                    _sh.copytree(sdir, ddir)
        except Exception:
            pass
    return new_dir


SETTINGS_DIR = _default_settings_dir()
PLUGIN_DIR = os.path.join(SETTINGS_DIR, "themes")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
FONT_DIR      = os.path.join(SETTINGS_DIR, "fonts")
APP_VERSION   = "1.4.7"

# 開けるファイルの拡張子 (YAML を含む)
OPEN_FILTER = ("Markdown / Text / YAML "
               "(*.md *.markdown *.txt *.yml *.yaml);;All Files (*)")
SAVE_FILTER = ("Markdown (*.md);;Text (*.txt);;"
               "YAML (*.yml *.yaml);;All Files (*)")
YAML_EXTS = (".yml", ".yaml")

# プラットフォーム既定の本文フォント。Windowsに存在しないHiragino等を
# 既定にするとTahomaへ解決されるため、OS別に実在フォントを既定にする。
_DEFAULT_FONT_FAMILY = "Yu Gothic UI" if sys.platform == "win32" else "Helvetica Neue"

# 推奨フォント。表示名 → 実際に登録されうるファミリ名の候補(先に見つかった方を使う)。
# IPAmj明朝 / Source Han Serif は環境によってファミリ名が異なるため別名も見る。
RECOMMENDED_FONTS = [
    ("Yu Gothic UI",   ["Yu Gothic UI", "Yu Gothic"]),  # Windows 10/11 標準
    ("Meiryo",         ["Meiryo UI", "Meiryo"]),         # Windows 標準
    ("Helvetica Neue",   ["Helvetica Neue", "Helvetica"]),
    ("Hiragino Sans",    ["Hiragino Sans", "Hiragino Kaku Gothic ProN"]),
    ("Hiragino Mincho",  ["Hiragino Mincho ProN", "Hiragino Mincho Pro"]),
    ("IPAmj明朝",         ["IPAmjMincho", "IPAmj明朝", "IPAmj Mincho"]),
    ("Source Han Serif", ["Source Han Serif", "Source Han Serif JP",
                          "Source Han Serif JP VF", "Noto Serif CJK JP",
                          "Noto Serif JP"]),
    ("LaTeX風セリフ",     ["Latin Modern Roman", "CMU Serif", "Latin Modern Math",
                          "Times New Roman", "Times"]),
]

DARK_PALETTE = {
    "bg":            "#000000",
    "bg2":           "#111111",
    "bg3":           "#1c1c1c",
    "border":        "#2a2a2a",
    "text":          "#c0c0c0",
    "text_dim":      "#484848",
    "accent":        "#4a9eff",
    "heading":       "#7ab8f5",
    "toolbar":       "#0c0c0c",
    "btn":           "#1c1c1c",
    "btn_hover":     "#2e2e2e",
    "btn_active_bg": "#4a4a4a",
    "btn_active_fg": "#ffffff",
    "select":        "#1a3a5c",
    "code_fg":       "#e06c75",
    "row_even":      "#0d0d0d",
    "sep":           "#2a2a2a",
    "copy_btn_bg":   "rgba(50,50,50,0.85)",
    "copy_btn_fg":   "#aaaaaa",
}

LIGHT_PALETTE = {
    "bg":            "#f0f0f0",
    "bg2":           "#ffffff",
    "bg3":           "#e6e6e6",
    "border":        "#c4c4c4",
    "text":          "#000000",
    "text_dim":      "#909090",
    "accent":        "#1a6abf",
    "heading":       "#1a5fa0",
    "toolbar":       "#dcdcdc",
    "btn":           "#cccccc",
    "btn_hover":     "#bababa",
    "btn_active_bg": "#888888",
    "btn_active_fg": "#ffffff",
    "select":        "#c0d8ff",
    "code_fg":       "#c0392b",
    "row_even":      "#f4f4f4",
    "sep":           "#b0b0b0",
    "copy_btn_bg":   "rgba(180,180,180,0.85)",
    "copy_btn_fg":   "#444444",
}

_PALETTE_REQUIRED_KEYS = list(DARK_PALETTE.keys())


def _mix_hex(c1: str, c2: str, t: float) -> str:
    """16進の色 c1 と c2 を t の割合で混ぜる (t=0 で c1、t=1 で c2)。

    16進表記でない色 (プラグインテーマが rgba() 等を使った場合) は
    混ぜずに c1 をそのまま返す。"""
    def parse(c):
        c = (c or "").strip()
        if not c.startswith("#"):
            return None
        h = c[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) != 6:
            return None
        try:
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            return None

    a, b = parse(c1), parse(c2)
    if a is None or b is None:
        return c1
    t = max(0.0, min(1.0, t))
    return "#{:02x}{:02x}{:02x}".format(
        *(round(x + (y - x) * t) for x, y in zip(a, b)))

# TXT編集モードの行同期プレビュー用: ブロック分割時のリスト項目判定
_LIST_ITEM_RE = re.compile(r'^\s{0,3}([-*+]|\d+[.)])\s+')

# TXT編集モードの書式ボタン用: 行頭のブロック書式マーカー
# (見出し / 引用 / 箇条書き / 番号付き / チェックボックス)。
# インデントを除いた残りの先頭に対して、繰り返し当てて使う。
# 見出しと引用は markdown 側が空白なしでも解釈する ("#見出し" が <h1> になる)
# ため、ここでも空白を必須にしない。逆に箇条書き・番号は空白が要るので必須。
_BLOCK_MARKER_RE = re.compile(
    r'^(?:#{1,6}[ \t]*|>[ \t]?|[-*+][ \t]+(?:\[[ xX]\][ \t]+)?|\d+\.[ \t]+)')

I18N = {
    "ja": {
        "back": "戻る", "view": "閲覧", "md_edit": "MD編集", "txt_edit": "TXT編集",
        "free": "フリー", "a4": "A4文書", "b5": "B5文書", "margin": "余白設定",
        "scale": "スケール", "settings": "詳細設定",
        "pdf_export": "PDF書き出し",
        "file": "ファイル", "open": "開く...", "save": "保存", "new": "新規作成",
        "save_as": "名前を付けて保存...",
        "pdf_export_menu": "PDFとして書き出し...",
        "html_export_menu": "HTMLとして書き出し...",
        "upload_gdrive": "Google Drive へアップロード...",
        "upload_onedrive": "OneDrive へアップロード...",
        "unsaved": "未保存の変更",
        "unsaved_msg": "変更が保存されていません。保存しますか？",
        "read_error": "読み込みエラー", "save_error": "保存エラー",
        "capture_error": "編集内容を取得できませんでした。文書を開いたまま再試行してください。",
        "settings_title": "詳細設定",
        "font_label": "フォント", "lang_label": "言語", "theme_label": "テーマ",
        "dark": "ダークモード", "light": "ライトモード",
        "bold_label": "テキスト太字強調",
        "hard_breaks_label": "改行の扱い",
        "hard_breaks_cb": "改行をそのまま改行として表示する",
        "hard_breaks_hint": "オフにすると、素の Markdown 仕様どおり単一の改行は\n"
                            "前の行につながります（改行するには行末に半角スペース\n"
                            "2個、または空行が必要になります）。",
        "plugin_label": "プラグインテーマ",
        "plugin_dir_btn": "テーマフォルダを開く",
        "untitled": "無題",
        "margin_title": "A4余白設定 (mm)",
        "margin_title_b5": "B5余白設定 (mm)",
        "margin_top": "上", "margin_right": "右",
        "margin_bottom": "下", "margin_left": "左",
        "fmt_bold": "B", "fmt_italic": "I", "fmt_strike": "~~", "fmt_code": "コード",
        "fmt_h1": "H1", "fmt_h2": "H2", "fmt_h3": "H3", "fmt_body": "本文",
        "fmt_list": "リスト", "fmt_num": "番号", "fmt_check": "チェック",
        "fmt_quote": "引用", "fmt_hr": "水平線", "fmt_link": "リンク",
        "fmt_img": "画像", "fmt_table": "テーブル",
        "gdrive_msg": "ファイル: {fname}\n\nGoogle Drive を開きます。\n"
                      "「+ 新規」→「ファイルのアップロード」からアップロードしてください。",
        "onedrive_msg": "ファイル: {fname}\n\nOneDrive を開きます。\n"
                        "「アップロード」→「ファイル」からアップロードしてください。",
        "unsaved_file": "（未保存）",
        "pdf_settings_title": "PDF書き出し設定",
        "pdf_page_size": "用紙サイズ",
        "pdf_orientation": "方向",
        "pdf_portrait": "縦向き",
        "pdf_landscape": "横向き",
        "pdf_success": "PDFを正常に書き出しました。",
        "pdf_error": "PDF書き出しに失敗しました。",
        "html_export_success": "HTMLを正常に書き出しました。",
        "html_save_error": "HTML保存エラー",
        "img_confirm_title": "外部画像の読み込み",
        "img_confirm_msg": "このファイルには {n} 個の外部画像リンクが含まれています。\n"
                           "外部サーバーから画像を読み込みますか？",
        "startup_title": "MD Viewer Pro",
        "startup_open": "ファイルを開く",
        "startup_new": "新規作成",
        "startup_hint": "開くファイルを選択するか、新規ファイルを作成します",
        "startup_language": "言語",
        "startup_guide": "説明を開く",
        "readonly_notice": "読み取り専用",
        "plugin_invalid": "テーマファイルが無効です: {name}",
        "toc": "目次",
        "pdf_embed_images": "画像を含める",
        "pdf_embed_images_label": "PDFに画像を埋め込む",
        "pdf_style_mode": "スタイルモード",
        "new_window": "新規ウィンドウ",
        "toc_title": "≡ 目次",
        "toc_empty": "見出しがありません",
        "link_text_default": "テキスト",
        "img_alt_default": "説明",
        "img_url_prompt": "画像URL",
        "link_dialog_title": "リンクの挿入",
        "link_url_label": "URL:",
        "link_invalid_url": "URLが無効です。http(s)://、mailto:、tel:、#、/、相対パスのいずれかで入力してください。",
        "img_dialog_title": "画像の挿入",
        "img_invalid_url": "画像URLが無効です。http(s):// または相対パスで入力してください。",
        "table_col": "列",
        "table_cell": "セル",
        "table_add_col": "+ 列",
        "table_add_col_title": "列を追加",
        "table_add_row": "+ 行",
        "table_add_row_title": "行を追加",
        "page_label_prefix": "",
        "page_label_suffix": " ページ目",
        "font_recommended": "推奨フォント",
        "font_user": "追加したフォント",
        "font_system": "システムフォント",
        "font_not_installed": "（未インストール）",
        "font_add": "フォントを追加...",
        "font_remove": "選択中のフォントを削除",
        "font_add_title": "フォントファイルを選択",
        "font_add_error": "フォントの追加に失敗しました。",
        "font_add_invalid": "このファイルはフォントとして読み込めませんでした。",
        "font_remove_title": "フォントの削除",
        "font_remove_msg": "追加したフォント「{name}」を削除しますか？",
        "font_hint": "未インストールの推奨フォントは「フォントを追加...」から\n"
                     "TTF/OTF ファイルを登録すると使えるようになります。",
        "front_matter": "フロントマター",
        "yaml_doc": "YAML ドキュメント",
    },
    "en": {
        "back": "Back", "view": "View", "md_edit": "MD Edit", "txt_edit": "TXT Edit",
        "free": "Free", "a4": "A4 Doc", "b5": "B5 Doc", "margin": "Margins",
        "scale": "Scale", "settings": "Settings",
        "pdf_export": "Export PDF",
        "file": "File", "open": "Open...", "save": "Save", "new": "New",
        "save_as": "Save As...",
        "pdf_export_menu": "Export as PDF...",
        "html_export_menu": "Export as HTML...",
        "upload_gdrive": "Upload to Google Drive...",
        "upload_onedrive": "Upload to OneDrive...",
        "unsaved": "Unsaved Changes",
        "unsaved_msg": "You have unsaved changes. Save now?",
        "read_error": "Read Error", "save_error": "Save Error",
        "capture_error": "Could not retrieve the edits. Keep the document open and try again.",
        "settings_title": "Settings",
        "font_label": "Font", "lang_label": "Language", "theme_label": "Theme",
        "dark": "Dark Mode", "light": "Light Mode",
        "bold_label": "Bold Text Emphasis",
        "hard_breaks_label": "Line Breaks",
        "hard_breaks_cb": "Render a single newline as a line break",
        "hard_breaks_hint": "When off, standard Markdown rules apply: a single\n"
                            "newline joins onto the previous line, and breaking a\n"
                            "line needs two trailing spaces or a blank line.",
        "plugin_label": "Plugin Theme",
        "plugin_dir_btn": "Open Theme Folder",
        "untitled": "Untitled",
        "margin_title": "A4 Margins (mm)",
        "margin_title_b5": "B5 Margins (mm)",
        "margin_top": "Top", "margin_right": "Right",
        "margin_bottom": "Bottom", "margin_left": "Left",
        "fmt_bold": "B", "fmt_italic": "I", "fmt_strike": "~~", "fmt_code": "Code",
        "fmt_h1": "H1", "fmt_h2": "H2", "fmt_h3": "H3", "fmt_body": "Body",
        "fmt_list": "List", "fmt_num": "Num", "fmt_check": "Check",
        "fmt_quote": "Quote", "fmt_hr": "HR", "fmt_link": "Link",
        "fmt_img": "Image", "fmt_table": "Table",
        "gdrive_msg": "File: {fname}\n\nOpening Google Drive.\n"
                      "Use '+ New' → 'File upload' to upload your file.",
        "onedrive_msg": "File: {fname}\n\nOpening OneDrive.\n"
                        "Use 'Upload' → 'Files' to upload your file.",
        "unsaved_file": "(Unsaved)",
        "pdf_settings_title": "PDF Export Settings",
        "pdf_page_size": "Page Size",
        "pdf_orientation": "Orientation",
        "pdf_portrait": "Portrait",
        "pdf_landscape": "Landscape",
        "pdf_success": "PDF exported successfully.",
        "pdf_error": "Failed to export PDF.",
        "html_export_success": "HTML exported successfully.",
        "html_save_error": "HTML Save Error",
        "img_confirm_title": "Load External Images",
        "img_confirm_msg": "This file contains {n} external image(s).\n"
                           "Load images from external servers?",
        "startup_title": "MD Viewer Pro",
        "startup_open": "Open File",
        "startup_new": "New File",
        "startup_hint": "Choose a file to open or create a new one",
        "startup_language": "Language",
        "startup_guide": "Open Guide",
        "readonly_notice": "Read Only",
        "plugin_invalid": "Invalid theme file: {name}",
        "toc": "TOC",
        "pdf_embed_images": "Include images",
        "pdf_embed_images_label": "Embed images in PDF",
        "pdf_style_mode": "Style Mode",
        "new_window": "New Window",
        "toc_title": "≡ Contents",
        "toc_empty": "No headings",
        "link_text_default": "Text",
        "img_alt_default": "Description",
        "img_url_prompt": "Image URL",
        "link_dialog_title": "Insert Link",
        "link_url_label": "URL:",
        "link_invalid_url": "Invalid URL. Use http(s)://, mailto:, tel:, #, /, or a relative path.",
        "img_dialog_title": "Insert Image",
        "img_invalid_url": "Invalid image URL. Use http(s):// or a relative path.",
        "table_col": "Col",
        "table_cell": "Cell",
        "table_add_col": "+ Col",
        "table_add_col_title": "Add column",
        "table_add_row": "+ Row",
        "table_add_row_title": "Add row",
        "page_label_prefix": "Page ",
        "page_label_suffix": "",
        "font_recommended": "Recommended fonts",
        "font_user": "Added fonts",
        "font_system": "System fonts",
        "font_not_installed": " (not installed)",
        "font_add": "Add Font...",
        "font_remove": "Remove selected font",
        "font_add_title": "Choose a font file",
        "font_add_error": "Failed to add the font.",
        "font_add_invalid": "This file could not be loaded as a font.",
        "font_remove_title": "Remove Font",
        "font_remove_msg": "Remove the added font \"{name}\"?",
        "font_hint": "Recommended fonts that are not installed become available\n"
                     "once you register a TTF/OTF file via 'Add Font...'.",
        "front_matter": "Front matter",
        "yaml_doc": "YAML document",
    },
    "de": {
        "back": "Zurück", "view": "Ansicht", "md_edit": "MD Bearbeiten", "txt_edit": "TXT Bearbeiten",
        "free": "Frei", "a4": "A4 Dok.", "b5": "B5 Dok.", "margin": "Ränder",
        "scale": "Skalierung", "settings": "Einstellungen",
        "pdf_export": "PDF exportieren",
        "file": "Datei", "open": "Öffnen...", "save": "Speichern", "new": "Neu",
        "save_as": "Speichern unter...",
        "pdf_export_menu": "Als PDF exportieren...",
        "html_export_menu": "Als HTML exportieren...",
        "upload_gdrive": "Auf Google Drive hochladen...",
        "upload_onedrive": "Auf OneDrive hochladen...",
        "unsaved": "Ungespeicherte Änderungen",
        "unsaved_msg": "Sie haben ungespeicherte Änderungen. Jetzt speichern?",
        "read_error": "Lesefehler", "save_error": "Speicherfehler",
        "capture_error": "Änderungen konnten nicht abgerufen werden. Dokument geöffnet lassen und erneut versuchen.",
        "settings_title": "Einstellungen",
        "font_label": "Schriftart", "lang_label": "Sprache", "theme_label": "Thema",
        "dark": "Dunkelmodus", "light": "Hellmodus",
        "bold_label": "Fettschrift-Hervorhebung",
        "hard_breaks_label": "Zeilenumbrüche",
        "hard_breaks_cb": "Einzelnen Zeilenumbruch als Umbruch darstellen",
        "hard_breaks_hint": "Ausgeschaltet gelten die Markdown-Regeln: ein einzelner\n"
                            "Umbruch hängt an der vorherigen Zeile an; ein Umbruch\n"
                            "braucht zwei Leerzeichen am Zeilenende oder eine Leerzeile.",
        "plugin_label": "Plugin-Thema",
        "plugin_dir_btn": "Themenordner öffnen",
        "untitled": "Unbenannt",
        "margin_title": "A4-Ränder (mm)",
        "margin_title_b5": "B5-Ränder (mm)",
        "margin_top": "Oben", "margin_right": "Rechts",
        "margin_bottom": "Unten", "margin_left": "Links",
        "fmt_bold": "B", "fmt_italic": "I", "fmt_strike": "~~", "fmt_code": "Code",
        "fmt_h1": "H1", "fmt_h2": "H2", "fmt_h3": "H3", "fmt_body": "Text",
        "fmt_list": "Liste", "fmt_num": "Num.", "fmt_check": "Check",
        "fmt_quote": "Zitat", "fmt_hr": "HR", "fmt_link": "Link",
        "fmt_img": "Bild", "fmt_table": "Tabelle",
        "gdrive_msg": "Datei: {fname}\n\nÖffnet Google Drive.\n"
                      "Verwenden Sie '+ Neu' → 'Datei hochladen'.",
        "onedrive_msg": "Datei: {fname}\n\nÖffnet OneDrive.\n"
                        "Verwenden Sie 'Hochladen' → 'Dateien'.",
        "unsaved_file": "(Ungespeichert)",
        "pdf_settings_title": "PDF-Exporteinstellungen",
        "pdf_page_size": "Seitengröße",
        "pdf_orientation": "Ausrichtung",
        "pdf_portrait": "Hochformat",
        "pdf_landscape": "Querformat",
        "pdf_success": "PDF erfolgreich exportiert.",
        "pdf_error": "PDF-Export fehlgeschlagen.",
        "html_export_success": "HTML erfolgreich exportiert.",
        "html_save_error": "HTML-Speicherfehler",
        "img_confirm_title": "Externe Bilder laden",
        "img_confirm_msg": "Diese Datei enthält {n} externe(s) Bild(er).\n"
                           "Bilder von externen Servern laden?",
        "startup_title": "MD Viewer Pro",
        "startup_open": "Datei öffnen",
        "startup_new": "Neue Datei",
        "startup_hint": "Datei auswählen oder neue Datei erstellen",
        "startup_language": "Sprache",
        "startup_guide": "Anleitung öffnen",
        "readonly_notice": "Schreibgeschützt",
        "plugin_invalid": "Ungültige Thema-Datei: {name}",
        "toc": "Inhalt",
        "pdf_embed_images": "Bilder einbetten",
        "pdf_embed_images_label": "Bilder in PDF einbetten",
        "pdf_style_mode": "Stilmodus",
        "new_window": "Neues Fenster",
        "toc_title": "≡ Inhalt",
        "toc_empty": "Keine Überschriften",
        "link_text_default": "Text",
        "img_alt_default": "Beschreibung",
        "img_url_prompt": "Bild-URL",
        "link_dialog_title": "Link einfügen",
        "link_url_label": "URL:",
        "link_invalid_url": "Ungültige URL. Verwenden Sie http(s)://, mailto:, tel:, #, / oder einen relativen Pfad.",
        "img_dialog_title": "Bild einfügen",
        "img_invalid_url": "Ungültige Bild-URL. Verwenden Sie http(s):// oder einen relativen Pfad.",
        "table_col": "Sp.",
        "table_cell": "Zelle",
        "table_add_col": "+ Sp.",
        "table_add_col_title": "Spalte hinzufügen",
        "table_add_row": "+ Zeile",
        "table_add_row_title": "Zeile hinzufügen",
        "page_label_prefix": "Seite ",
        "page_label_suffix": "",
        "font_recommended": "Empfohlene Schriftarten",
        "font_user": "Hinzugefügte Schriftarten",
        "font_system": "Systemschriftarten",
        "font_not_installed": " (nicht installiert)",
        "font_add": "Schriftart hinzufügen...",
        "font_remove": "Ausgewählte Schriftart entfernen",
        "font_add_title": "Schriftdatei auswählen",
        "font_add_error": "Die Schriftart konnte nicht hinzugefügt werden.",
        "font_add_invalid": "Diese Datei konnte nicht als Schriftart geladen werden.",
        "font_remove_title": "Schriftart entfernen",
        "font_remove_msg": "Hinzugefügte Schriftart „{name}“ entfernen?",
        "font_hint": "Nicht installierte empfohlene Schriftarten stehen zur Verfügung,\n"
                     "sobald Sie über „Schriftart hinzufügen...“ eine TTF/OTF-Datei registrieren.",
        "front_matter": "Front Matter",
        "yaml_doc": "YAML-Dokument",
    },
    "fr": {
        "back": "Retour", "view": "Vue", "md_edit": "Édition MD", "txt_edit": "Édition TXT",
        "free": "Libre", "a4": "Doc A4", "b5": "Doc B5", "margin": "Marges",
        "scale": "Échelle", "settings": "Paramètres",
        "pdf_export": "Exporter PDF",
        "file": "Fichier", "open": "Ouvrir...", "save": "Enregistrer", "new": "Nouveau",
        "save_as": "Enregistrer sous...",
        "pdf_export_menu": "Exporter en PDF...",
        "html_export_menu": "Exporter en HTML...",
        "upload_gdrive": "Télécharger sur Google Drive...",
        "upload_onedrive": "Télécharger sur OneDrive...",
        "unsaved": "Modifications non enregistrées",
        "unsaved_msg": "Vous avez des modifications non enregistrées. Enregistrer maintenant?",
        "read_error": "Erreur de lecture", "save_error": "Erreur d'enregistrement",
        "capture_error": "Impossible de récupérer les modifications. Gardez le document ouvert et réessayez.",
        "settings_title": "Paramètres",
        "font_label": "Police", "lang_label": "Langue", "theme_label": "Thème",
        "dark": "Mode sombre", "light": "Mode clair",
        "bold_label": "Emphase en gras",
        "hard_breaks_label": "Sauts de ligne",
        "hard_breaks_cb": "Afficher un saut de ligne simple comme un retour à la ligne",
        "hard_breaks_hint": "Désactivé, les règles Markdown s'appliquent : un saut de\n"
                            "ligne simple rejoint la ligne précédente ; il faut deux\n"
                            "espaces en fin de ligne ou une ligne vide pour couper.",
        "plugin_label": "Thème plugin",
        "plugin_dir_btn": "Ouvrir le dossier des thèmes",
        "untitled": "Sans titre",
        "margin_title": "Marges A4 (mm)",
        "margin_title_b5": "Marges B5 (mm)",
        "margin_top": "Haut", "margin_right": "Droite",
        "margin_bottom": "Bas", "margin_left": "Gauche",
        "fmt_bold": "G", "fmt_italic": "I", "fmt_strike": "~~", "fmt_code": "Code",
        "fmt_h1": "H1", "fmt_h2": "H2", "fmt_h3": "H3", "fmt_body": "Corps",
        "fmt_list": "Liste", "fmt_num": "Num.", "fmt_check": "Case",
        "fmt_quote": "Citation", "fmt_hr": "Ligne", "fmt_link": "Lien",
        "fmt_img": "Image", "fmt_table": "Tableau",
        "gdrive_msg": "Fichier: {fname}\n\nOuverture de Google Drive.\n"
                      "Utilisez '+ Nouveau' → 'Importer un fichier'.",
        "onedrive_msg": "Fichier: {fname}\n\nOuverture de OneDrive.\n"
                        "Utilisez 'Télécharger' → 'Fichiers'.",
        "unsaved_file": "(Non enregistré)",
        "pdf_settings_title": "Paramètres d'export PDF",
        "pdf_page_size": "Format de page",
        "pdf_orientation": "Orientation",
        "pdf_portrait": "Portrait",
        "pdf_landscape": "Paysage",
        "pdf_success": "PDF exporté avec succès.",
        "pdf_error": "Échec de l'export PDF.",
        "html_export_success": "HTML exporté avec succès.",
        "html_save_error": "Erreur d'enregistrement HTML",
        "img_confirm_title": "Charger des images externes",
        "img_confirm_msg": "Ce fichier contient {n} image(s) externe(s).\n"
                           "Charger les images depuis des serveurs externes?",
        "startup_title": "MD Viewer Pro",
        "startup_open": "Ouvrir un fichier",
        "startup_new": "Nouveau fichier",
        "startup_hint": "Choisissez un fichier ou créez-en un nouveau",
        "startup_language": "Langue",
        "startup_guide": "Ouvrir le guide",
        "readonly_notice": "Lecture seule",
        "plugin_invalid": "Fichier de thème invalide: {name}",
        "toc": "Sommaire",
        "pdf_embed_images": "Inclure les images",
        "pdf_embed_images_label": "Intégrer les images dans le PDF",
        "pdf_style_mode": "Mode de style",
        "new_window": "Nouvelle fenêtre",
        "toc_title": "≡ Sommaire",
        "toc_empty": "Aucun titre",
        "link_text_default": "Texte",
        "img_alt_default": "Description",
        "img_url_prompt": "URL de l'image",
        "link_dialog_title": "Insérer un lien",
        "link_url_label": "URL :",
        "link_invalid_url": "URL invalide. Utilisez http(s)://, mailto:, tel:, #, / ou un chemin relatif.",
        "img_dialog_title": "Insérer une image",
        "img_invalid_url": "URL d'image invalide. Utilisez http(s):// ou un chemin relatif.",
        "table_col": "Col",
        "table_cell": "Cellule",
        "table_add_col": "+ Col",
        "table_add_col_title": "Ajouter une colonne",
        "table_add_row": "+ Ligne",
        "table_add_row_title": "Ajouter une ligne",
        "page_label_prefix": "Page ",
        "page_label_suffix": "",
        "font_recommended": "Polices recommandées",
        "font_user": "Polices ajoutées",
        "font_system": "Polices système",
        "font_not_installed": " (non installée)",
        "font_add": "Ajouter une police...",
        "font_remove": "Supprimer la police sélectionnée",
        "font_add_title": "Choisir un fichier de police",
        "font_add_error": "Échec de l'ajout de la police.",
        "font_add_invalid": "Ce fichier n'a pas pu être chargé comme police.",
        "font_remove_title": "Supprimer la police",
        "font_remove_msg": "Supprimer la police ajoutée « {name} » ?",
        "font_hint": "Les polices recommandées non installées deviennent disponibles\n"
                     "après avoir enregistré un fichier TTF/OTF via « Ajouter une police... ».",
        "front_matter": "En-tête YAML",
        "yaml_doc": "Document YAML",
    },
    "zh": {
        "back": "返回", "view": "阅读", "md_edit": "MD编辑", "txt_edit": "TXT编辑",
        "free": "自由", "a4": "A4文档", "b5": "B5文档", "margin": "页边距",
        "scale": "缩放", "settings": "设置", "pdf_export": "导出PDF",
        "file": "文件", "open": "打开...", "save": "保存", "new": "新建",
        "save_as": "另存为...",
        "pdf_export_menu": "导出为 PDF...",
        "html_export_menu": "导出为 HTML...",
        "upload_gdrive": "上传到 Google Drive...",
        "upload_onedrive": "上传到 OneDrive...",
        "unsaved": "有未保存的更改",
        "unsaved_msg": "有尚未保存的更改。现在保存吗？",
        "read_error": "读取错误", "save_error": "保存错误",
        "capture_error": "无法获取编辑内容。请保持文档打开并重试。",
        "settings_title": "设置",
        "font_label": "字体", "lang_label": "语言", "theme_label": "主题",
        "dark": "深色模式", "light": "浅色模式",
        "bold_label": "正文加粗",
        "hard_breaks_label": "换行的处理",
        "hard_breaks_cb": "把输入的换行直接显示为换行",
        "hard_breaks_hint": "关闭后按标准 Markdown 规则处理：单个换行会\n"
                            "接到上一行，要换行需要在行尾加两个空格或\n"
                            "插入一个空行。",
        "plugin_label": "插件主题", "plugin_dir_btn": "打开主题文件夹",
        "untitled": "未命名",
        "margin_title": "A4 页边距 (mm)", "margin_title_b5": "B5 页边距 (mm)",
        "margin_top": "上", "margin_right": "右",
        "margin_bottom": "下", "margin_left": "左",
        "fmt_bold": "B", "fmt_italic": "I", "fmt_strike": "~~",
        "fmt_code": "代码", "fmt_h1": "H1", "fmt_h2": "H2", "fmt_h3": "H3",
        "fmt_body": "正文", "fmt_list": "项目", "fmt_num": "编号",
        "fmt_check": "清单", "fmt_quote": "引用", "fmt_hr": "横线",
        "fmt_link": "链接", "fmt_img": "图片", "fmt_table": "表格",
        "gdrive_msg": "文件：{fname}\n\n正在打开 Google Drive。\n"
                      "请使用「+ 新建」→「文件上传」上传文件。",
        "onedrive_msg": "文件：{fname}\n\n正在打开 OneDrive。\n"
                        "请使用「上传」→「文件」上传文件。",
        "unsaved_file": "（未保存）",
        "pdf_settings_title": "PDF 导出设置",
        "pdf_page_size": "纸张大小", "pdf_orientation": "方向",
        "pdf_portrait": "纵向", "pdf_landscape": "横向",
        "pdf_success": "PDF 导出成功。", "pdf_error": "PDF 导出失败。",
        "html_export_success": "HTML 导出成功。",
        "html_save_error": "HTML 保存错误",
        "img_confirm_title": "载入外部图片",
        "img_confirm_msg": "此文件包含 {n} 张外部图片。\n要从外部服务器载入吗？",
        "startup_title": "MD Viewer Pro",
        "startup_open": "打开文件", "startup_new": "新建文件",
        "startup_hint": "请选择要打开的文件，或新建一个文件",
        "startup_language": "语言", "startup_guide": "打开使用指南",
        "readonly_notice": "只读",
        "plugin_invalid": "主题文件无效：{name}",
        "toc": "目录",
        "pdf_embed_images": "包含图片",
        "pdf_embed_images_label": "在 PDF 中嵌入图片",
        "pdf_style_mode": "样式",
        "new_window": "新建窗口",
        "toc_title": "≡ 目录", "toc_empty": "没有标题",
        "link_text_default": "文字", "img_alt_default": "说明",
        "img_url_prompt": "图片网址",
        "link_dialog_title": "插入链接",
        "link_url_label": "URL：",
        "link_invalid_url": "URL 无效。请使用 http(s)://、mailto:、tel:、#、/ 或相对路径。",
        "img_dialog_title": "插入图片",
        "img_invalid_url": "图片 URL 无效。请使用 http(s):// 或相对路径。",
        "table_col": "列", "table_cell": "单元格",
        "table_add_col": "+ 列", "table_add_col_title": "添加列",
        "table_add_row": "+ 行", "table_add_row_title": "添加行",
        "page_label_prefix": "第 ", "page_label_suffix": " 页",
        "font_recommended": "推荐字体", "font_user": "已添加的字体",
        "font_system": "系统字体", "font_not_installed": "（未安装）",
        "font_add": "添加字体...", "font_remove": "删除所选字体",
        "font_add_title": "选择字体文件",
        "font_add_error": "添加字体失败。",
        "font_add_invalid": "该文件无法作为字体载入。",
        "font_remove_title": "删除字体",
        "font_remove_msg": "要删除已添加的字体「{name}」吗？",
        "font_hint": "未安装的推荐字体，可通过「添加字体...」注册\n"
                     "TTF/OTF 文件后使用。",
        "front_matter": "前置元数据", "yaml_doc": "YAML 文档",
    },
}


# ════════════════════════════════════════════════
#  設定の読み書き
# ════════════════════════════════════════════════
_SETTINGS_DEFAULTS: dict = {
    "lang":             "ja",
    "theme":            "dark",
    "font_family":      _DEFAULT_FONT_FAMILY,
    "bold_mode":        False,
    "scale_idx":        DEFAULT_SCALE_IDX,
    "last_pdf_dir":     "",
    "pdf_embed_images": True,
    "window_geometry":  "",
    # 目次は既定でオン。機能の存在に気づいてもらうため、初回起動時から開いた状態にする。
    "show_toc":         True,
    # 改行の扱い。既定はオン (Enter で入れた改行をそのまま改行として表示する)。
    # オフにすると素の Markdown 仕様どおり、単一の改行は前の行に連結される。
    "hard_breaks":      True,
}

def load_settings() -> dict:
    result = dict(_SETTINGS_DEFAULTS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in _SETTINGS_DEFAULTS.items():
            if k in data:
                result[k] = data[k]
        result["scale_idx"] = max(0, min(len(SCALE_STEPS) - 1, int(result["scale_idx"])))
        result["show_toc"] = bool(result["show_toc"])
        result["hard_breaks"] = bool(result["hard_breaks"])
        if result["lang"] not in ("ja", "en", "de", "fr", "zh"):
            result["lang"] = "ja"
        if not result["last_pdf_dir"] or not os.path.isdir(result["last_pdf_dir"]):
            result["last_pdf_dir"] = os.path.expanduser("~")
    except Exception:
        result["last_pdf_dir"] = os.path.expanduser("~")
    return result

def save_settings(settings: dict):
    try:
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ════════════════════════════════════════════════
#  フォント管理 — ユーザーが追加した TTF/OTF を扱う
#
#  ~/.mdviewer/fonts/ に置かれたフォントを起動時に Qt へ登録する。
#  「追加」でファイルをこのフォルダへ取り込み、「削除」で取り除く。
#  システムに元から入っているフォントは対象外 (削除できない)。
# ════════════════════════════════════════════════
_USER_FONTS: Dict[str, str] = {}      # ファミリ名 → フォントファイルのパス
_USER_FONT_IDS: Dict[str, int] = {}   # フォントファイルのパス → Qt の登録 ID
_FONT_EXTS = (".ttf", ".otf", ".ttc", ".otc")


def _register_font_file(path: str) -> List[str]:
    """フォントファイルを Qt に登録し、追加されたファミリ名を返す。"""
    try:
        fid = QFontDatabase.addApplicationFont(path)
    except Exception:
        return []
    if fid < 0:
        return []
    try:
        fams = list(QFontDatabase.applicationFontFamilies(fid))
    except Exception:
        fams = []
    if not fams:
        return []
    _USER_FONT_IDS[path] = fid
    for fam in fams:
        _USER_FONTS[fam] = path
    return fams


def load_user_fonts() -> Dict[str, str]:
    """~/.mdviewer/fonts/ 内のフォントをすべて登録する (起動時に一度)。"""
    _USER_FONTS.clear()
    _USER_FONT_IDS.clear()
    try:
        os.makedirs(FONT_DIR, exist_ok=True)
    except Exception:
        return _USER_FONTS
    for path in sorted(glob_mod.glob(os.path.join(FONT_DIR, "*"))):
        if path.lower().endswith(_FONT_EXTS):
            _register_font_file(path)
    return _USER_FONTS


def add_user_font(src_path: str) -> List[str]:
    """フォントファイルを取り込んで登録する。追加されたファミリ名を返す。"""
    try:
        os.makedirs(FONT_DIR, exist_ok=True)
        dest = os.path.join(FONT_DIR, os.path.basename(src_path))
        if os.path.abspath(src_path) != os.path.abspath(dest):
            shutil.copy2(src_path, dest)
    except Exception:
        return []
    fams = _register_font_file(dest)
    if not fams:
        # フォントとして読めなかったファイルは取り込まない
        try:
            os.remove(dest)
        except Exception:
            pass
    return fams


def remove_user_font(family: str) -> bool:
    """ユーザーが追加したフォントを登録解除してファイルごと削除する。"""
    path = _USER_FONTS.get(family)
    if not path:
        return False
    fid = _USER_FONT_IDS.pop(path, None)
    if fid is not None:
        try:
            QFontDatabase.removeApplicationFont(fid)
        except Exception:
            pass
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        return False
    for fam in [f for f, p in _USER_FONTS.items() if p == path]:
        _USER_FONTS.pop(fam, None)
    return True




def _bundled_file(*parts: str) -> Optional[str]:
    """同梱ファイルの実パス。PyInstaller (_MEIPASS) とソース実行の両対応。
    見つからなければ None。"""
    if hasattr(sys, "_MEIPASS"):
        p = os.path.join(sys._MEIPASS, *parts)
        if os.path.isfile(p):
            return p
    base = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, *parts)
    return p if os.path.isfile(p) else None


# ════════════════════════════════════════════════
#  QApplication サブクラス — macOS ファイルオープンイベント / マルチウィンドウ対応
# ════════════════════════════════════════════════
class MDApplication(QApplication):
    # 二重起動防止のローカルサーバー名。2つ目以降の起動はここへ
    # ファイルパスを送り、既存プロセス側で開いて終了する。
    # (Windowsで .md をダブルクリックし続けてもプロセスが増えないように)
    _SINGLE_INSTANCE_NAME = "MDViewerPro-single-instance"

    def __init__(self, argv):
        super().__init__(argv)
        self._windows: List["MDViewerPro"] = []
        self.setQuitOnLastWindowClosed(False)
        # ユーザーが追加したフォントは、ウィンドウを作る前に登録しておく
        # (QFontDatabase は QGuiApplication 生成後でないと使えない)
        load_user_fonts()
        self._dock_menu: Optional[object] = None
        self._setup_dock_menu()
        self._local_server: Optional[QLocalServer] = None
        self._lock_file: Optional[QLockFile] = None
        self._is_primary = False
        self._acquire_primary()

    # ─── 新規ウィンドウ ──────────────────────────
    def new_window(self) -> "MDViewerPro":
        win = MDViewerPro()
        win.show()
        win.raise_()
        win.activateWindow()
        self._windows.append(win)
        win.window_closed.connect(lambda w=win: self._on_window_closed(w))
        return win

    def _on_window_closed(self, win: "MDViewerPro"):
        if win in self._windows:
            self._windows.remove(win)
        if not self._windows:
            self.quit()

    # ─── シングルインスタンス ──────────────────────
    # プライマリ判定は QLockFile で行う。QLocalServer.listen() は Windows で
    # 同名パイプの二重待ち受けを成功扱いにすることがあるため、listen の成否を
    # プライマリ判定に使わない。メッセージ転送のパイプ自体は QLocalServer を使う。
    def _acquire_primary(self) -> bool:
        """ロックが取れれば待ち受けて True。取れなければ False (転送側に回る)。
        判定不能時は True (通常起動。二重起動の可能性は残る)。"""
        try:
            if self._lock_file is None:
                self._lock_file = QLockFile(
                    QDir.temp().absoluteFilePath("MDViewerPro-single-instance.lock"))
            if not self._lock_file.tryLock(0):
                self._is_primary = False
                return False
            try:
                server = QLocalServer(self)
                if server.listen(self._SINGLE_INSTANCE_NAME):
                    server.newConnection.connect(self._on_single_instance_message)
                    self._local_server = server
            except Exception:
                pass
            self._is_primary = True
            return True
        except Exception:
            self._is_primary = True
            return True

    def is_primary_instance(self) -> bool:
        return self._is_primary

    def forward_to_primary(self, path: Optional[str]) -> bool:
        """既存プロセスへパスを送れたら True。送れなければ False。
        古いサーバー名が残っているだけの場合は取り除いて False を返す
        (呼び出し側は待ち受け直して通常起動する)。"""
        try:
            sock = QLocalSocket(self)
            sock.connectToServer(self._SINGLE_INSTANCE_NAME)
            if not sock.waitForConnected(500):
                try:
                    QLocalServer.removeServer(self._SINGLE_INSTANCE_NAME)
                except Exception:
                    pass
                return False
            if path:
                sock.write((path + "\n").encode("utf-8"))
                sock.flush()
                sock.waitForBytesWritten(1000)
            sock.disconnectFromServer()
            return True
        except Exception:
            return False

    def take_over_as_primary(self) -> None:
        """転送失敗時 (プライマリ不在) に確保し直して通常起動する。"""
        self._acquire_primary()

    def _on_single_instance_message(self) -> None:
        try:
            assert self._local_server is not None
            sock = self._local_server.nextPendingConnection()
            if sock is None:
                return
            sock.waitForReadyRead(1000)
            data = bytes(sock.readAll().data()).decode("utf-8", errors="ignore")
            sock.disconnectFromServer()
            for line in data.splitlines():
                self.open_path_external(line.strip())
        except Exception:
            pass

    def open_path_external(self, path: str) -> None:
        """起動中プロセスへの外部オープン (関連付け/2重起動転送)。
        空のウィンドウがあればそこで開き、なければ新規ウィンドウで開く
        (macOSの QFileOpenEvent 処理と同方針)。"""
        if not path or not os.path.isfile(path):
            return
        target = self._windows[-1] if self._windows else None
        if target is not None and getattr(target, "_startup_done", False):
            if target.current_file_path is None and not target._content_text.strip():
                target._load_file(path)
                target.showNormal()
                target.raise_()
                target.activateWindow()
                return
        new_win = self.new_window()
        new_win._load_file(path)

    # ─── macOS Dock メニュー ─────────────────────
    def _setup_dock_menu(self):
        try:
            from AppKit import NSApplication, NSMenu, NSMenuItem
            import objc

            qt_app = self

            # NSObject サブクラスとして New Window アクションターゲットを作成
            class _DockTarget(objc.lookUpClass("NSObject")):
                def newMDWindow_(self, sender):
                    """Dock メニューから新規ウィンドウを開く"""
                    from PySide6.QtCore import QTimer as _QTimer
                    _QTimer.singleShot(0, qt_app.new_window)

            target = _DockTarget.alloc().init()

            def _build_and_set_dock_menu():
                try:
                    menu = NSMenu.alloc().init()
                    item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                        "New Window", "newMDWindow:", ""
                    )
                    item.setTarget_(target)
                    item.setEnabled_(True)
                    menu.addItem_(item)
                    NSApplication.sharedApplication().setDockMenu_(menu)
                    # GC 対策: 参照を保持
                    self._dock_menu_obj = menu
                    self._dock_target_obj = target
                except Exception:
                    pass

            from PySide6.QtCore import QTimer as _QTimer
            _QTimer.singleShot(1000, _build_and_set_dock_menu)
        except Exception:
            pass

    # ─── イベント処理 ────────────────────────────
    def event(self, e):
        if isinstance(e, QFileOpenEvent):
            path = e.file()
            if path and os.path.isfile(path):
                target = self._windows[-1] if self._windows else None
                if target is not None:
                    if target._startup_done:
                        # すでにコンテンツがあるウィンドウは新規ウィンドウで開く
                        if target.current_file_path is not None or target._content_text.strip():
                            new_win = self.new_window()
                            new_win._initial_file = path
                        else:
                            target._load_file(path)
                    else:
                        target._initial_file = path
                return True
        elif e.type() == QEvent.Type.ApplicationActivated:
            # Dock アイコンクリックなどでアプリが前面に — ウィンドウがなければ新規作成
            visible = any(w.isVisible() and not w.isMinimized() for w in self._windows)
            if not visible:
                if self._windows:
                    self._windows[-1].showNormal()
                    self._windows[-1].raise_()
                else:
                    self.new_window()
        return super().event(e)


# ════════════════════════════════════════════════
#  プラグインテーマローダー
# ════════════════════════════════════════════════
def load_plugin_themes() -> Dict[str, dict]:
    """~/.mdviewer/themes/*.json からカスタムテーマを読み込む"""
    themes: Dict[str, dict] = {}
    if not os.path.isdir(PLUGIN_DIR):
        try:
            os.makedirs(PLUGIN_DIR, exist_ok=True)
            _write_example_theme()
        except Exception:
            pass
        return themes
    for path in glob_mod.glob(os.path.join(PLUGIN_DIR, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name", os.path.splitext(os.path.basename(path))[0])
            palette = {k: data[k] for k in _PALETTE_REQUIRED_KEYS if k in data}
            if len(palette) == len(_PALETTE_REQUIRED_KEYS):
                themes[name] = palette
        except Exception:
            pass
    return themes


def _write_example_theme():
    """サンプルテーマファイルを書き出す"""
    sample = {
        "name": "Solarized Dark",
        "bg": "#002b36", "bg2": "#073642", "bg3": "#073642",
        "border": "#586e75", "text": "#839496", "text_dim": "#586e75",
        "accent": "#268bd2", "heading": "#93a1a1",
        "toolbar": "#002b36", "btn": "#073642", "btn_hover": "#586e75",
        "btn_active_bg": "#839496", "btn_active_fg": "#002b36",
        "select": "#073642", "code_fg": "#dc322f",
        "row_even": "#073642", "sep": "#586e75",
        "copy_btn_bg": "rgba(0,43,54,0.85)", "copy_btn_fg": "#93a1a1",
    }
    path = os.path.join(PLUGIN_DIR, "solarized_dark.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════
#  画像フェッチユーティリティ
# ════════════════════════════════════════════════
# 画像 URL を抽出。タイトル付き構文 ![alt](url "title") にも対応する。
_REMOTE_IMG_RE = re.compile(r'!\[[^\]]*\]\(\s*(https?://[^\s)]+)(?:\s+[^)]*)?\)')

def _extract_remote_image_urls(text: str) -> List[str]:
    return list(dict.fromkeys(_REMOTE_IMG_RE.findall(text)))

def _ip_is_safe(ip: str) -> bool:
    """IP アドレス文字列が外部公開アドレスかを判定する。"""
    ip = (ip or "").split("%", 1)[0]  # IPv6 ゾーン ID を除去
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast or addr.is_unspecified)


def _host_is_safe(host: str) -> bool:
    """ホスト名/IP が外部公開アドレスかを確認する (SSRF 対策・事前チェック)。

    localhost・社内 IP・リンクローカル・クラウド metadata endpoint 等の
    内部アドレスへの到達を拒否する。名前解決した全 IP を検査する。
    実際の接続時には _Pinned*Connection が接続先 IP を再検査するため、
    DNS リバインディング (TTL を悪用した二度目の解決すり替え) も防止される。
    """
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    if not infos:
        return False
    return all(_ip_is_safe(info[4][0]) for info in infos)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """接続直前に解決先 IP を検査し、公開アドレスにのみ接続する (DNS リバインディング対策)。"""
    def connect(self):
        infos = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)
        last_err = None
        for family, socktype, proto, _canon, sa in infos:
            if not _ip_is_safe(sa[0]):
                raise OSError(f"blocked non-public address: {sa[0]}")
            try:
                self.sock = socket.create_connection(
                    sa, self.timeout, self.source_address)
                if getattr(self, "_tunnel_host", None):
                    self._tunnel()
                return
            except OSError as e:
                last_err = e
        raise last_err or OSError("no address for host")


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS 版。SNI/証明書検証は元のホスト名で行い、接続先 IP のみ検査・固定する。"""
    def connect(self):
        infos = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)
        last_err = None
        for family, socktype, proto, _canon, sa in infos:
            if not _ip_is_safe(sa[0]):
                raise OSError(f"blocked non-public address: {sa[0]}")
            try:
                sock = socket.create_connection(
                    sa, self.timeout, self.source_address)
            except OSError as e:
                last_err = e
                continue
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
            return
        raise last_err or OSError("no address for host")


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_PinnedHTTPConnection, req)


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_PinnedHTTPSConnection, req)


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """リダイレクト先も http/https かつ外部アドレスのみ許可する。"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        pu = urlparse(newurl)
        if pu.scheme not in ("http", "https"):
            return None
        if not _host_is_safe(pu.hostname or ""):
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _safe_fetch_image(url: str, max_bytes: int = 10 * 1024 * 1024, timeout: int = 10):
    try:
        pu = urlparse(url)
        if pu.scheme not in ("http", "https"):
            return None
        if not _host_is_safe(pu.hostname or ""):
            return None
        req = urllib.request.Request(
            url, headers={"User-Agent": f"MDViewerPro/{APP_VERSION}"})
        # IP 固定接続ハンドラを使い、接続時にも解決先 IP を再検査する
        opener = urllib.request.build_opener(
            _PinnedHTTPHandler, _PinnedHTTPSHandler, _SafeRedirectHandler)
        with opener.open(req, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "")
            if not ctype.startswith("image/"):
                return None
            data = resp.read(max_bytes + 1)
            if len(data) > max_bytes:
                return None
            mime = ctype.split(";")[0].strip()
            return mime, data
    except Exception:
        return None


class ImageFetchWorker(QThread):
    """リモート画像をバックグラウンドスレッドで取得する (UI を固めない)。"""
    fetched = Signal(dict)  # {url: data_uri}

    MAX_IMAGES = 50
    MAX_TOTAL_BYTES = 40 * 1024 * 1024

    def __init__(self, urls: List[str], parent=None):
        super().__init__(parent)
        self._urls = list(urls)[: self.MAX_IMAGES]
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        results: Dict[str, str] = {}
        total = 0
        for url in self._urls:
            if self._cancel:
                break
            r = _safe_fetch_image(url)
            if not r:
                continue
            mime, data = r
            total += len(data)
            if total > self.MAX_TOTAL_BYTES:
                break
            b64 = base64.b64encode(data).decode("ascii")
            results[url] = f"data:{mime};base64,{b64}"
        if not self._cancel:
            self.fetched.emit(results)


# ════════════════════════════════════════════════
#  カスタム WebEnginePage — リンク制御
# ════════════════════════════════════════════════
class MDWebPage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "view"
        # Web コンテンツ側からの危険な操作を明示的に禁止する。
        try:
            s = self.settings()
            A = QWebEngineSettings.WebAttribute
            s.setAttribute(A.JavascriptCanOpenWindows, False)
            s.setAttribute(A.LocalContentCanAccessRemoteUrls, False)
            s.setAttribute(A.AllowRunningInsecureContent, False)
            s.setAttribute(A.JavascriptCanAccessClipboard, False)
            s.setAttribute(A.JavascriptCanPaste, False)
        except Exception:
            pass

    def set_mode(self, mode: str):
        self._mode = mode

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            if self._mode == "view":
                QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


# ════════════════════════════════════════════════
#  QWebChannel ブリッジ — MD編集モード用
# ════════════════════════════════════════════════
class ContentBridge(QObject):
    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self._callback = callback

    @Slot(str)
    def contentChanged(self, html_content: str):
        self._callback(html_content)


# ════════════════════════════════════════════════
#  QWebChannel ブリッジ — クリップボード用（全モード共通）
# ════════════════════════════════════════════════
class ClipboardBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    @Slot(str)
    def copyText(self, text: str):
        QApplication.clipboard().setText(text)


# ════════════════════════════════════════════════
#  HTML → Markdown 変換 (標準ライブラリのみ使用)
# ════════════════════════════════════════════════
class _HTML2MD(HTMLParser):
    class _Verbatim(str):
        pass

    def __init__(self, hard_breaks=True):
        super().__init__()
        self.hard_breaks = hard_breaks
        self._pre_start = 0
        self._code_marks = []
        self.parts: List[str] = []
        self._stack: List[str] = []
        self._in_pre = False
        self._pre_fence_open = False
        self._pending_href: Optional[str] = None
        self._a_depth = 0
        self._list_depth = 0
        self._ol_counters: List[int] = []
        self._in_thead = False
        self._th_count = 0
        self._skip_at: Optional[int] = None
        # 直前に <br> を改行として出力したか。markdown が nl2br で出力する
        # "<br />\n" の実改行を二重に数えないための目印 (handle_data で使う)。
        self._after_br = False
        # <blockquote> 開始時点の parts 長。閉じるときに中身を取り出して
        # 各行へ "> " を付け直すために使う。
        self._bq_marks: List[int] = []
        # <li> の行頭マーカー ("- " 等) を出した直後の parts 長。項目の中身が
        # まだ何も出ていないかの判定に使う (loose list の <p> 対策)。
        self._li_marks: List[int] = []
        # <p>/<div> 開始時点の parts 長。閉じるときに中身が空だったかを見る
        # (Enter で入れた空行を保存できるようにするため)。
        self._p_marks: List[int] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_d = dict(attrs)
        if tag not in {'br', 'hr', 'img', 'input', 'meta', 'link', 'wbr'}:
            self._stack.append(tag)
        cls = attrs_d.get('class', '') or ''
        cls_set = set(cls.split())
        if self._skip_at is None:
            # 数式・フロントマターは表示用に組版された HTML なので、
            # 中身ではなく原文 (data-tex / data-fm) から元の記法を復元する。
            if 'mdv-math' in cls_set:
                tex = attrs_d.get('data-tex', '') or ''
                if attrs_d.get('data-display', '0') == '1':
                    self.parts.append('\n\n$$' + tex + '$$\n\n')
                else:
                    self.parts.append('$' + tex + '$')
                self._skip_at = len(self._stack)
                return
            if 'mdv-fm' in cls_set:
                fm = attrs_d.get('data-fm', '') or ''
                self.parts.append('---\n' + fm + '\n---\n\n')
                self._skip_at = len(self._stack)
                return
            # \newpage 等の体裁コマンドは表示用に描画した空要素なので、
            # 中身ではなく data-tex の原文に戻す。
            if 'mdv-texcmd' in cls_set:
                cmd = attrs_d.get('data-tex', '') or ''
                if 'mdv-newpage' in cls_set or 'mdv-vspace' in cls_set:
                    self.parts.append('\n\n' + cmd + '\n\n')
                else:
                    self.parts.append(cmd)
                self._skip_at = len(self._stack)
                return
            # エディタが注入する制御要素(コピーボタン・テーブル操作ボタン・
            # 改ページ線・オーバーレイ目次)は出力しない
            if cls_set & {'mdv-copy-btn', 'mdv-table-ctrl', 'pg-brk', 'mdv-toc'}:
                self._skip_at = len(self._stack)
        if self._skip_at is not None:
            return
        self._after_br = False
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.parts.append('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'p':
            # loose list (項目間に空行がある箇条書き) では markdown が
            # <li><p>…</p></li> を出す。この <p> で改段落すると "- " だけの行と
            # 中身の行に割れてしまうため、項目の先頭にある <p> は境界を出さない。
            if not (self._li_marks and self._li_marks[-1] == len(self.parts)):
                self.parts.append('\n\n')
            self._p_marks.append(len(self.parts))
        elif tag == 'div':
            # contenteditable が Enter で生成する <div> は <p> と同じ段落境界として扱う。
            # 単一改行 ('\n') のみだと、往復編集のたびに段落間の空行(段落区切り)が
            # 失われ、保存後に再度開くと改行が詰まって表示される不具合の原因になっていた。
            self.parts.append('\n\n')
            self._p_marks.append(len(self.parts))
        elif tag == 'br':
            if any(t in self._stack for t in ('td', 'th')):
                self.parts.append('<br>')
            else:
                self.parts.append('\n' if self.hard_breaks else '  \n')
                self._after_br = True
        elif tag in ('strong', 'b'):
            self.parts.append('**')
        elif tag in ('em', 'i'):
            self.parts.append('*')
        elif tag in ('s', 'del', 'strike'):
            self.parts.append('~~')
        elif tag == 'code':
            if self._in_pre:
                # コードブロックの言語指定 (class="language-xxx") を保持する
                m = re.search(r'language-([\w+#.\-]+)', cls)
                lang = m.group(1) if m else ''
                self.parts.append('\n\n```' + lang + '\n')
                self._pre_fence_open = True
            else:
                self._code_marks.append(len(self.parts))
        elif tag == 'pre':
            self._pre_start = len(self.parts)
            self._in_pre = True
            self._pre_fence_open = False
            # フェンスは <code class="language-xxx"> を見てから開く (言語保持)。
            # <code> が無い <pre> は handle_data 側でフェンスを開く。
        elif tag == 'a':
            # 入れ子の <a> は最も外側だけをリンクとして扱う (Markdown はリンク入れ子不可)
            if self._a_depth == 0:
                self._pending_href = attrs_d.get('href', '')
                self.parts.append('[')
            self._a_depth += 1
        elif tag == 'img':
            src = attrs_d.get('src', '')
            alt = attrs_d.get('alt', '')
            self.parts.append(f'![{alt}]({src})')
        elif tag == 'ul':
            self._list_depth += 1
        elif tag == 'ol':
            self._list_depth += 1
            self._ol_counters.append(0)
        elif tag == 'li':
            # 入れ子の字下げは 4 文字。Python-Markdown は既定の tab_length=4 で、
            # 2 文字だと入れ子として読み直してもらえず往復で階層が潰れる。
            indent = '    ' * (self._list_depth - 1)
            parent = next((t for t in reversed(self._stack[:-1]) if t in ('ul', 'ol')), 'ul')
            if parent == 'ol' and self._ol_counters:
                self._ol_counters[-1] += 1
                self.parts.append(f'\n{indent}{self._ol_counters[-1]}. ')
            else:
                self.parts.append(f'\n{indent}- ')
            self._li_marks.append(len(self.parts))
        elif tag == 'blockquote':
            # 中身は一旦そのまま貯めておき、閉じるときに各行へ "> " を付ける
            # (handle_endtag 参照)。開始時に "> " を1つ置くだけだと 2 行目以降に
            # 引用符が付かず、往復のたびに引用が本文に崩れてしまう。
            self.parts.append('\n\n')
            self._bq_marks.append(len(self.parts))
        elif tag == 'hr':
            self.parts.append('\n\n---\n\n')
        elif tag == 'thead':
            self._in_thead = True
            self._th_count = 0
        elif tag == 'tr':
            self.parts.append('\n|')
        elif tag in ('th', 'td'):
            if self._in_thead and tag == 'th':
                self._th_count += 1
            self.parts.append(' ')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        if self._skip_at is not None:
            if len(self._stack) < self._skip_at:
                self._skip_at = None
            return
        # <br /> は HTMLParser が開始/終了の両方を呼ぶ (handle_startendtag)。
        # ここで目印を消すと直後の実改行を取り除けなくなるため除外する。
        if tag != 'br':
            self._after_br = False
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.parts.append('\n\n')
        elif tag == 'li':
            if self._li_marks:
                self._li_marks.pop()
        elif tag in ('p', 'div'):
            if self._p_marks:
                start = self._p_marks.pop()
                if ''.join(self.parts[start:]).strip() == '':
                    # 中身が空の段落 = 利用者が Enter で入れた空行。
                    # Markdown は連続した空行を無視するので、素の空行として
                    # 書き出すと保存後に消えてしまう。空行を確実に表現できる
                    # <br> だけの行にする (再度開いても同じ空段落に戻る)。
                    del self.parts[start:]
                    self.parts.append('<br>')
            # 箇条書きの項目内での段落終わりは 1 改行だけにする。空行を入れると
            # 次の項目との間に空行ができ、往復のたびに loose list 化していく。
            self.parts.append('\n' if 'li' in self._stack else '\n\n')
        elif tag in ('strong', 'b'):
            self.parts.append('**')
        elif tag in ('em', 'i'):
            self.parts.append('*')
        elif tag in ('s', 'del', 'strike'):
            self.parts.append('~~')
        elif tag == 'code' and not self._in_pre:
            if self._code_marks:
                start = self._code_marks.pop()
                code = ''.join(self.parts[start:])
                del self.parts[start:]
                fence = '`' * max(1, 1 + max(
                    (len(m.group()) for m in re.finditer(r'`+', code)), default=0))
                pad = ' ' if code.startswith(('`', ' ')) or code.endswith(('`', ' ')) else ''
                self.parts.append(self._Verbatim(fence + pad + code + pad + fence))
        elif tag == 'pre':
            self._in_pre = False
            if not self._pre_fence_open:
                self.parts.append('\n\n```\n')
            # コード末尾に既に改行があれば重複させない (往復での空行累積を防ぐ)
            if self.parts and self.parts[-1].endswith('\n'):
                self.parts.append('```\n\n')
            else:
                self.parts.append('\n```\n\n')
            self._pre_fence_open = False
        elif tag == 'a':
            self._a_depth = max(0, self._a_depth - 1)
            if self._a_depth == 0:
                href = self._pending_href or ''
                self.parts.append(f']({href})')
                self._pending_href = None
        elif tag in ('th', 'td'):
            self.parts.append(' |')
        elif tag == 'blockquote':
            if self._bq_marks:
                start = self._bq_marks.pop()
                inner = ''.join(self.parts[start:]).strip('\n')
                # 段落境界の \n\n が重なって 3 連以上になっていると、引用符
                # だけの行が余分に並んでしまうため先にまとめる。
                inner = re.sub(r'\n{3,}', '\n\n', inner)
                del self.parts[start:]
                if inner:
                    quoted = '\n'.join(
                        ('> ' + ln) if ln.strip() else '>'
                        for ln in inner.split('\n'))
                    self.parts.append(quoted)
                self.parts.append('\n\n')
        elif tag == 'thead':
            self._in_thead = False
            if self._th_count > 0:
                self.parts.append('\n|' + ' --- |' * self._th_count)
        elif tag in ('ul', 'ol'):
            self._list_depth = max(0, self._list_depth - 1)
            if tag == 'ol' and self._ol_counters:
                self._ol_counters.pop()
            # 入れ子のリストを閉じたところで改行を足すと、親の次の項目との間に
            # 空行ができてしまう。ブロックを閉じるのは一番外側のリストだけ。
            if self._list_depth == 0:
                self.parts.append('\n')

    def handle_data(self, data):
        if self._skip_at is not None:
            return
        # <pre> 内のデータはコードの一部なので、整形用の空白判定や
        # 改行除去の対象にせずそのまま保護する (コード内の連続空行や
        # 行頭インデントを保存時に残すため)。
        if self._in_pre:
            if not self._pre_fence_open:
                self.parts.append('\n\n```\n')
                self._pre_fence_open = True
            self.parts.append(self._Verbatim(data))
            return
        # markdown の nl2br は "<br />\n" を出力する。<br> で既に改行を1つ
        # 出しているので、直後の実改行はそのまま数えると空行 (段落区切り) に
        # なってしまう。1つだけ取り除いて「改行のまま」往復させる。
        if self._after_br:
            self._after_br = False
            if data.startswith('\n'):
                data = data[1:]
                if not data:
                    return
        else:
            self._after_br = False
        # テーブル要素内の空白のみのデータはMarkdown変換を壊すため無視する
        _TABLE_TAGS = {'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td'}
        if data.strip() == '' and any(t in self._stack for t in _TABLE_TAGS):
            return
        # <ul>/<ol> の直下 (項目と項目の間) にある改行・インデントは、markdown が
        # 整形のために出力しているだけの空白。そのまま拾うと項目間に空行が入り、
        # 往復のたびに loose list 化して最後は箇条書きが崩れてしまう。
        if (data.strip() == '' and self._stack
                and self._stack[-1] in ('ul', 'ol')):
            return
        # 同様に、<li> の直後・中身より前にある整形用の空白も落とす
        # (これを残すと loose list の <p> 判定がずれる)。
        if (data.strip() == '' and self._li_marks
                and self._li_marks[-1] == len(self.parts)):
            return
        # <li> の直下にある「改行を含む空白だけ」のテキストも落とす。入れ子
        # リストを閉じた後などに markdown が整形用に入れるもので、残すと親の
        # 次の項目との間に空行ができて loose list 化する。単語間の空白は改行を
        # 含まないので、この条件なら巻き込まない。
        if (data.strip() == '' and '\n' in data
                and self._stack and self._stack[-1] == 'li'):
            return
        self.parts.append(data)

    def get_result(self) -> str:
        chunks: List[str] = []
        buf: List[str] = []
        # 連続する空行の圧縮は段落境界 (\n\n) の正規化目的なので、コード
        # (フェンス内 / インラインコード) の中身には適用しない。
        # コード区間 (_Verbatim) の前後で部分文字列を分け、コードは素通しする。
        for part in self.parts:
            if isinstance(part, self._Verbatim):
                if buf:
                    chunks.append(''.join(buf))
                    buf = []
                chunks.append(part)
            else:
                buf.append(part)
        if buf:
            chunks.append(''.join(buf))
        text = ''.join(
            re.sub(r'(?<=\S)\n{3,}(?=\S)', '\n\n', c)
            if not isinstance(c, self._Verbatim) else c
            for c in chunks)
        return text.strip()


def _html_to_md(html: str, hard_breaks: bool = True) -> str:
    parser = _HTML2MD(hard_breaks=hard_breaks)
    parser.feed(html)
    return parser.get_result()


# ════════════════════════════════════════════════
#  HTML サニタイザ — Markdown 由来の未信頼 HTML を無害化
#  (標準ライブラリのみ。bleach 等の追加依存を増やさない)
# ════════════════════════════════════════════════
import html as _html_mod

# 許可するタグ
_SAN_ALLOWED_TAGS = {
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr', 'div', 'span',
    'pre', 'code', 'blockquote', 'a', 'img', 'strong', 'b', 'em', 'i', 'u',
    's', 'strike', 'del', 'ins', 'mark', 'sub', 'sup', 'small', 'kbd', 'samp',
    'var', 'abbr', 'cite', 'q', 'dfn', 'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption',
    'colgroup', 'col', 'input', 'figure', 'figcaption', 'details', 'summary',
    'wbr',
}
# 中身ごと完全に削除するタグ (スクリプト等)
_SAN_DROP_CONTENT = {
    'script', 'style', 'iframe', 'object', 'embed', 'template', 'noscript',
    'svg', 'math', 'frame', 'frameset', 'applet', 'form', 'textarea',
    'select', 'option', 'button', 'audio', 'video', 'source', 'track',
    'link', 'meta', 'base', 'title', 'head', 'canvas',
}
# 終了タグを出さない void 要素
_SAN_VOID = {'br', 'hr', 'img', 'input', 'col', 'wbr'}
# 属性の許可リスト
_SAN_GLOBAL_ATTRS = {'class', 'id', 'title', 'dir', 'lang', 'style', 'align'}
_SAN_TAG_ATTRS = {
    'a': {'href', 'target', 'rel', 'name'},
    'img': {'src', 'alt', 'width', 'height'},
    'input': {'type', 'checked', 'disabled'},
    'ol': {'start', 'type'},
    'td': {'colspan', 'rowspan', 'scope'},
    'th': {'colspan', 'rowspan', 'scope'},
    'col': {'span'},
    'colgroup': {'span'},
}
_SAN_HREF_OK_SCHEMES = ('http:', 'https:', 'mailto:', 'tel:')


def _san_safe_url(val: str, allow_data_image: bool = False) -> bool:
    v = (val or '').strip()
    if not v:
        return False
    low = v.lower().replace('\t', '').replace('\n', '').replace('\r', '')
    # 相対 URL・アンカー・絶対パスは許可
    if low.startswith('#') or low.startswith('/') or low.startswith('./') or low.startswith('../'):
        return True
    if low.startswith('data:'):
        return allow_data_image and low.startswith('data:image/')
    # スキームを含む場合は allowlist のみ
    if ':' in low.split('/', 1)[0]:
        return any(low.startswith(s) for s in _SAN_HREF_OK_SCHEMES)
    # スキームなし (相対パス)
    return True


class _HTMLSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: List[str] = []
        self._skip_depth = 0
        self._skip_tag: Optional[str] = None

    def _emit_tag(self, tag, attrs, self_close=False):
        parts = ['<', tag]
        allowed = _SAN_GLOBAL_ATTRS | _SAN_TAG_ATTRS.get(tag, set())
        for name, val in attrs:
            name = (name or '').lower()
            if name.startswith('on'):           # イベントハンドラは常に除去
                continue
            if name not in allowed:
                continue
            if name == 'style':
                sv = (val or '')
                low = sv.lower()
                # url()/expression()/javascript: を含む style は破棄
                if '(' in sv or 'javascript:' in low or 'expression' in low or '@import' in low:
                    continue
            if name == 'href' and not _san_safe_url(val):
                continue
            if name == 'src' and not _san_safe_url(val, allow_data_image=True):
                continue
            if val is None:
                parts.append(f' {name}')
            else:
                parts.append(f' {name}="{_html_mod.escape(val, quote=True)}"')
        parts.append(' />' if self_close else '>')
        self.out.append(''.join(parts))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self._skip_depth > 0:
            if tag == self._skip_tag:
                self._skip_depth += 1
            return
        if tag in _SAN_DROP_CONTENT:
            self._skip_tag = tag
            self._skip_depth = 1
            return
        if tag in _SAN_VOID:
            if tag in _SAN_ALLOWED_TAGS:
                self._emit_tag(tag, attrs, self_close=True)
            return
        if tag in _SAN_ALLOWED_TAGS:
            self._emit_tag(tag, attrs)
        # 許可外の非危険タグは unwrap (中身は残す)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self._skip_depth > 0:
            return
        if tag in _SAN_DROP_CONTENT:
            return
        if tag in _SAN_ALLOWED_TAGS:
            self._emit_tag(tag, attrs, self_close=True)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._skip_depth > 0:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if self._skip_depth == 0:
                    self._skip_tag = None
            return
        if tag in _SAN_VOID:
            return
        if tag in _SAN_ALLOWED_TAGS:
            self.out.append(f'</{tag}>')

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        self.out.append(_html_mod.escape(data, quote=False))

    def handle_comment(self, data):
        pass

    def get_result(self) -> str:
        return ''.join(self.out)


def _sanitize_html(html: str) -> str:
    s = _HTMLSanitizer()
    s.feed(html)
    s.close()
    return s.get_result()


# ════════════════════════════════════════════════
#  LaTeX 数式レンダラ (標準ライブラリのみ・完全オフライン)
#
#  KaTeX/MathJax のような外部 JS は使わない。数式は Python 側で
#  HTML + CSS に組版し、`.mdv-math` の中に埋め込む。
#  ・追加依存やネットワークアクセスが発生しない
#  ・PDF/HTML 書き出しにもそのまま乗る
#  ・サニタイザを通した後に差し込むため、生成 HTML が壊されない
#  対応範囲は実用的なサブセット (詳細は README / 設計ドキュメント)。
# ════════════════════════════════════════════════

# 数式退避用プレースホルダ。markdown / サニタイザ / html.escape の
# いずれも書き換えない私用領域 (Private Use Area) の文字を使う。
_MATH_PH_OPEN  = "\ue000"
_MATH_PH_CLOSE = "\ue001"
_MATH_PH_RE = re.compile(_MATH_PH_OPEN + r'(\d+)' + _MATH_PH_CLOSE)

# ─── 記号テーブル ──────────────────────────────
_TEX_SYMBOLS = {
    # ギリシャ文字 (小文字)
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ϵ',
    'varepsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ', 'vartheta': 'ϑ',
    'iota': 'ι', 'kappa': 'κ', 'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ',
    'omicron': 'ο', 'pi': 'π', 'varpi': 'ϖ', 'rho': 'ρ', 'varrho': 'ϱ',
    'sigma': 'σ', 'varsigma': 'ς', 'tau': 'τ', 'upsilon': 'υ', 'phi': 'ϕ',
    'varphi': 'φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω',
    # ギリシャ文字 (大文字)
    'Gamma': 'Γ', 'Delta': 'Δ', 'Theta': 'Θ', 'Lambda': 'Λ', 'Xi': 'Ξ',
    'Pi': 'Π', 'Sigma': 'Σ', 'Upsilon': 'Υ', 'Phi': 'Φ', 'Psi': 'Ψ',
    'Omega': 'Ω',
    # 二項演算子
    'times': '×', 'div': '÷', 'pm': '±', 'mp': '∓', 'cdot': '⋅', 'ast': '∗',
    'star': '⋆', 'circ': '∘', 'bullet': '∙', 'oplus': '⊕', 'ominus': '⊖',
    'otimes': '⊗', 'oslash': '⊘', 'odot': '⊙', 'dagger': '†', 'ddagger': '‡',
    'amalg': '⨿', 'uplus': '⊎', 'sqcup': '⊔', 'sqcap': '⊓', 'wr': '≀',
    'triangleleft': '◁', 'triangleright': '▷', 'bigtriangleup': '△',
    'bigtriangledown': '▽',
    # 関係子
    'leq': '≤', 'le': '≤', 'geq': '≥', 'ge': '≥', 'neq': '≠', 'ne': '≠',
    'equiv': '≡', 'approx': '≈', 'sim': '∼', 'simeq': '≃', 'cong': '≅',
    'propto': '∝', 'll': '≪', 'gg': '≫', 'prec': '≺', 'succ': '≻',
    'subset': '⊂', 'supset': '⊃', 'subseteq': '⊆', 'supseteq': '⊇',
    'sqsubseteq': '⊑', 'sqsupseteq': '⊒', 'in': '∈', 'notin': '∉', 'ni': '∋',
    'mid': '∣', 'nmid': '∤', 'perp': '⊥', 'parallel': '∥', 'models': '⊨',
    'vdash': '⊢', 'dashv': '⊣', 'doteq': '≐', 'asymp': '≍', 'bowtie': '⋈',
    'lneq': '⪇', 'gneq': '⪈', 'coloneqq': '≔',
    # 集合・論理
    'cup': '∪', 'cap': '∩', 'setminus': '∖', 'emptyset': '∅',
    'varnothing': '∅', 'forall': '∀', 'exists': '∃', 'nexists': '∄',
    'neg': '¬', 'lnot': '¬', 'land': '∧', 'wedge': '∧', 'lor': '∨',
    'vee': '∨', 'complement': '∁',
    # 矢印
    'to': '→', 'rightarrow': '→', 'leftarrow': '←', 'gets': '←',
    'leftrightarrow': '↔', 'Rightarrow': '⇒', 'Leftarrow': '⇐',
    'Leftrightarrow': '⇔', 'mapsto': '↦', 'implies': '⟹', 'impliedby': '⟸',
    'iff': '⟺', 'uparrow': '↑', 'downarrow': '↓', 'updownarrow': '↕',
    'longrightarrow': '⟶', 'longleftarrow': '⟵', 'hookrightarrow': '↪',
    'nearrow': '↗', 'searrow': '↘', 'swarrow': '↙', 'nwarrow': '↖',
    # その他
    'infty': '∞', 'partial': '∂', 'nabla': '∇', 'angle': '∠',
    'therefore': '∴', 'because': '∵', 'cdots': '⋯', 'ldots': '…',
    'dots': '…', 'dotsc': '…', 'vdots': '⋮', 'ddots': '⋱',
    'prime': '′', 'degree': '°', 'hbar': 'ℏ', 'ell': 'ℓ', 'Re': 'ℜ',
    'Im': 'ℑ', 'aleph': 'ℵ', 'wp': '℘', 'surd': '√', 'top': '⊤',
    'bot': '⊥', 'flat': '♭', 'natural': '♮', 'sharp': '♯', 'clubsuit': '♣',
    'diamondsuit': '♢', 'heartsuit': '♡', 'spadesuit': '♠',
    'checkmark': '✓', 'square': '□', 'blacksquare': '■', 'triangle': '△',
    'S': '§', 'P': '¶', 'copyright': '©', 'pounds': '£',
    'langle': '⟨', 'rangle': '⟩', 'lfloor': '⌊', 'rfloor': '⌋',
    'lceil': '⌈', 'rceil': '⌉', 'backslash': '\\',
}

# 上下に添字を積む大型演算子 (display 時)
_TEX_BIGOPS_STACK = {
    'sum': '∑', 'prod': '∏', 'coprod': '∐', 'bigcup': '⋃', 'bigcap': '⋂',
    'bigoplus': '⨁', 'bigotimes': '⨂', 'bigodot': '⨀', 'bigvee': '⋁',
    'bigwedge': '⋀', 'bigsqcup': '⨆', 'biguplus': '⨄',
}
# 添字を右に付ける大型演算子 (積分系)
_TEX_BIGOPS_SIDE = {
    'int': '∫', 'oint': '∮', 'iint': '∬', 'iiint': '∭', 'oiint': '∯',
}
# 立体で組む関数名 (添字は右)
_TEX_FUNCS = (
    'arccos', 'arcsin', 'arctan', 'arg', 'cos', 'cosh', 'cot', 'coth',
    'csc', 'deg', 'det', 'dim', 'exp', 'gcd', 'hom', 'ker', 'lg', 'ln',
    'log', 'sec', 'sin', 'sinh', 'tan', 'tanh', 'Pr',
)
# 立体で組み、display では上下に添字を積む関数名
_TEX_FUNCS_LIMITS = ('lim', 'limsup', 'liminf', 'max', 'min', 'sup', 'inf',
                     'argmax', 'argmin')

# 書体変更コマンド → (CSSクラス, 文字変換テーブル名)
_TEX_STYLES = {
    'mathrm': 'mdv-rm', 'textrm': 'mdv-rm', 'text': 'mdv-txt',
    'mathbf': 'mdv-bf', 'textbf': 'mdv-bf', 'boldsymbol': 'mdv-bf',
    'bm': 'mdv-bf', 'mathit': 'mdv-it', 'textit': 'mdv-it',
    'mathsf': 'mdv-sf', 'textsf': 'mdv-sf',
    'mathtt': 'mdv-tt', 'texttt': 'mdv-tt',
    'mathbb': 'mdv-bb', 'mathcal': 'mdv-cal', 'mathscr': 'mdv-cal',
    'mathfrak': 'mdv-frak', 'mathnormal': 'mdv-it',
}
# 黒板太字 / 花文字は Unicode の該当文字に置き換える (フォント非依存)
_TEX_BB = {
    'A': '𝔸', 'B': '𝔹', 'C': 'ℂ', 'D': '𝔻', 'E': '𝔼', 'F': '𝔽', 'G': '𝔾',
    'H': 'ℍ', 'I': '𝕀', 'J': '𝕁', 'K': '𝕂', 'L': '𝕃', 'M': '𝕄', 'N': 'ℕ',
    'O': '𝕆', 'P': 'ℙ', 'Q': 'ℚ', 'R': 'ℝ', 'S': '𝕊', 'T': '𝕋', 'U': '𝕌',
    'V': '𝕍', 'W': '𝕎', 'X': '𝕏', 'Y': '𝕐', 'Z': 'ℤ',
}
_TEX_CAL = {
    'A': '𝒜', 'B': 'ℬ', 'C': '𝒞', 'D': '𝒟', 'E': 'ℰ', 'F': 'ℱ', 'G': '𝒢',
    'H': 'ℋ', 'I': 'ℐ', 'J': '𝒥', 'K': '𝒦', 'L': 'ℒ', 'M': 'ℳ', 'N': '𝒩',
    'O': '𝒪', 'P': '𝒫', 'Q': '𝒬', 'R': 'ℛ', 'S': '𝒮', 'T': '𝒯', 'U': '𝒰',
    'V': '𝒱', 'W': '𝒲', 'X': '𝒳', 'Y': '𝒴', 'Z': '𝒵',
}
# アクセント → (記号, 上に載せるか)
_TEX_ACCENTS = {
    'hat': 'ˆ', 'widehat': 'ˆ', 'check': 'ˇ', 'tilde': '˜', 'widetilde': '˜',
    'acute': '´', 'grave': '`', 'dot': '˙', 'ddot': '¨', 'breve': '˘',
    'bar': '‾', 'vec': '→', 'overrightarrow': '→', 'mathring': '˚',
}
# 空白コマンド → em 単位の幅
_TEX_SPACES = {
    ',': 0.167, ':': 0.222, ';': 0.278, '!': -0.167, ' ': 0.333,
    'quad': 1.0, 'qquad': 2.0, 'thinspace': 0.167, 'enspace': 0.5,
    'hspace': 0.5,
}
# \left \right で使える区切り記号
_TEX_DELIMS = {
    '(': 'lparen', ')': 'rparen', '[': 'lbrack', ']': 'rbrack',
    '\\{': 'lbrace', '\\}': 'rbrace', '|': 'vert', '\\|': 'dvert',
    '.': 'none', '\\langle': 'langle', '\\rangle': 'rangle',
    '\\lfloor': 'lfloor', '\\rfloor': 'rfloor',
    '\\lceil': 'lceil', '\\rceil': 'rceil',
    '\\vert': 'vert', '\\Vert': 'dvert', '<': 'langle', '>': 'rangle',
}
_TEX_DELIM_GLYPH = {
    'lbrace': '{', 'rbrace': '}', 'langle': '⟨', 'rangle': '⟩',
    'lfloor': '⌊', 'rfloor': '⌋', 'lceil': '⌈', 'rceil': '⌉',
}
# 前後に空きを入れる二項演算子 / 関係子
_TEX_BINOPS = set('+−-*=<>±×÷≤≥≠≡≈∼≃≅∝≪≫⊂⊃⊆⊇∈∉∋∪∩∖∧∨→←↔⇒⇐⇔↦⟹⟸⟺≺≻⊥∣⊨⊢⋅∗⋆∘∙⊕⊖⊗⊘⊙')

_TEX_TOK_RE = re.compile(r'\\[A-Za-z]+|\\.|\s+|.', re.DOTALL)


def _tex_escape(s: str) -> str:
    return _html_mod.escape(s, quote=True)


class _TexNode:
    """組版済みの部分式。html と、区切り記号の伸縮に使う概算高さ (行数) を持つ。"""
    __slots__ = ("html", "h", "kind")

    def __init__(self, html: str, h: float = 1.0, kind: str = "ord"):
        self.html = html
        self.h = h
        self.kind = kind


class _TexRenderer:
    """LaTeX 数式の実用的サブセットを HTML + CSS に組版する。

    再帰下降でトークン列を解析する。未対応のコマンドは黙って読み飛ばさず、
    そのままの文字列として描画して「何が書かれていたか」が失われないようにする。
    """

    MAX_TOKENS = 20000   # 病的な入力で固まらないための上限

    def __init__(self, tex: str, display: bool):
        self.toks = _TEX_TOK_RE.findall(tex)[: self.MAX_TOKENS]
        self.i = 0
        self.display = display

    # ─── トークン操作 ─────────────────────────
    def _peek(self, skip_space=True):
        j = self.i
        while skip_space and j < len(self.toks) and self.toks[j].isspace():
            j += 1
        return self.toks[j] if j < len(self.toks) else None

    def _next(self, skip_space=True):
        while (skip_space and self.i < len(self.toks)
               and self.toks[self.i].isspace()):
            self.i += 1
        if self.i >= len(self.toks):
            return None
        t = self.toks[self.i]
        self.i += 1
        return t

    # 式の切れ目になるトークン。`]` は含めない ([0,1] のような通常の
    # 角括弧まで式の終わりと誤認してしまうため、\sqrt[n] の読み取り側
    # (read_optional) だけが個別に `]` を停止条件に加える。
    _STOPPERS = ('}', '\\right', '&', '\\\\', '\\end')

    # ─── 式 (ノードの並び) ────────────────────
    def parse_expr(self, stop=_STOPPERS) -> _TexNode:
        parts, h = [], 1.0
        while True:
            t = self._peek()
            if t is None or t in stop:
                break
            node = self.parse_atom()
            if node is None:
                break
            parts.append(node.html)
            h = max(h, node.h)
        return _TexNode(''.join(parts), h)

    # ─── 添字付きの原子 ──────────────────────
    def parse_atom(self):
        base = self.parse_node()
        if base is None:
            return None
        sup = sub = None
        while True:
            t = self._peek()
            if t == '^' and sup is None:
                self._next()
                sup = self.read_group()
            elif t == '_' and sub is None:
                self._next()
                sub = self.read_group()
            else:
                break
        if sup is None and sub is None:
            return base
        stack = (base.kind == 'bigop' and self.display) or base.kind == 'stack'
        if stack:
            rows = []
            if sup is not None:
                rows.append(f'<span class="mdv-lim-up">{sup.html}</span>')
            rows.append(f'<span class="mdv-lim-base">{base.html}</span>')
            if sub is not None:
                rows.append(f'<span class="mdv-lim-lo">{sub.html}</span>')
            html = '<span class="mdv-lim">' + ''.join(rows) + '</span>'
            return _TexNode(html, base.h + 1.2, 'ord')
        scripts = []
        if sup is not None:
            scripts.append(f'<span class="mdv-sup">{sup.html}</span>')
        if sub is not None:
            scripts.append(f'<span class="mdv-sub">{sub.html}</span>')
        if sup is not None and sub is not None:
            html = (base.html + '<span class="mdv-scripts">'
                    + ''.join(scripts) + '</span>')
        else:
            html = base.html + ''.join(scripts)
        return _TexNode(html, base.h + 0.45, 'ord')

    # ─── 引数 ({...} または 1 トークン) ────────
    def read_group(self) -> _TexNode:
        t = self._peek()
        if t is None:
            return _TexNode('')
        if t == '{':
            self._next()
            node = self.parse_expr()
            if self._peek() == '}':
                self._next()
            return node
        node = self.parse_node()
        return node if node is not None else _TexNode('')

    def read_optional(self):
        """\\sqrt[n]{x} の [n] のような省略可能引数を読む。"""
        if self._peek() != '[':
            return None
        self._next()
        node = self.parse_expr(stop=(']', '}', '\\end'))
        if self._peek() == ']':
            self._next()
        return node

    # ─── 単一ノード ─────────────────────────
    def parse_node(self):
        t = self._next()
        if t is None:
            return None
        if t.isspace():
            return _TexNode('')
        if t == '{':
            node = self.parse_expr()
            if self._peek() == '}':
                self._next()
            return node
        if t in ('}', '&', '\\\\'):
            return _TexNode('')
        if t.startswith('\\'):
            return self.parse_command(t)
        return self.parse_char(t)

    # ─── 通常の文字 ─────────────────────────
    def parse_char(self, c):
        if c.isalpha():
            # 変数はイタリック (LaTeX と同じ組版規則)
            return _TexNode(f'<i class="mdv-var">{_tex_escape(c)}</i>')
        if c == "'":
            return _TexNode('<span class="mdv-sup">′</span>')
        if c == '-':
            return _TexNode('<span class="mdv-bin">−</span>')
        if c in _TEX_BINOPS:
            return _TexNode(f'<span class="mdv-bin">{_tex_escape(c)}</span>')
        if c in ',;':
            return _TexNode(f'{_tex_escape(c)}<span class="mdv-sp-punct"></span>')
        if c in '()[]|':
            return _TexNode(f'<span class="mdv-open">{_tex_escape(c)}</span>')
        return _TexNode(_tex_escape(c))

    # ─── コマンド ───────────────────────────
    def parse_command(self, tok):
        name = tok[1:]

        # エスケープされた記号
        if name in ('{', '}', '$', '%', '&', '#', '_'):
            return _TexNode(_tex_escape(name))
        if tok == '\\\\':
            return _TexNode('<br>')

        # 空白
        if name in _TEX_SPACES:
            w = _TEX_SPACES[name]
            return _TexNode(f'<span style="display:inline-block;width:{w}em"></span>')

        # 分数
        if name in ('frac', 'dfrac', 'tfrac', 'cfrac'):
            num, den = self.read_group(), self.read_group()
            cls = 'mdv-frac mdv-frac-t' if name == 'tfrac' else 'mdv-frac'
            html = (f'<span class="{cls}">'
                    f'<span class="mdv-frac-n">{num.html}</span>'
                    f'<span class="mdv-frac-d">{den.html}</span></span>')
            return _TexNode(html, num.h + den.h + 0.2)
        if name == 'binom':
            top, bot = self.read_group(), self.read_group()
            inner = (f'<span class="mdv-frac mdv-frac-nb">'
                     f'<span class="mdv-frac-n">{top.html}</span>'
                     f'<span class="mdv-frac-d">{bot.html}</span></span>')
            return self._fence('lparen', 'rparen',
                               _TexNode(inner, top.h + bot.h + 0.2))
        # 根号
        if name == 'sqrt':
            idx = self.read_optional()
            body = self.read_group()
            h = body.h
            idx_html = (f'<span class="mdv-sqrt-idx">{idx.html}</span>'
                        if idx is not None else '')
            html = (f'<span class="mdv-sqrt">{idx_html}'
                    f'<span class="mdv-sqrt-sign" style="transform:scaleY({h:.2f})">'
                    f'√</span>'
                    f'<span class="mdv-sqrt-body">{body.html}</span></span>')
            return _TexNode(html, h + 0.2)
        # 上線 / 下線
        if name in ('overline', 'underline'):
            body = self.read_group()
            cls = 'mdv-over' if name == 'overline' else 'mdv-under'
            return _TexNode(f'<span class="{cls}">{body.html}</span>', body.h + 0.15)
        # アクセント
        if name in _TEX_ACCENTS:
            body = self.read_group()
            mark = _TEX_ACCENTS[name]
            cls = 'mdv-acc-wide' if name in ('vec', 'overrightarrow',
                                             'widehat', 'widetilde') else 'mdv-acc-m'
            html = (f'<span class="mdv-acc"><span class="{cls}">'
                    f'{_tex_escape(mark)}</span>{body.html}</span>')
            return _TexNode(html, body.h + 0.15)
        # 書体
        if name in _TEX_STYLES:
            cls = _TEX_STYLES[name]
            body = self.read_group_raw() if name in ('text', 'textrm', 'textbf',
                                                     'textit', 'textsf', 'texttt') \
                else self.read_group()
            inner = body.html
            if name in ('mathbb',):
                inner = self._map_letters(inner, _TEX_BB)
            elif name in ('mathcal', 'mathscr'):
                inner = self._map_letters(inner, _TEX_CAL)
            return _TexNode(f'<span class="{cls}">{inner}</span>', body.h)
        if name == 'operatorname':
            body = self.read_group_raw()
            return _TexNode(f'<span class="mdv-fn">{body.html}</span>')
        # 大型演算子
        if name in _TEX_BIGOPS_STACK:
            return _TexNode(
                f'<span class="mdv-bigop">{_TEX_BIGOPS_STACK[name]}</span>',
                1.4, 'bigop')
        if name in _TEX_BIGOPS_SIDE:
            return _TexNode(
                f'<span class="mdv-bigop mdv-bigop-int">'
                f'{_TEX_BIGOPS_SIDE[name]}</span>', 1.4, 'ord')
        # 関数名
        if name in _TEX_FUNCS:
            return _TexNode(f'<span class="mdv-fn">{name}</span>')
        if name in _TEX_FUNCS_LIMITS:
            return _TexNode(f'<span class="mdv-fn">{name}</span>', 1.0, 'bigop')
        # 区切り記号の伸縮
        if name == 'left':
            return self.parse_left()
        if name == 'right':
            return _TexNode('')
        if name in ('bigl', 'bigr', 'Bigl', 'Bigr', 'biggl', 'biggr'):
            nxt = self._next()
            return self._delim_node(nxt or '', 1.4)
        # 環境
        if name == 'begin':
            return self.parse_environment()
        if name == 'end':
            self.read_group_raw()
            return _TexNode('')
        # 表示に影響しない指示は無視
        if name in ('displaystyle', 'textstyle', 'scriptstyle', 'limits',
                    'nolimits', 'nonumber', 'notag', 'label', 'mathstrut',
                    'strut', 'phantom'):
            if name in ('label', 'phantom'):
                self.read_group_raw()
            return _TexNode('')
        # 記号テーブル
        if name in _TEX_SYMBOLS:
            sym = _TEX_SYMBOLS[name]
            cls = 'mdv-bin' if sym in _TEX_BINOPS else 'mdv-sym'
            return _TexNode(f'<span class="{cls}">{_tex_escape(sym)}</span>')
        # 未知のコマンドはそのまま見せる (黙って消さない)
        return _TexNode(f'<span class="mdv-unknown">{_tex_escape(tok)}</span>')

    def read_group_raw(self) -> _TexNode:
        """\\text{...} のように中身をそのままの文字列として扱う引数を読む。"""
        if self._peek() != '{':
            node = self.parse_node()
            return node if node is not None else _TexNode('')
        self._next(skip_space=False)
        # '{' の直後からは空白も意味を持つ
        while self.i < len(self.toks) and self.toks[self.i].isspace():
            self.i += 1
        buf, depth = [], 1
        while self.i < len(self.toks):
            t = self.toks[self.i]
            self.i += 1
            if t == '{':
                depth += 1
            elif t == '}':
                depth -= 1
                if depth == 0:
                    break
            buf.append(t)
        return _TexNode(_tex_escape(''.join(buf)))

    @staticmethod
    def _map_letters(html: str, table: dict) -> str:
        """タグを壊さないよう、タグの外側の A-Z だけを置き換える。"""
        out, in_tag = [], False
        for ch in html:
            if ch == '<':
                in_tag = True
            elif ch == '>':
                in_tag = False
            if not in_tag and ch in table:
                out.append(table[ch])
            else:
                out.append(ch)
        return ''.join(out)

    # ─── \left ... \right ───────────────────
    def parse_left(self):
        ldelim = self._next() or '.'
        inner = self.parse_expr(stop=('\\right', '\\end'))
        rdelim = '.'
        if self._peek() == '\\right':
            self._next()
            rdelim = self._next() or '.'
        return self._fence(_TEX_DELIMS.get(ldelim, 'none'),
                           _TEX_DELIMS.get(rdelim, 'none'), inner)

    def _delim_node(self, delim_tok: str, h: float):
        kind = _TEX_DELIMS.get(delim_tok, 'none')
        return _TexNode(self._delim_html(kind, h, left=True), h)

    @staticmethod
    def _delim_html(kind: str, h: float, left: bool) -> str:
        if kind == 'none':
            return ''
        # 括弧・角括弧・縦棒は CSS の枠線で描き、flex の stretch で自動的に伸びる
        if kind in ('lparen', 'rparen', 'lbrack', 'rbrack', 'vert', 'dvert'):
            return f'<span class="mdv-d mdv-d-{kind}"></span>'
        # 波括弧などのグリフは高さに応じて縦方向に拡大する
        glyph = _TEX_DELIM_GLYPH.get(kind, '')
        scale = max(1.0, min(4.0, h))
        return (f'<span class="mdv-d-glyph" style="transform:scaleY({scale:.2f})">'
                f'{_tex_escape(glyph)}</span>')

    def _fence(self, lkind, rkind, inner: _TexNode) -> _TexNode:
        html = ('<span class="mdv-fence">'
                + self._delim_html(lkind, inner.h, True)
                + f'<span class="mdv-fb">{inner.html}</span>'
                + self._delim_html(rkind, inner.h, False)
                + '</span>')
        return _TexNode(html, inner.h)

    # ─── \begin{...} ... \end{...} ──────────
    _ENV_FENCE = {
        'pmatrix': ('lparen', 'rparen'), 'bmatrix': ('lbrack', 'rbrack'),
        'Bmatrix': ('lbrace', 'rbrace'), 'vmatrix': ('vert', 'vert'),
        'Vmatrix': ('dvert', 'dvert'), 'matrix': ('none', 'none'),
        'smallmatrix': ('none', 'none'), 'array': ('none', 'none'),
        'cases': ('lbrace', 'none'),
        'aligned': ('none', 'none'), 'align': ('none', 'none'),
        'align*': ('none', 'none'), 'aligned*': ('none', 'none'),
        'gathered': ('none', 'none'), 'gather': ('none', 'none'),
        'split': ('none', 'none'),
    }

    def parse_environment(self):
        env_node = self.read_group_raw()
        env = env_node.html.strip()
        if env == 'array':
            self.read_group_raw()      # 列指定 (l/c/r) は読み捨てる
        if env not in self._ENV_FENCE:
            # 未知の環境は中身だけ描画する
            body = self.parse_expr(stop=('\\end',))
            if self._peek() == '\\end':
                self._next()
                self.read_group_raw()
            return body
        rows, row = [], []
        while True:
            cell = self.parse_expr(stop=('&', '\\\\', '\\end', '}'))
            row.append(cell)
            t = self._peek()
            if t == '&':
                self._next()
                continue
            if t == '\\\\':
                self._next()
                rows.append(row)
                row = []
                continue
            break
        if self._peek() == '\\end':
            self._next()
            self.read_group_raw()
        if row and (len(row) > 1 or row[0].html.strip()):
            rows.append(row)
        if not rows:
            rows = [[_TexNode('')]]

        ncol = max(len(r) for r in rows)
        cells, h = [], 0.0
        align_mode = env in ('cases', 'aligned', 'align', 'align*',
                             'aligned*', 'split')
        for r in rows:
            rh = max((c.h for c in r), default=1.0)
            h += rh
            for ci in range(ncol):
                c = r[ci] if ci < len(r) else _TexNode('')
                if align_mode:
                    just = 'right' if (ci == 0 and env != 'cases') else 'left'
                else:
                    just = 'center'
                cells.append(f'<span class="mdv-mc" style="justify-self:{just}">'
                             f'{c.html}</span>')
        gap = '.2em 1.1em' if env == 'cases' else '.25em .8em'
        grid = (f'<span class="mdv-mtx" style="grid-template-columns:'
                f'repeat({ncol},auto);gap:{gap}">' + ''.join(cells) + '</span>')
        lk, rk = self._ENV_FENCE[env]
        return self._fence(lk, rk, _TexNode(grid, max(1.0, h * 1.15)))


def _render_tex(tex: str, display: bool) -> str:
    """LaTeX 断片を HTML に変換する。失敗しても元の記述を必ず残す。"""
    try:
        node = _TexRenderer(tex, display).parse_expr(stop=())
        inner = node.html
        if not inner.strip():
            raise ValueError("empty")
    except Exception:
        inner = f'<span class="mdv-tex-raw">{_tex_escape(tex)}</span>'
    cls = "mdv-math mdv-math-display" if display else "mdv-math"
    # data-tex に原文を持たせ、MD編集モードの HTML→Markdown 逆変換で
    # 元の $...$ 記法を復元できるようにする。
    return (f'<span class="{cls}" data-tex="{_tex_escape(tex)}" '
            f'data-display="{"1" if display else "0"}" '
            f'contenteditable="false">{inner}</span>')


# ─── Markdown 変換前の数式退避 ──────────────────
def _split_code_fences(text: str):
    """(is_code, chunk) のリストに分割する。chunk は改行で連結すると原文に戻る。"""
    lines = text.split('\n')
    out, buf = [], []
    i, n = 0, len(lines)
    while i < n:
        m = re.match(r'^(`{3,}|~{3,})', lines[i])
        if m:
            marker = m.group(1)
            close_re = re.compile(r'^' + re.escape(marker) + r'[ \t]*$')
            j = i + 1
            while j < n and not close_re.match(lines[j]):
                j += 1
            if j < n:
                if buf:
                    out.append((False, '\n'.join(buf)))
                    buf = []
                out.append((True, '\n'.join(lines[i:j + 1])))
                i = j + 1
                continue
        buf.append(lines[i])
        i += 1
    if buf:
        out.append((False, '\n'.join(buf)))
    return out


def _find_inline_math_close(s: str, start: int):
    """`$` で開いたインライン数式の閉じ位置を返す。見つからなければ -1。

    `$5 と $10` のような通貨表記を数式と誤認しないよう、TeX 互換の規則
    (開き `$` の直後と閉じ `$` の直前が空白でないこと) を課す。
    空行やコードスパンをまたぐものも数式とはみなさない。"""
    n = len(s)
    if start + 1 >= n or s[start + 1].isspace() or s[start + 1] == '$':
        return -1
    j = start + 1
    while j < n:
        c = s[j]
        if c == '\\':          # \$ 等のエスケープは 2 文字まとめて読み飛ばす
            j += 2
            continue
        if c == '`':
            # コードスパンの中の `$` を閉じ記号として拾わない。
            # 例: 「金額の $10 です。`$x$` も…」の `$x$` に食い付いて
            #     間の日本語まで数式として組んでしまうのを防ぐ。
            return -1
        if c == '\n' and j + 1 < n and s[j + 1] == '\n':
            return -1          # 空行をまたぐものは数式とみなさない
        if c == '$':
            return -1 if s[j - 1].isspace() else j
        j += 1
    return -1


def _extract_math(text: str):
    """Markdown 変換前に数式をプレースホルダへ退避する。

    コードフェンス内・インラインコード内の `$` は数式として扱わない。
    戻り値: (置換後テキスト, [(display, tex), ...])"""
    store: List[tuple] = []

    def ph(display, tex):
        if not tex.strip():
            return None
        store.append((display, tex))
        return f"{_MATH_PH_OPEN}{len(store) - 1}{_MATH_PH_CLOSE}"

    def scan(s: str) -> str:
        out, i, n = [], 0, len(s)
        while i < n:
            c = s[i]
            if c == '\\' and i + 1 < n:
                nxt = s[i + 1]
                if nxt in '([':
                    end = '\\)' if nxt == '(' else '\\]'
                    j = s.find(end, i + 2)
                    if j != -1:
                        p = ph(nxt == '[', s[i + 2:j])
                        if p:
                            out.append(p)
                            i = j + 2
                            continue
                out.append(s[i:i + 2])
                i += 2
                continue
            if c == '`':
                k = i
                while k < n and s[k] == '`':
                    k += 1
                run = s[i:k]
                j = s.find(run, k)
                if j != -1:
                    out.append(s[i:j + len(run)])
                    i = j + len(run)
                    continue
                out.append(run)
                i = k
                continue
            if c == '$':
                if s.startswith('$$', i):
                    j = s.find('$$', i + 2)
                    if j != -1:
                        p = ph(True, s[i + 2:j])
                        if p:
                            out.append(p)
                            i = j + 2
                            continue
                else:
                    j = _find_inline_math_close(s, i)
                    if j != -1:
                        p = ph(False, s[i + 1:j])
                        if p:
                            out.append(p)
                            i = j + 1
                            continue
            out.append(c)
            i += 1
        return ''.join(out)

    chunks = [c if is_code else scan(c) for is_code, c in _split_code_fences(text)]
    return '\n'.join(chunks), store


def _restore_math(html: str, store: List[tuple]) -> str:
    """サニタイズ後の HTML にレンダリング済みの数式を差し込む。"""
    if not store:
        return html

    def sub(m):
        idx = int(m.group(1))
        if idx >= len(store):
            return ''
        display, tex = store[idx]
        return _render_tex(tex, display)

    return _MATH_PH_RE.sub(sub, html)


# ════════════════════════════════════════════════
#  LaTeX の体裁コマンド (\newpage 等)
#
#  \newpage のような「文書の体裁を指示する」コマンドは、数式と違って
#  組版する中身を持たない。文字列のまま表示されてしまうと本文の邪魔に
#  なるため、指示として解釈して表示に反映し、コマンド自体は見せない。
#    ・改ページ … PDF書き出しでは実際にページを分け、A4/B5表示では
#                 次のページの先頭まで送る (通常表示では何も見せない)
#    ・改行/空き … 指示どおりの改行・縦の空きを入れる
#    ・体裁のみ … 表示には反映できないので隠すだけ
#  対応していないコマンドは書き換えずそのまま残す (数式と同じ方針)。
# ════════════════════════════════════════════════
_TEXCMD_PH_OPEN  = "\ue002"
_TEXCMD_PH_CLOSE = "\ue003"
_TEXCMD_PH_RE = re.compile(_TEXCMD_PH_OPEN + r'(\d+)' + _TEXCMD_PH_CLOSE)

# コマンド名 → (種別, 既定値)
#   "page"  改ページ / "br" 改行 / "par" 段落 / "space" 縦の空き / "none" 隠すだけ
_TEX_LAYOUT_CMDS = {
    'newpage':         ('page',  None),
    'pagebreak':       ('page',  None),
    'clearpage':       ('page',  None),
    'cleardoublepage': ('page',  None),
    'newline':         ('br',    None),
    'linebreak':       ('br',    None),
    'par':             ('par',   None),
    'bigskip':         ('space', '12pt'),
    'medskip':         ('space', '6pt'),
    'smallskip':       ('space', '3pt'),
    'noindent':        ('none',  None),
    'indent':          ('none',  None),
    'centering':       ('none',  None),
    'raggedright':     ('none',  None),
    'raggedleft':      ('none',  None),
    'hfill':           ('none',  None),
}

# 長いものから並べる (\clearpage より \cleardoublepage を先に当てる)。
# 直後が英字のときは別コマンド (\par と \parbox 等) なので採らない。
_TEX_LAYOUT_RE = re.compile(
    r'\\(vspace\*?|'
    + '|'.join(sorted(_TEX_LAYOUT_CMDS, key=len, reverse=True))
    + r')(?![a-zA-Z])'
    r'(?:\[[^\]\n]*\])?'      # \pagebreak[4] のような任意引数
    r'(?:\{([^}\n]*)\})?'     # \vspace{1cm} の長さ
)

# CSS がそのまま解釈できる長さの単位
_TEX_CSS_UNITS = ('cm', 'mm', 'in', 'pt', 'pc', 'px', 'em', 'ex', 'rem')


def _tex_length_to_css(arg: str) -> str:
    """LaTeX の長さ指定を CSS の長さに直す。解釈できなければ 0。"""
    s = (arg or '').strip()
    m = re.match(r'^(-?\d*\.?\d+)\s*\\?([a-zA-Z]*)$', s)
    if not m:
        return '0'
    num, unit = m.group(1), m.group(2).lower()
    if unit in _TEX_CSS_UNITS:
        return f'{num}{unit}'
    # \baselineskip / \parskip などは行送りを基準にした概算に置き換える
    if unit in ('baselineskip', 'lineskip'):
        try:
            return f'{float(num) * 1.5:g}em'
        except ValueError:
            return '0'
    if unit == '':
        return '0'
    return '0'


def _extract_tex_layout(text: str):
    """Markdown 変換前に体裁コマンドをプレースホルダへ退避する。

    コードフェンス内・インラインコード内は対象外 (説明として書かれた
    `\\newpage` を勝手に消してしまわないため)。
    戻り値: (置換後テキスト, [原文, ...])"""
    store: List[str] = []

    def scan(s: str) -> str:
        out, i, n = [], 0, len(s)
        while i < n:
            c = s[i]
            if c == '`':
                # インラインコードはそのまま通す
                k = i
                while k < n and s[k] == '`':
                    k += 1
                run = s[i:k]
                j = s.find(run, k)
                if j != -1:
                    out.append(s[i:j + len(run)])
                    i = j + len(run)
                    continue
                out.append(run)
                i = k
                continue
            if c == '\\':
                m = _TEX_LAYOUT_RE.match(s, i)
                if m:
                    store.append(m.group(0))
                    out.append(f"{_TEXCMD_PH_OPEN}{len(store) - 1}{_TEXCMD_PH_CLOSE}")
                    i = m.end()
                    continue
                # 体裁コマンド以外のエスケープは 2 文字まとめて素通しする
                out.append(s[i:i + 2])
                i += 2
                continue
            out.append(c)
            i += 1
        return ''.join(out)

    chunks = [c if is_code else scan(c) for is_code, c in _split_code_fences(text)]
    return '\n'.join(chunks), store


def _render_tex_layout(raw: str) -> str:
    """体裁コマンド 1 つ分の HTML を作る。

    原文を data-tex に持たせ、MD編集モードの HTML→Markdown 逆変換で
    元のコマンドに戻せるようにする (数式と同じ仕組み)。"""
    m = _TEX_LAYOUT_RE.match(raw)
    if not m:
        return _tex_escape(raw)
    name, arg = m.group(1), m.group(2)
    esc = _tex_escape(raw)
    attrs = f'data-tex="{esc}" contenteditable="false"'
    if name.startswith('vspace'):
        return (f'<div class="mdv-texcmd mdv-vspace" {attrs} '
                f'style="height:{_tex_length_to_css(arg)}"></div>')
    kind, val = _TEX_LAYOUT_CMDS.get(name, ('none', None))
    if kind == 'page':
        return f'<div class="mdv-texcmd mdv-newpage" {attrs}></div>'
    if kind == 'space':
        return (f'<div class="mdv-texcmd mdv-vspace" {attrs} '
                f'style="height:{val}"></div>')
    # <br> は必ず自己終了形で書く。HTMLParser は void 要素を知らないため、
    # <br> のままだと開始タグだけが積まれてタグの対応が崩れ、
    # HTML→Markdown 変換で後続の本文が丸ごと失われる。
    if kind == 'br':
        return f'<span class="mdv-texcmd mdv-texbr" {attrs}><br/></span>'
    if kind == 'par':
        return f'<span class="mdv-texcmd mdv-texbr" {attrs}><br/><br/></span>'
    return f'<span class="mdv-texcmd" {attrs}></span>'


# 行に体裁コマンドだけが書かれていた場合、markdown はそれを <p> で包む。
# ブロック要素を <p> の中に置くと HTML として不正なので包みを外す。
_TEXCMD_UNWRAP_RE = re.compile(
    r'<p>\s*((?:<div class="mdv-texcmd[^>]*></div>\s*)+)</p>')


def _restore_tex_layout(html: str, store: List[str]) -> str:
    """サニタイズ後の HTML に体裁コマンドの描画結果を差し込む。"""
    if not store:
        return html

    def sub(m):
        idx = int(m.group(1))
        if idx >= len(store):
            return ''
        return _render_tex_layout(store[idx])

    return _TEXCMD_UNWRAP_RE.sub(r'\1', _TEXCMD_PH_RE.sub(sub, html))


# ════════════════════════════════════════════════
#  Mermaid ダイアグラム
#
#  グラフレイアウトを要するため数式のような自作Pythonレンダラは非現実的。
#  完全オフラインでバンドルした mermaid.js (assets/mermaid.min.js, MIT
#  license, ネットワークアクセスなし) を QWebEngineView 上で実行して描画
#  する。プレビュー限定 (MD編集モードでは他言語同様、生フェンスのまま
#  編集できるよう抽出しない)。数式/体裁コマンドと同じ
#  「変換前にプレースホルダへ退避→sanitize後に復元」パターンを使う。
# ════════════════════════════════════════════════
_MERMAID_PH_OPEN  = ""
_MERMAID_PH_CLOSE = ""
_MERMAID_PH_RE = re.compile(_MERMAID_PH_OPEN + r'(\d+)' + _MERMAID_PH_CLOSE)
_MERMAID_FENCE_RE = re.compile(r'^(`{3,}|~{3,})[ \t]*mermaid[ \t]*$', re.IGNORECASE)


def _extract_mermaid(text: str):
    """Markdown 変換前に ```mermaid フェンスをプレースホルダへ退避する。

    他のコードフェンス・本文は変更しない。
    戻り値: (置換後テキスト, [ダイアグラム原文, ...])"""
    store: List[str] = []
    chunks = []
    for is_code, chunk in _split_code_fences(text):
        if is_code:
            lines = chunk.split('\n')
            if len(lines) >= 2 and _MERMAID_FENCE_RE.match(lines[0]):
                store.append('\n'.join(lines[1:-1]))
                chunks.append(f"\n\n{_MERMAID_PH_OPEN}{len(store) - 1}{_MERMAID_PH_CLOSE}\n\n")
                continue
        chunks.append(chunk)
    return '\n'.join(chunks), store


def _restore_mermaid(html: str, store: List[str]) -> str:
    """サニタイズ後の HTML にダイアグラム描画用の <pre class="mermaid"> を差し込む。"""
    if not store:
        return html

    def sub(m):
        idx = int(m.group(1))
        if idx >= len(store):
            return ''
        return f'<pre class="mermaid">{_html_mod.escape(store[idx])}</pre>'

    return _MERMAID_PH_RE.sub(sub, html)


_MERMAID_JS_CACHE: Optional[str] = None


def _mermaid_js_source() -> str:
    """バンドル済み assets/mermaid.min.js を読み込む (初回のみ・以後メモ化)。"""
    global _MERMAID_JS_CACHE
    if _MERMAID_JS_CACHE is not None:
        return _MERMAID_JS_CACHE
    candidates = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(script_dir, "assets", "mermaid.min.js"))
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "assets", "mermaid.min.js"))
    exe_dir = os.path.dirname(sys.executable)
    candidates.append(os.path.join(exe_dir, "..", "Resources", "assets", "mermaid.min.js"))
    for path in candidates:
        path = os.path.normpath(path)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _MERMAID_JS_CACHE = f.read()
                    return _MERMAID_JS_CACHE
            except Exception:
                pass
    _MERMAID_JS_CACHE = ""
    return _MERMAID_JS_CACHE


def _hex_is_dark(hex_color: str) -> bool:
    """パレット色 (#rrggbb) が暗色かどうかを知覚輝度で判定する。"""
    h = (hex_color or "").lstrip("#")
    if len(h) != 6:
        return True
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return True
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128


# ════════════════════════════════════════════════
#  YAML — フロントマター解析 (最小サブセット / 依存追加なし)
# ════════════════════════════════════════════════
def _split_front_matter(text: str):
    """先頭の YAML フロントマターを切り出す。

    戻り値: (front_matter本文 or None, 残りの本文, 本文の開始行番号)
    `---` で始まり `---` / `...` で閉じるブロックのみを対象とする。"""
    if not text.startswith('---'):
        return None, text, 0
    lines = text.split('\n')
    if lines[0].strip() != '---':
        return None, text, 0
    for i in range(1, len(lines)):
        if lines[i].strip() in ('---', '...'):
            fm = '\n'.join(lines[1:i])
            body = '\n'.join(lines[i + 1:])
            return fm, body, i + 1
    return None, text, 0


def _parse_simple_yaml(text: str):
    """フロントマター表示用の最小 YAML パーサ。

    マッピング / ネスト / 並び / 引用文字列 / コメントを扱う。
    アンカーやフロースタイル等の高度な記法は文字列として素通しする
    (表示専用のため、厳密な YAML 準拠より壊れないことを優先する)。"""
    def scalar(v: str):
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            return v[1:-1]
        return v

    def skip_blank(lines, i):
        while i < len(lines) and (not lines[i].strip()
                                  or lines[i].strip().startswith('#')):
            i += 1
        return i

    def indent_of(line):
        return len(line) - len(line.lstrip(' '))

    def parse_child(lines, i, parent_indent, allow_same_indent_list):
        """入れ子ブロックを読む。子の字下げ幅は決め打ちせず、実際の
        次行から判定する (YAML は 2 スペース以外の字下げも許すため)。
        マッピングの値が並びの場合、YAML では親と同じ字下げで
        `- item` を並べる書き方も正しいので、その場合だけ同じ深さを許す。"""
        j = skip_blank(lines, i)
        if j >= len(lines):
            return '', j
        ni = indent_of(lines[j])
        if ni > parent_indent:
            return parse_block(lines, j, ni)
        if (allow_same_indent_list and ni == parent_indent
                and lines[j].strip().startswith('- ')):
            return parse_block(lines, j, ni)
        return '', i

    def parse_block(lines, start, indent):
        """(値, 次に読む行) を返す。"""
        items, mapping = [], {}
        i = start
        while i < len(lines):
            raw = lines[i]
            if not raw.strip() or raw.strip().startswith('#'):
                i += 1
                continue
            cur = indent_of(raw)
            if cur < indent:
                break
            if cur > indent:
                i += 1
                continue
            s = raw.strip()
            if s.startswith('- '):
                val = s[2:].strip()
                m = re.match(r'^([^:#]+):\s*(.*)$', val)
                if m and not val.startswith(('"', "'")):
                    sub = {m.group(1).strip(): scalar(m.group(2))}
                    nested, i = parse_child(lines, i + 1, cur, False)
                    if isinstance(nested, dict):
                        sub.update(nested)
                    items.append(sub)
                    continue
                items.append(scalar(val))
                i += 1
                continue
            m = re.match(r'^([^:#]+):\s*(.*)$', s)
            if not m:
                items.append(scalar(s))
                i += 1
                continue
            key, val = m.group(1).strip(), m.group(2).strip()
            if val and not val.startswith('#'):
                mapping[key] = scalar(val)
                i += 1
                continue
            child, i = parse_child(lines, i + 1, cur, True)
            mapping[key] = child if child not in ({}, []) else ''
        if items and not mapping:
            return items, i
        return mapping, i

    lines = [ln.rstrip() for ln in text.split('\n')]
    try:
        value, _ = parse_block(lines, 0, 0)
    except Exception:
        return {}
    return value


def _front_matter_html(fm_text: str, title: str) -> str:
    """フロントマターを畳めるメタ情報パネルとして描画する。"""
    data = _parse_simple_yaml(fm_text)

    def render(v, depth=0):
        if isinstance(v, dict):
            rows = []
            for k, sv in v.items():
                rows.append(
                    f'<div class="mdv-fm-row" style="padding-left:{depth * 14}px">'
                    f'<span class="mdv-fm-key">{_tex_escape(str(k))}</span>'
                    f'<span class="mdv-fm-val">{render(sv, depth + 1)}</span>'
                    f'</div>')
            return ''.join(rows)
        if isinstance(v, list):
            if all(not isinstance(x, (dict, list)) for x in v):
                return ' '.join(
                    f'<span class="mdv-fm-tag">{_tex_escape(str(x))}</span>'
                    for x in v)
            return ''.join(f'<div>{render(x, depth)}</div>' for x in v)
        return _tex_escape(str(v))

    body = render(data) if data else (
        f'<pre class="mdv-fm-raw">{_tex_escape(fm_text)}</pre>')
    # data-fm に原文を持たせ、MD編集モードの HTML→Markdown 逆変換で
    # 元の `---` ブロックをそのまま復元できるようにする。
    return (f'<div class="mdv-fm" data-fm="{_tex_escape(fm_text)}" '
            f'contenteditable="false"><div class="mdv-fm-title">'
            f'{_tex_escape(title)}</div>{body}</div>')


# ════════════════════════════════════════════════
#  SafeWebLoader
# ════════════════════════════════════════════════
class SafeWebLoader:
    _MAX_BYTES = 1_900_000

    def __init__(self, web: QWebEngineView, dark: bool = True):
        self._web = web
        self._tmpdir = tempfile.mkdtemp(prefix="mdvp_")
        self._counter = 0
        bg = QColor("#000000" if dark else "#f0f0f0")
        self._web.page().setBackgroundColor(bg)

    def set_background(self, color: str):
        try:
            self._web.page().setBackgroundColor(QColor(color))
        except Exception:
            pass

    def load_html(self, html: str, base_path: Optional[str] = None):
        encoded = html.encode("utf-8")
        if len(encoded) > self._MAX_BYTES:
            self._counter += 1
            path = os.path.join(self._tmpdir, f"page_{self._counter}.html")
            # 大きいHTMLはbase tagを注入してローカルリソースを解決
            if base_path:
                base_url = QUrl.fromLocalFile(base_path).toString()
                insert = f'<base href="{base_url}">'
                html = html.replace("<head>", f"<head>{insert}", 1)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)
                self._web.load(QUrl.fromLocalFile(path))
            except Exception:
                self._web.setHtml(encoded[:self._MAX_BYTES].decode("utf-8", errors="replace"), QUrl())
        else:
            base_url = QUrl.fromLocalFile(base_path) if base_path else QUrl()
            self._web.setHtml(html, base_url)

    def cleanup(self):
        if os.path.isdir(self._tmpdir):
            shutil.rmtree(self._tmpdir, ignore_errors=True)


# ════════════════════════════════════════════════
#  余白ダイアログ
# ════════════════════════════════════════════════
class MarginDialog(QDialog):
    def __init__(self, parent, margins, t, title=None):
        super().__init__(parent)
        self.setWindowTitle(title or t["margin_title"])
        self.setFixedWidth(300)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._spins = {}
        for i, (k, lbl) in enumerate(zip(
            ["top", "right", "bottom", "left"],
            [t["margin_top"], t["margin_right"], t["margin_bottom"], t["margin_left"]]
        )):
            sb = QSpinBox()
            sb.setRange(0, 100)
            sb.setValue(margins[i])
            sb.setSuffix(" mm")
            form.addRow(f"{lbl}:", sb)
            self._spins[k] = sb
        root.addLayout(form)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def get_margins(self):
        return tuple(self._spins[k].value() for k in ["top", "right", "bottom", "left"])


# ════════════════════════════════════════════════
#  詳細設定ダイアログ
# ════════════════════════════════════════════════
class SettingsDialog(QDialog):
    def __init__(self, parent, font_family, lang, current_theme, bold_mode, t,
                 plugin_themes: Dict[str, dict], hard_breaks: bool = True):
        super().__init__(parent)
        self.setWindowTitle(t["settings_title"])
        self.setMinimumWidth(380)
        root = QVBoxLayout(self)
        root.setSpacing(14)

        # フォント (推奨 / 追加したフォント / システムフォント)
        self._t = t
        fg = QGroupBox(t["font_label"])
        fl = QVBoxLayout(fg)
        self._font_cb = QComboBox()
        self._font_cb.setMaxVisibleItems(20)
        fl.addWidget(self._font_cb)

        btn_row = QHBoxLayout()
        self._font_add_btn = QPushButton(t.get("font_add", "Add Font..."))
        self._font_add_btn.clicked.connect(self._on_add_font)
        btn_row.addWidget(self._font_add_btn)
        self._font_del_btn = QPushButton(t.get("font_remove", "Remove"))
        self._font_del_btn.clicked.connect(self._on_remove_font)
        btn_row.addWidget(self._font_del_btn)
        fl.addLayout(btn_row)

        hint = QLabel(t.get("font_hint", ""))
        hint.setWordWrap(True)
        hint.setObjectName("fontHint")
        fl.addWidget(hint)
        root.addWidget(fg)

        self._font_cb.currentIndexChanged.connect(self._on_font_changed)
        self._populate_fonts(font_family)

        # 言語
        lg = QGroupBox(t.get("lang_label", "Language"))
        ll = QVBoxLayout(lg)
        self._lang_cb = QComboBox()
        self._lang_cb.addItems(list(LANGS.keys()))
        cur = [k for k, v in LANGS.items() if v == lang]
        if cur:
            self._lang_cb.setCurrentText(cur[0])
        ll.addWidget(self._lang_cb)
        root.addWidget(lg)

        # テーマ（ダーク・ライト＋プラグイン）
        tg = QGroupBox(t["theme_label"])
        tl = QVBoxLayout(tg)
        self._theme_cb = QComboBox()
        self._theme_items = [t["dark"], t["light"]] + list(plugin_themes.keys())
        self._theme_cb.addItems(self._theme_items)
        # current_theme: "dark" / "light" / plugin name
        if current_theme == "dark":
            self._theme_cb.setCurrentIndex(0)
        elif current_theme == "light":
            self._theme_cb.setCurrentIndex(1)
        else:
            idx = self._theme_items.index(current_theme) if current_theme in self._theme_items else 0
            self._theme_cb.setCurrentIndex(idx)
        tl.addWidget(self._theme_cb)
        root.addWidget(tg)

        # プラグインフォルダを開く
        pg = QGroupBox(t["plugin_label"])
        pl = QVBoxLayout(pg)
        open_dir_btn = QPushButton(t["plugin_dir_btn"])
        open_dir_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(PLUGIN_DIR)))
        pl.addWidget(open_dir_btn)
        root.addWidget(pg)

        # 太字強調
        bg2 = QGroupBox(t["bold_label"])
        bl = QVBoxLayout(bg2)
        self._bold_cb = QCheckBox(t["bold_label"])
        self._bold_cb.setChecked(bold_mode)
        bl.addWidget(self._bold_cb)
        root.addWidget(bg2)

        # 改行の扱い (既定はオン = 書いたとおりに改行する)
        hg = QGroupBox(t.get("hard_breaks_label", "Line Breaks"))
        hl = QVBoxLayout(hg)
        self._hard_breaks_cb = QCheckBox(
            t.get("hard_breaks_cb", "Render a single newline as a line break"))
        self._hard_breaks_cb.setChecked(hard_breaks)
        hl.addWidget(self._hard_breaks_cb)
        hint = QLabel(t.get("hard_breaks_hint", ""))
        hint.setWordWrap(True)
        # 明暗どちらのテーマでも読める中間色にする
        hint.setStyleSheet("color: rgba(140,140,140,1); font-size: 11px;")
        hl.addWidget(hint)
        root.addWidget(hg)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

        self._t_dark  = t["dark"]
        self._t_light = t["light"]
        self._plugin_themes = plugin_themes

    # ─── フォント一覧 ─────────────────────────
    def _add_header(self, label):
        """選択できない見出し行をコンボボックスに追加する。"""
        self._font_cb.addItem(f"── {label} ──", None)
        idx = self._font_cb.count() - 1
        item = self._font_cb.model().item(idx)
        if item is not None:
            item.setEnabled(False)

    def _populate_fonts(self, current: str):
        t = self._t
        cb = self._font_cb
        cb.blockSignals(True)
        cb.clear()
        try:
            installed = sorted(set(QFontDatabase.families()))
        except Exception:
            installed = []

        self._add_header(t.get("font_recommended", "Recommended"))
        for label, candidates in RECOMMENDED_FONTS:
            fam = next((c for c in candidates if c in installed), None)
            if fam:
                cb.addItem(label if label == fam else f"{label}  ({fam})", fam)
            else:
                cb.addItem(label + t.get("font_not_installed", ""), None)
                item = cb.model().item(cb.count() - 1)
                if item is not None:
                    item.setEnabled(False)

        if _USER_FONTS:
            self._add_header(t.get("font_user", "Added"))
            for fam in sorted(_USER_FONTS):
                cb.addItem(fam, fam)

        self._add_header(t.get("font_system", "System"))
        for fam in installed:
            cb.addItem(fam, fam)

        # 現在のフォントを選択 (推奨欄よりシステム欄の実名を優先しない)
        target = -1
        for i in range(cb.count()):
            if cb.itemData(i) == current:
                target = i
                break
        cb.setCurrentIndex(target if target >= 0 else 0)
        cb.blockSignals(False)
        self._on_font_changed()

    def _current_font_family(self):
        return self._font_cb.itemData(self._font_cb.currentIndex())

    def _on_font_changed(self, _idx=None):
        fam = self._current_font_family()
        self._font_del_btn.setEnabled(bool(fam) and fam in _USER_FONTS)

    def _on_add_font(self):
        t = self._t
        path, _ = QFileDialog.getOpenFileName(
            self, t.get("font_add_title", "Choose a font file"),
            os.path.expanduser("~"),
            "Fonts (*.ttf *.otf *.ttc *.otc);;All Files (*)")
        if not path:
            return
        fams = add_user_font(path)
        if not fams:
            QMessageBox.warning(self, t.get("font_add_error", "Error"),
                                t.get("font_add_invalid", ""))
            return
        self._populate_fonts(fams[0])

    def _on_remove_font(self):
        t = self._t
        fam = self._current_font_family()
        if not fam or fam not in _USER_FONTS:
            return
        if QMessageBox.question(
                self, t.get("font_remove_title", "Remove Font"),
                t.get("font_remove_msg", "Remove \"{name}\"?").format(name=fam),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        remove_user_font(fam)
        self._populate_fonts(_DEFAULT_FONT_FAMILY)

    def get_result(self):
        font = self._current_font_family() or _DEFAULT_FONT_FAMILY
        lang = LANGS[self._lang_cb.currentText()]
        bold = self._bold_cb.isChecked()
        idx  = self._theme_cb.currentIndex()
        if idx == 0:
            theme = "dark"
        elif idx == 1:
            theme = "light"
        else:
            theme = self._theme_items[idx]
        return font, lang, theme, bold, self._hard_breaks_cb.isChecked()


# ════════════════════════════════════════════════
#  スタートアップダイアログ（新規作成ボタン付き）
# ════════════════════════════════════════════════
class StartupDialog(QDialog):
    ACTION_OPEN  = "open"
    ACTION_NEW   = "new"
    ACTION_GUIDE = "guide"

    def __init__(self, parent, t, current_lang: str = "ja"):
        super().__init__(parent)
        self.setWindowTitle(t["startup_title"])
        self.setMinimumWidth(360)
        self.action: Optional[str] = None
        self.selected_lang: str = current_lang

        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(32, 28, 32, 28)

        self._title_lbl = QLabel(t["startup_title"])
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tf = self._title_lbl.font()
        tf.setPointSize(20)
        tf.setBold(True)
        self._title_lbl.setFont(tf)
        root.addWidget(self._title_lbl)

        self._hint_lbl = QLabel(t["startup_hint"])
        self._hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._hint_lbl)

        root.addSpacing(8)

        self._open_btn = QPushButton(t["startup_open"])
        self._open_btn.setFixedHeight(44)
        self._open_btn.clicked.connect(self._on_open)
        root.addWidget(self._open_btn)

        self._new_btn = QPushButton(t["startup_new"])
        self._new_btn.setFixedHeight(44)
        self._new_btn.clicked.connect(self._on_new)
        root.addWidget(self._new_btn)

        # Language selector row
        lang_row = QWidget()
        lang_lay = QHBoxLayout(lang_row)
        lang_lay.setContentsMargins(0, 0, 0, 0)
        self._lang_lbl = QLabel(t.get("startup_language", "Language"))
        lang_lay.addWidget(self._lang_lbl)
        self._lang_cb = QComboBox()
        self._lang_cb.addItems(list(LANGS.keys()))
        cur_key = [k for k, v in LANGS.items() if v == current_lang]
        if cur_key:
            self._lang_cb.setCurrentText(cur_key[0])
        self._lang_cb.currentIndexChanged.connect(self._on_lang_changed)
        lang_lay.addWidget(self._lang_cb)
        root.addWidget(lang_row)

        self._guide_btn = QPushButton(t.get("startup_guide", "説明を開く"))
        self._guide_btn.setFixedHeight(44)
        self._guide_btn.clicked.connect(self._on_guide)
        root.addWidget(self._guide_btn)

    def _on_lang_changed(self, _idx: int):
        lang = LANGS.get(self._lang_cb.currentText(), "ja")
        self.selected_lang = lang
        t = I18N[lang]
        self.setWindowTitle(t["startup_title"])
        self._title_lbl.setText(t["startup_title"])
        self._hint_lbl.setText(t["startup_hint"])
        self._open_btn.setText(t["startup_open"])
        self._new_btn.setText(t["startup_new"])
        self._guide_btn.setText(t.get("startup_guide", "説明を開く"))
        self._lang_lbl.setText(t.get("startup_language", "Language"))

    def _current_selected_lang(self) -> str:
        return LANGS.get(self._lang_cb.currentText(), "ja")

    def _on_open(self):
        self.selected_lang = self._current_selected_lang()
        self.action = self.ACTION_OPEN
        self.accept()

    def _on_new(self):
        self.selected_lang = self._current_selected_lang()
        self.action = self.ACTION_NEW
        self.accept()

    def _on_guide(self):
        self.selected_lang = self._current_selected_lang()
        self.action = self.ACTION_GUIDE
        self.accept()

    # ─── × ボタン / Escape → 新規作成として扱う ──────────
    def reject(self):
        if self.action is None:
            self.selected_lang = self._current_selected_lang()
            self.action = self.ACTION_NEW
        super().accept()

    # ─── ダイアログ以外（本体ウィンドウ等）がアクティブになった → 新規作成 ──
    def changeEvent(self, event):
        super().changeEvent(event)
        if (event.type() == QEvent.Type.ActivationChange
                and not self.isActiveWindow()
                and self.isVisible()
                and self.action is None):
            # ComboBox ポップアップ等による一時的な非アクティブ化を除外するため
            # 200ms 待ってから判定する
            QTimer.singleShot(200, self._check_deactivation)

    def _check_deactivation(self):
        """非アクティブ化が持続していれば（本体クリック等）新規作成として処理"""
        if not self.isVisible() or self.action is not None:
            return
        # 自分自身または子ポップアップがアクティブな場合は何もしない
        if self.isActiveWindow():
            return
        active = QApplication.activeWindow()
        if active is self or (active is not None and active.parent() is self):
            return
        self.selected_lang = self._current_selected_lang()
        self.action = self.ACTION_NEW
        self.accept()


# ════════════════════════════════════════════════
#  PDF書き出し設定ダイアログ
# ════════════════════════════════════════════════
class PdfExportDialog(QDialog):
    def __init__(self, parent, page_mode, a4_margins, b5_margins, t,
                 embed_images=True, current_theme="dark", plugin_themes=None):
        super().__init__(parent)
        self.setWindowTitle(t.get("pdf_settings_title", "PDF書き出し設定"))
        self.setMinimumWidth(320)
        self._a4_margins = a4_margins
        self._b5_margins = b5_margins
        if plugin_themes is None:
            plugin_themes = {}
        root = QVBoxLayout(self)
        root.setSpacing(12)

        pg = QGroupBox(t.get("pdf_page_size", "用紙サイズ"))
        pl = QVBoxLayout(pg)
        self._page_cb = QComboBox()
        self._page_cb.addItems(["A4", "B5"])
        if page_mode == "b5":
            self._page_cb.setCurrentText("B5")
        pl.addWidget(self._page_cb)
        root.addWidget(pg)

        og = QGroupBox(t.get("pdf_orientation", "方向"))
        ol = QVBoxLayout(og)
        self._orient_cb = QComboBox()
        self._orient_cb.addItems([
            t.get("pdf_portrait", "縦向き"),
            t.get("pdf_landscape", "横向き"),
        ])
        ol.addWidget(self._orient_cb)
        root.addWidget(og)

        mg = QGroupBox(t.get("margin_title", "余白設定 (mm)"))
        ml = QFormLayout()
        curr = b5_margins if page_mode == "b5" else a4_margins
        self._margin_spins: Dict[str, QSpinBox] = {}
        for i, (k, lbl) in enumerate(zip(
            ["top", "right", "bottom", "left"],
            [t.get("margin_top","上"), t.get("margin_right","右"),
             t.get("margin_bottom","下"), t.get("margin_left","左")]
        )):
            sb = QSpinBox()
            sb.setRange(0, 100)
            sb.setValue(curr[i])
            sb.setSuffix(" mm")
            ml.addRow(f"{lbl}:", sb)
            self._margin_spins[k] = sb
        mg.setLayout(ml)
        root.addWidget(mg)

        ig = QGroupBox(t.get("pdf_embed_images", "画像を含める"))
        il = QVBoxLayout(ig)
        self._embed_images_cb = QCheckBox(t.get("pdf_embed_images_label", "PDFに画像を埋め込む"))
        self._embed_images_cb.setChecked(embed_images)
        il.addWidget(self._embed_images_cb)
        root.addWidget(ig)

        # スタイルモード選択 (ダーク / ライト / プラグイン)
        sg = QGroupBox(t.get("pdf_style_mode", "スタイルモード"))
        sl = QVBoxLayout(sg)
        self._style_cb = QComboBox()
        _dark_lbl  = t.get("dark",  "ダークモード")
        _light_lbl = t.get("light", "ライトモード")
        self._style_items = [("dark", _dark_lbl), ("light", _light_lbl)]
        for name in plugin_themes.keys():
            self._style_items.append((name, name))
        self._style_cb.addItems([lbl for _, lbl in self._style_items])
        cur_idx = next((i for i, (k, _) in enumerate(self._style_items) if k == current_theme), 0)
        self._style_cb.setCurrentIndex(cur_idx)
        sl.addWidget(self._style_cb)
        root.addWidget(sg)

        self._page_cb.currentTextChanged.connect(self._on_page_changed)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def _on_page_changed(self, text):
        m = self._b5_margins if text == "B5" else self._a4_margins
        for i, k in enumerate(["top", "right", "bottom", "left"]):
            self._margin_spins[k].setValue(m[i])

    def get_settings(self):
        page = self._page_cb.currentText()
        landscape = self._orient_cb.currentIndex() == 1
        margins = tuple(self._margin_spins[k].value() for k in ["top", "right", "bottom", "left"])
        embed_images = self._embed_images_cb.isChecked()
        pdf_theme = self._style_items[self._style_cb.currentIndex()][0]
        return page, landscape, margins, embed_images, pdf_theme


# ════════════════════════════════════════════════
#  PianoBtn
# ════════════════════════════════════════════════
class PianoBtn(QPushButton):
    """ツールバーのボタン。

    ウィンドウ幅が狭くなってラベルがボタン幅に収まらなくなったとき、
    そのボタンだけフォントを 1px ずつ縮めて枠内に収める。ボタンごとに
    文字数が違うため、ウィンドウ幅による一律のサイズ変更だけでは
    「戻る」は余るのに「PDF書き出し」は溢れる、という状態になってしまう。"""

    MIN_FONT_PX = 8

    def __init__(self, label="", parent=None):
        super().__init__(label, parent)
        sp = self.sizePolicy()
        sp.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        sp.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        self.setSizePolicy(sp)
        self.setProperty("active", False)
        self._base_px = 0        # ウィンドウ幅から決まる基準サイズ (px)
        self._pad_px = 12        # 左右パディング + 枠線の合計 (px)
        self._min_hint_w = 24    # レイアウトに申告する最小幅 (px)
        self._applied_px = -1

    def set_fit_metrics(self, base_px, pad_px, min_hint_w):
        self._base_px = int(base_px)
        self._pad_px = int(pad_px)
        self._min_hint_w = int(min_hint_w)
        self._applied_px = -1
        self.updateGeometry()
        self._fit_text()

    def setText(self, text):
        super().setText(text)
        self.updateGeometry()
        self._fit_text()

    def _hint_width(self, px):
        """基準フォントサイズでのラベル幅。実際に適用中のフォントではなく
        基準サイズで計算するのが要点で、こうしないと
        「文字を縮める → サイズヒントが縮む → 幅が変わる → また縮める」
        という発振が起きてレイアウトが収束しない。"""
        f = QFont(self.font())
        f.setBold(True)
        f.setPixelSize(px)
        return QFontMetrics(f).horizontalAdvance(self.text()) + self._pad_px

    def sizeHint(self):
        s = super().sizeHint()
        if self._base_px <= 0:
            return s
        return QSize(self._hint_width(self._base_px), s.height())

    def minimumSizeHint(self):
        # QPushButton の既定の最小幅はラベル全体が入る幅。そのままだと
        # ボタンが縮まず、ツールバーがウィンドウ幅を超えて文字が切れる。
        # 文字はこちら側で縮めるので、レイアウトには小さい最小幅を返す。
        s = super().minimumSizeHint()
        base_w = (self._hint_width(self._base_px)
                  if self._base_px > 0 else s.width())
        return QSize(min(base_w, self._min_hint_w), s.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_text()

    def _fit_text(self):
        if self._base_px <= 0:
            return
        text = self.text()
        avail = self.width() - self._pad_px
        if not text or avail <= 0:
            return
        f = QFont(self.font())
        f.setBold(True)          # スタイルシート側で bold 指定のため合わせる
        px = self._base_px
        while px > self.MIN_FONT_PX:
            f.setPixelSize(px)
            if QFontMetrics(f).horizontalAdvance(text) <= avail:
                break
            px -= 1
        if px == self._applied_px:
            return
        self._applied_px = px
        # 親 (QMainWindow) の "QPushButton#mainBtn{font-size:...}" を上書きするには
        # 同じセレクタで自ウィジェットに指定する。Qt はウィジェット自身の
        # スタイルシートを継承したものより優先する。
        name = self.objectName() or "mainBtn"
        self.setStyleSheet(f"QPushButton#{name}{{font-size:{px}px;}}")

    def set_active(self, on):
        if self.property("active") != on:
            self.setProperty("active", on)
            self.style().unpolish(self)
            self.style().polish(self)


# ════════════════════════════════════════════════
#  メインウィンドウ
# ════════════════════════════════════════════════
class MDViewerPro(QMainWindow):
    window_closed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MD Viewer Pro")
        _icon_path = _bundled_file("assets", "favicon.ico")
        if _icon_path:
            self.setWindowIcon(QIcon(_icon_path))
        self.resize(1280, 900)
        self.setMinimumSize(480, 360)

        # 設定を読み込む
        _s = load_settings()

        self.current_file_path: Optional[str] = None
        self.is_modified       = False
        self.current_theme     = _s["theme"]
        self.scale_idx         = _s["scale_idx"]
        self.page_mode         = "free"
        self.edit_mode         = "view"
        self.a4_margins        = (20, 20, 20, 20)
        self.b5_margins        = (15, 15, 15, 15)
        self.lang              = _s["lang"]
        self.ui_font_family    = _s["font_family"]
        self.bold_mode         = _s["bold_mode"]
        # 改行をそのまま改行として描画するか (詳細設定で切り替え)
        self.hard_breaks       = _s["hard_breaks"]
        self._last_pdf_dir     = _s["last_pdf_dir"]
        self._content_text     = ""
        self._palette          = DARK_PALETTE
        self._plugin_themes: Dict[str, dict] = {}
        self._image_cache: Dict[str, str] = {}
        self._readonly_file    = False
        # MD編集モードの内容取り込み中フラグ (入れ子のイベントループの再入防止)
        self._md_flushing      = False
        # "md" | "yaml" — YAML ファイルは全文を YAML として構文強調表示する
        self.doc_kind          = "md"
        self._saved_scroll_y   = 0
        self._restore_scroll_pending = False
        # モード切替時に持ち回るスクロールアンカー (行番号, 行内の位置の割合)
        self._pending_anchor: Optional[tuple] = None
        self._initial_file: Optional[str] = None
        self._show_toc         = bool(_s.get("show_toc", True))
        self._pdf_embed_images = _s.get("pdf_embed_images", True)
        # PDF書き出し用オフスクリーンViewの参照 (書き出し中のみ保持し、
        # 終了時に破棄する。表示側 _preview_web には一切触らない)。
        self._pdf_view = None
        self._pdf_loader = None
        self._pdf_layout_ref = None
        self._pdf_state = "done"

        # UI スケール管理 (空文字で初回強制適用)
        self._last_ui_scale_cat = ""

        # プラグインテーマ読み込み
        self._plugin_themes = load_plugin_themes()

        self._apply_app_font()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._flush_preview)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(80)
        self._resize_timer.timeout.connect(self._apply_responsive_style)

        self._startup_done = False

        self._build_ui()

        # ウィンドウジオメトリ復元 (前回終了時のサイズ・位置)
        if _s.get("window_geometry"):
            try:
                geom = QByteArray.fromBase64(_s["window_geometry"].encode("ascii"))
                self.restoreGeometry(geom)
            except Exception:
                pass

        # ツールバー等は即座にスタイル適用し、ウィンドウをすぐ表示できるようにする。
        # 重い QWebEngineView の生成は show() 後 (次のイベントループ) まで遅延させる
        # (旧実装は __init__ 内で同期生成しておりウィンドウ表示自体が遅延していた)。
        self._apply_theme(refresh=False)
        QTimer.singleShot(0, self._finish_deferred_init)

        # MDApplication の管理リストへの登録は MDApplication.new_window() で行う

    def _apply_app_font(self):
        """UI 全体の既定フォントを設定に合わせる。"""
        af = QFont(self.ui_font_family if self.ui_font_family else _DEFAULT_FONT_FAMILY)
        af.setPointSize(15)
        af.setBold(True)
        QApplication.setFont(af)

    def _finish_deferred_init(self):
        """QWebEngineView の生成・WebChannel 配線・スタートアップダイアログ表示。
        ウィンドウが画面に表示された直後の最初のイベントループで実行される。"""
        self._md_page = MDWebPage()
        self._preview_web = QWebEngineView()
        self._preview_web.setPage(self._md_page)
        self._preview_web.loadFinished.connect(self._on_preview_loaded)
        idx = self._splitter.indexOf(self._preview_placeholder)
        self._splitter.replaceWidget(idx, self._preview_web)
        self._preview_placeholder.deleteLater()
        self._preview_placeholder = None

        self._loader = SafeWebLoader(self._preview_web, dark=True)

        self._bridge = ContentBridge(self._on_md_content_changed, self)
        self._clipboard_bridge = ClipboardBridge(self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("bridge", self._bridge)
        self._channel.registerObject("clipboard", self._clipboard_bridge)
        self._md_page.setWebChannel(self._channel)

        self._apply_theme(refresh=False)

        # スタートアップダイアログを即座に表示しつつ WebEngine をバックグラウンドで初期化
        # (旧実装: loadFinished 待ち → 最大 4 秒の遅延があった)
        self._startup_done = True
        self._loader.load_html("<html><body></body></html>")  # WebEngine ウォームアップ
        QTimer.singleShot(0, self._startup_open)

    def _on_preview_loaded(self, ok):
        """プレビュー再読み込み完了ごとに呼ばれる (TXT編集時の行ハイライト再適用用)。"""
        if not ok or self.edit_mode != "txt":
            return
        line = self._md_editor.textCursor().blockNumber()
        self._preview_web.page().runJavaScript(
            f"window._mdvHighlightLine && window._mdvHighlightLine({line});"
        )

    def _t(self, key):
        # 空文字列が正規の翻訳値であるケース (page_label_prefix/suffix 等) を
        # "未翻訳" と誤判定しないよう、真偽値ではなく None で判定する。
        v = I18N[self.lang].get(key)
        if v is not None:
            return v
        v = I18N["ja"].get(key)
        if v is not None:
            return v
        return key

    # ════════════════════════════════════════════
    #  UI 構築
    # ════════════════════════════════════════════
    def _build_ui(self):
        root_w = QWidget()
        self.setCentralWidget(root_w)
        root_l = QVBoxLayout(root_w)
        root_l.setContentsMargins(0, 0, 0, 0)
        root_l.setSpacing(0)

        self._main_tb = self._make_main_tb()
        root_l.addWidget(self._main_tb)

        self._fmt_container = QWidget()
        self._fmt_container.setFixedHeight(FMT_H)
        self._fmt_container_layout = QVBoxLayout(self._fmt_container)
        self._fmt_container_layout.setContentsMargins(0, 0, 0, 0)
        self._fmt_container_layout.setSpacing(0)
        self._fmt_tb = self._make_fmt_tb()
        self._fmt_tb.setFixedHeight(FMT_H)
        self._fmt_container_layout.addWidget(self._fmt_tb)
        self._fmt_container.setVisible(False)
        root_l.addWidget(self._fmt_container)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        root_l.addWidget(self._splitter)

        # 見出し(TOC)パネル: MD編集/TXT編集モードでのみ引き出せる
        self._toc_panel = self._make_toc_panel()
        self._toc_panel.setVisible(False)
        self._splitter.addWidget(self._toc_panel)

        self._editor_stack = QStackedWidget()
        self._view_placeholder = QWidget()
        self._editor_stack.addWidget(self._view_placeholder)
        self._md_editor = QPlainTextEdit()
        self._md_editor.textChanged.connect(self._on_editor_changed)
        self._md_editor.cursorPositionChanged.connect(self._on_txt_cursor_moved)
        self._editor_stack.addWidget(self._md_editor)
        # 閲覧・MD編集モードでは中身が空のため隠す (非表示ウィジェットは
        # QSplitter が自動的に幅0に畳み、ハンドルも操作不能になる →
        # 空白パネルをドラッグで引き出せてしまう不具合を防ぐ)
        self._editor_stack.setVisible(False)
        self._splitter.addWidget(self._editor_stack)

        # QWebEngineView は生成コストが高くウィンドウ表示を遅らせるため、
        # ここでは軽量なプレースホルダーを差し込み、show() 後に差し替える
        # (_finish_deferred_init 参照)。
        self._preview_placeholder = QWidget()
        self._splitter.addWidget(self._preview_placeholder)

        self._splitter.setSizes([0, 0, 1])
        self._build_menu()

    def _make_toc_panel(self):
        panel = QWidget()
        panel.setObjectName("tocPanel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._toc_title_lbl = QLabel(self._t("toc_title"))
        self._toc_title_lbl.setObjectName("tocTitle")
        lay.addWidget(self._toc_title_lbl)
        self._toc_list = QListWidget()
        self._toc_list.setObjectName("tocList")
        self._toc_list.itemClicked.connect(self._on_toc_item_clicked)
        lay.addWidget(self._toc_list)
        return panel

    # ─── メインツールバー ─────────────────────────
    def _make_main_tb(self):
        tb = QWidget()
        tb.setObjectName("mainTB")
        tb.setFixedHeight(TB_H)
        lay = QHBoxLayout(tb)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        def sep():
            w = QWidget()
            w.setFixedWidth(1)
            w.setObjectName("vSep")
            lay.addWidget(w)

        self._back_btn = PianoBtn(self._t("back"))
        self._back_btn.setObjectName("mainBtn")
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self._go_back)
        lay.addWidget(self._back_btn)
        sep()

        self._mode_btns = {}
        for key, tk in [("view","view"), ("md","md_edit"), ("txt","txt_edit")]:
            b = PianoBtn(self._t(tk))
            b.setObjectName("mainBtn")
            b.clicked.connect(lambda _, k=key: self._set_mode(k))
            lay.addWidget(b)
            self._mode_btns[key] = b
        sep()

        self._layout_btns = {}
        for key, tk in [("free","free"), ("a4","a4"), ("b5","b5")]:
            b = PianoBtn(self._t(tk))
            b.setObjectName("mainBtn")
            b.clicked.connect(lambda _, k=key: self._set_layout(k))
            lay.addWidget(b)
            self._layout_btns[key] = b

        self._margin_btn = PianoBtn(self._t("margin"))
        self._margin_btn.setObjectName("mainBtn")
        self._margin_btn.setEnabled(False)
        self._margin_btn.clicked.connect(self._open_margin_dialog)
        lay.addWidget(self._margin_btn)
        sep()

        self._scale_lbl = QLabel(self._t("scale"))
        self._scale_lbl.setObjectName("tbLabel")
        self._scale_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scale_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        lay.addWidget(self._scale_lbl)

        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setObjectName("scaleSlider")
        self._scale_slider.setRange(0, len(SCALE_STEPS) - 1)
        self._scale_slider.setValue(self.scale_idx)
        self._scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._scale_slider.setTickInterval(1)
        self._scale_slider.setFixedWidth(120)
        self._scale_slider.valueChanged.connect(self._on_scale_slider)
        self._scale_slider.sliderReleased.connect(self._save_app_settings)
        lay.addWidget(self._scale_slider)

        self._scale_val_lbl = QLabel(SCALE_LABELS[self.scale_idx])
        self._scale_val_lbl.setObjectName("tbLabel")
        self._scale_val_lbl.setFixedWidth(48)
        self._scale_val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._scale_val_lbl)
        sep()

        self._settings_btn = PianoBtn(self._t("settings"))
        self._settings_btn.setObjectName("mainBtn")
        self._settings_btn.clicked.connect(self._open_settings)
        lay.addWidget(self._settings_btn)
        sep()

        self._toc_btn = PianoBtn(self._t("toc"))
        self._toc_btn.setObjectName("mainBtn")
        self._toc_btn.clicked.connect(self._toggle_toc)
        lay.addWidget(self._toc_btn)
        sep()

        self._pdf_btn = PianoBtn(self._t("pdf_export"))
        self._pdf_btn.setObjectName("mainBtn")
        self._pdf_btn.clicked.connect(self._export_pdf)
        lay.addWidget(self._pdf_btn)

        return tb

    # ─── 書式ツールバー ──────────────────────────
    def _make_fmt_tb(self):
        tb = QWidget()
        tb.setObjectName("fmtTB")
        lay = QHBoxLayout(tb)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        def fb(tk, txt_wrap=None, txt_pre=None, txt_post=None,
               md_cmd=None, md_block=None, md_js=None):
            b = PianoBtn(self._t(tk))
            b.setObjectName("fmtBtn")
            def on_click(checked=False,
                         _tw=txt_wrap, _tp=txt_pre, _tpo=txt_post,
                         _mc=md_cmd, _mb=md_block, _mj=md_js):
                if self.edit_mode == "txt":
                    if _tw == "wrap" and _tp is not None:
                        self._md_wrap(_tp, _tpo or "")
                    elif _tw == "prefix" and _tp is not None:
                        self._md_set_block(_tp)
                    elif _tw == "num_toggle":
                        self._md_toggle_ordered()
                    elif _tw == "bullet_toggle":
                        self._md_toggle_unordered()
                    elif _tw == "insert" and _tp is not None:
                        self._md_insert(_tp)
                elif self.edit_mode == "md":
                    if _mc:
                        self._preview_web.page().runJavaScript(
                            f"window._mdvExec('{_mc}');"
                        )
                    elif _mb:
                        self._preview_web.page().runJavaScript(
                            f"window._mdvBlock('{_mb}');"
                        )
                    elif _mj:
                        self._preview_web.page().runJavaScript(_mj)
            b.clicked.connect(on_click)
            lay.addWidget(b)

        def fs():
            w = QWidget()
            w.setFixedWidth(1)
            w.setObjectName("vSep")
            lay.addWidget(w)

        fb("fmt_bold",   txt_wrap="wrap",   txt_pre="**",      txt_post="**",  md_cmd="bold")
        fb("fmt_italic", txt_wrap="wrap",   txt_pre="*",       txt_post="*",   md_cmd="italic")
        fb("fmt_strike", txt_wrap="wrap",   txt_pre="~~",      txt_post="~~",  md_cmd="strikethrough")
        fb("fmt_code",   txt_wrap="wrap",   txt_pre="\n```\n", txt_post="\n```\n",
           md_js="(function(){var s=window.getSelection();if(s&&s.rangeCount){var r=s.getRangeAt(0);var t=r.toString()||'code';r.deleteContents();var pre=document.createElement('pre');var c=document.createElement('code');c.textContent=t;pre.appendChild(c);r.insertNode(pre);var w=document.querySelector('.wrap');if(w)w.dispatchEvent(new Event('input',{bubbles:true}));}})();")
        fs()
        fb("fmt_h1",     txt_wrap="prefix", txt_pre="# ",      md_block="h1")
        fb("fmt_h2",     txt_wrap="prefix", txt_pre="## ",     md_block="h2")
        fb("fmt_h3",     txt_wrap="prefix", txt_pre="### ",    md_block="h3")

        # 本文ボタン: 現在のカーソル位置のブロックを通常の本文(段落)にする
        body_btn = PianoBtn(self._t("fmt_body"))
        body_btn.setObjectName("fmtBtn")
        def on_body():
            if self.edit_mode == "txt":
                self._md_body()
            elif self.edit_mode == "md":
                self._preview_web.page().runJavaScript("window._mdvBody && window._mdvBody();")
        body_btn.clicked.connect(on_body)
        lay.addWidget(body_btn)
        fs()
        fb("fmt_list",   txt_wrap="bullet_toggle",             md_cmd="insertUnorderedList")
        fb("fmt_num",    txt_wrap="num_toggle",                md_cmd="insertOrderedList")
        fs()
        fb("fmt_quote",  txt_wrap="prefix", txt_pre="> ",      md_block="blockquote")
        fb("fmt_hr",     txt_wrap="insert", txt_pre="\n---\n", md_cmd="insertHorizontalRule")
        _link_placeholder = f'[{self._t("link_text_default")}](URL)'
        _img_placeholder = f'![{self._t("img_alt_default")}](URL)'
        # MD編集のリンク・画像は QWebEngine 内の JS prompt() では表示できない
        # (javaScriptPrompt 未実装のため無反応になる) ため、Python 側の
        # ネイティブダイアログでURLを受け取り _mdvLink/_mdvImage で挿入する。
        link_btn = PianoBtn(self._t("fmt_link"))
        link_btn.setObjectName("fmtBtn")
        def on_link():
            if self.edit_mode == "txt":
                self._md_insert(_link_placeholder)
            elif self.edit_mode == "md":
                self._on_md_link_button()
        link_btn.clicked.connect(on_link)
        lay.addWidget(link_btn)
        img_btn = PianoBtn(self._t("fmt_img"))
        img_btn.setObjectName("fmtBtn")
        def on_img():
            if self.edit_mode == "txt":
                self._md_insert(_img_placeholder)
            elif self.edit_mode == "md":
                self._on_md_image_button()
        img_btn.clicked.connect(on_img)
        lay.addWidget(img_btn)
        fs()

        # テーブルボタン（特殊）
        tbl_btn = PianoBtn(self._t("fmt_table"))
        tbl_btn.setObjectName("fmtBtn")
        _col = self._t("table_col")
        _cell = self._t("table_cell")
        _table_html = (
            f"<table><thead><tr><th>{_col}1</th><th>{_col}2</th><th>{_col}3</th></tr></thead>"
            f"<tbody><tr><td>{_cell}</td><td>{_cell}</td><td>{_cell}</td></tr>"
            f"<tr><td>{_cell}</td><td>{_cell}</td><td>{_cell}</td></tr></tbody></table>"
        )
        def on_table():
            if self.edit_mode == "txt":
                self._md_insert_table()
            elif self.edit_mode == "md":
                self._preview_web.page().runJavaScript(
                    "(function(){"
                    "var w=document.querySelector('.wrap');"
                    "if(!w)return;"
                    "var tmp=document.createElement('div');"
                    f"tmp.innerHTML={json.dumps(_table_html)};"
                    "var tbl=tmp.firstChild;"
                    "var sel=window.getSelection();"
                    "if(sel&&sel.rangeCount){"
                    "var r=sel.getRangeAt(0);"
                    "var anchor=r.startContainer;"
                    "while(anchor&&anchor.parentNode!==w)anchor=anchor.parentNode;"
                    "if(anchor&&anchor.parentNode===w){"
                    "w.insertBefore(tbl,anchor.nextSibling);"
                    "}else{w.appendChild(tbl);}"
                    "}else{w.appendChild(tbl);}"
                    "w.dispatchEvent(new Event('input',{bubbles:true}));"
                    "if(typeof window._mdvSetupTableBtns==='function')window._mdvSetupTableBtns();"
                    "})()"
                )
        tbl_btn.clicked.connect(on_table)
        lay.addWidget(tbl_btn)

        return tb

    def _rebuild_fmt_tb(self):
        old = self._fmt_tb
        self._fmt_tb = self._make_fmt_tb()
        self._fmt_tb.setFixedHeight(self._fmt_container.height())
        self._fmt_container_layout.replaceWidget(old, self._fmt_tb)
        old.deleteLater()

    # ─── メニュー ─────────────────────────────────
    def _build_menu(self):
        mb = self.menuBar()
        mb.setNativeMenuBar(True)
        fm = mb.addMenu(self._t("file"))

        # New Window
        nw_act = QAction(self._t("new_window"), self)
        nw_act.setShortcut(QKeySequence("Ctrl+Shift+N"))
        nw_act.triggered.connect(self.new_window)
        fm.addAction(nw_act)
        fm.addSeparator()

        for tk, sc, fn in [
            ("new",             "Ctrl+N",       self.file_new),
            ("open",            "Ctrl+O",       self.file_open),
            ("save",            "Ctrl+S",       self.file_save),
            ("save_as",         "Ctrl+Shift+S", self.file_save_as),
            ("pdf_export_menu", "Ctrl+P",       self._export_pdf),
            ("html_export_menu","",             self._export_html),
        ]:
            a = QAction(self._t(tk), self)
            if sc:
                a.setShortcut(QKeySequence(sc))
            a.triggered.connect(fn)
            fm.addAction(a)
        fm.addSeparator()
        ga = QAction(self._t("upload_gdrive"), self)
        ga.triggered.connect(self._upload_gdrive)
        fm.addAction(ga)
        oa = QAction(self._t("upload_onedrive"), self)
        oa.triggered.connect(self._upload_onedrive)
        fm.addAction(oa)

    # ════════════════════════════════════════════
    #  レスポンシブ UI スケーリング
    # ════════════════════════════════════════════
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start()
        if (getattr(self, "_show_toc", False)
                and getattr(self, "edit_mode", None) in ("md", "txt")
                and hasattr(self, "_splitter")):
            self._sync_toc_width_on_resize()

    def _get_ui_scale_cat(self):
        w = self.width()
        if w >= 1100:  return "large"
        elif w >= 780: return "medium"
        elif w >= 620: return "small"
        else:          return "xsmall"

    # ウィンドウ幅の段階ごとの寸法。btn_pad/fmt_pad は左右パディング (px)。
    # min_w はスタイルシートの min-width になり、実際のボタン最小幅は
    # min_w + btn_pad*2。ここが大きいとボタンが縮まず、ツールバー全体が
    # ウィンドウ幅を超えて文字が枠外へ切れてしまうため、狭い段階では
    # 十分小さくしておく (実際の文字サイズは PianoBtn が個別に詰める)。
    _UI_SIZE_TABLE = {
        "large":  {"tb_fs": 17, "btn_pad": 16, "fmt_fs": 15, "fmt_pad": 13,
                   "lbl_fs": 15, "min_w": 44, "slider_w": 120, "val_w": 48},
        "medium": {"tb_fs": 14, "btn_pad": 11, "fmt_fs": 13, "fmt_pad": 9,
                   "lbl_fs": 13, "min_w": 28, "slider_w": 100, "val_w": 44},
        "small":  {"tb_fs": 12, "btn_pad": 6,  "fmt_fs": 11, "fmt_pad": 5,
                   "lbl_fs": 11, "min_w": 26, "slider_w": 80,  "val_w": 40},
        "xsmall": {"tb_fs": 11, "btn_pad": 4,  "fmt_fs": 10, "fmt_pad": 3,
                   "lbl_fs": 10, "min_w": 24, "slider_w": 58,  "val_w": 34},
    }

    def _apply_responsive_style(self):
        cat = self._get_ui_scale_cat()
        if cat == self._last_ui_scale_cat:
            return
        self._last_ui_scale_cat = cat

        if cat == "large":
            tb_h, fmt_h = TB_H, FMT_H
        elif cat == "medium":
            tb_h, fmt_h = 58, 44
        elif cat == "small":
            tb_h, fmt_h = 46, 36
        else:
            tb_h, fmt_h = 40, 32

        self._main_tb.setFixedHeight(tb_h)
        self._fmt_tb.setFixedHeight(fmt_h)
        self._fmt_container.setFixedHeight(fmt_h)
        self._apply_theme(refresh=False)

    def _ui_sizes(self):
        return self._UI_SIZE_TABLE[self._get_ui_scale_cat()]

    def _apply_btn_fit_metrics(self, sz):
        """各ボタンに基準フォントサイズと余白を伝え、幅に合わせて詰めさせる。"""
        for b in self.findChildren(PianoBtn):
            if b.objectName() == "fmtBtn":
                b.set_fit_metrics(sz["fmt_fs"], sz["fmt_pad"] * 2 + 4,
                                  max(12, sz["min_w"] - 14))
            else:
                b.set_fit_metrics(sz["tb_fs"], sz["btn_pad"] * 2 + 4,
                                  sz["min_w"])

    # ════════════════════════════════════════════
    #  HTML ビルダー
    # ════════════════════════════════════════════
    def _toc_base_font_px(self):
        """目次の基準フォントサイズ(px)。ウィンドウ幅で縮む tb_fs には連動させず、
        常にはっきり読める大きさを保つ。閲覧モードのオーバーレイ目次と
        MD/TXT編集モードのネイティブ目次パネルで同じ値を使い、見た目を揃える。"""
        return max(16, self._ui_sizes()["tb_fs"] + 3)

    def _toc_js(self):
        p = self._palette
        base_fs = self._toc_base_font_px()
        toc_w = self._toc_panel_width()
        return (
            '<script>'
            'window.addEventListener("load",function(){'
            'var wrap=document.querySelector(".wrap");'
            'if(!wrap)return;'
            'var hs=wrap.querySelectorAll("h1,h2,h3,h4,h5,h6");'
            'if(hs.length===0)return;'
            'hs.forEach(function(h,i){if(!h.id)h.id="mdv-h-"+i;});'
            f'var baseFs={int(base_fs)};'
            'var toc=document.createElement("div");'
            'toc.id="mdv-toc";'
            f'toc.style.cssText="position:fixed;top:0;left:0;bottom:0;width:{int(toc_w)}px;'
            f'background:{p["bg2"]};border-right:1px solid {p["border"]};'
            f'overflow-y:auto;z-index:9999;padding:12px 0 24px 0;'
            f'box-shadow:2px 0 8px rgba(0,0,0,0.4);";'
            'var title=document.createElement("div");'
            f'title.style.cssText="padding:10px 14px 8px 14px;font-weight:bold;'
            f'font-size:"+baseFs+"px;color:{p["heading"]};'
            f'border-bottom:1px solid {p["border"]};margin-bottom:6px;";'
            f'title.textContent={json.dumps(self._t("toc_title"))};'
            'toc.appendChild(title);'
            'hs.forEach(function(h){'
            'var a=document.createElement("a");'
            'var lv=parseInt(h.tagName[1]);'
            'var indent=(lv-1)*12;'
            'var fs=Math.max(16,baseFs-(lv-1));'
            f'a.style.cssText="display:block;padding:5px 12px 5px "+(indent+12)+"px;'
            f'font-size:"+fs+"px;color:{p["text"]};text-decoration:none;'
            f'cursor:pointer;border-radius:3px;margin:1px 6px;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";'
            'a.textContent=h.textContent;'
            f'a.onmouseover=function(){{this.style.background="{p["btn_hover"]}";this.style.color="{p["accent"]}";}}; '
            f'a.onmouseout=function(){{this.style.background="";this.style.color="{p["text"]}";}}; '
            'a.onclick=function(e){'
            'e.preventDefault();'
            'h.scrollIntoView({behavior:"smooth",block:"start"});'
            '};'
            'toc.appendChild(a);'
            '});'
            'document.body.appendChild(toc);'
            f'document.body.style.marginLeft="{int(toc_w) + 8}px";'
            '});'
            '</script>'
        )

    @staticmethod
    def _copy_plain_js():
        return (
            '<script>'
            'document.addEventListener("copy",function(e){'
            'var t=window.getSelection().toString();'
            'if(t&&e.clipboardData){'
            'e.clipboardData.setData("text/plain",t);'
            'e.preventDefault();}'
            '},true);'
            '</script>'
        )

    @staticmethod
    def _copy_code_btn_js():
        return (
            '<script>'
            'function _mdvCopy(btn){'
            'var pre=btn.parentElement;'
            # ライブDOMの <code> から textContent を取得する。
            # detachした clone に innerText を使うと Chromium ではレイアウト未計算のため
            # 空になる。pre 直下の子である copy ボタンは <code> の外なので混入しない。
            # <pre> のコード本文は改行を <br> ではなく実際の改行文字で保持するため
            # textContent で改行が正しく取得できる。
            'var code=pre.querySelector("code");'
            'var src=code?code:pre;'
            'var text=(src.textContent||"").replace(/\\n$/,"");'
            # Python ClipboardBridgeを使う（WebEngineのclipboard制限を回避）
            'if(typeof _mdvClipboard!=="undefined"&&_mdvClipboard){'
            '_mdvClipboard.copyText(text);'
            '}else{'
            # フォールバック: textarea経由でコピー
            'var ta=document.createElement("textarea");'
            'ta.value=text;'
            'ta.style.cssText="position:fixed;top:-9999px;left:-9999px;";'
            'document.body.appendChild(ta);ta.focus();ta.select();'
            'try{document.execCommand("copy");}catch(e){}'
            'document.body.removeChild(ta);'
            '}'
            'var orig=btn.textContent;'
            'btn.textContent="✓";btn.style.opacity="1";'
            'setTimeout(function(){btn.textContent=orig;btn.style.opacity="";},1500);}'
            'window.addEventListener("load",function(){'
            'document.querySelectorAll("pre:not(.mermaid)").forEach(function(p){'
            'if(p.querySelector(".mdv-copy-btn"))return;'
            'var b=document.createElement("button");'
            'b.className="mdv-copy-btn";'
            'b.textContent="copy";'
            'b.setAttribute("type","button");'
            'b.onclick=function(e){e.stopPropagation();_mdvCopy(this);};'
            'p.appendChild(b);});});'
            '</script>'
        )

    def _md_edit_fmt_js(self):
        """MD編集モード用の書式JS関数群"""
        return (
            '<script>'
            # ── DOM正規化: execCommand が生成しがちな不正な入れ子
            #    (<p> の中に <ol>/<ul> が入る、隣接する同種リストが分裂する等) を
            #    修復する。リスト操作系コマンドの直後に必ず呼び出す。
            'window._mdvNormalize=function(){'
            'var w=document.querySelector(".wrap");if(!w)return;'
            'var guard=0;'
            'while(guard++<50){'
            'var list=w.querySelector("p>ol,p>ul");'
            'if(!list)break;'
            'var p=list.parentNode;'
            'if(!p||!p.parentNode)break;'
            'var before=document.createElement("p");'
            'var after=document.createElement("p");'
            'var seen=false;'
            'Array.prototype.slice.call(p.childNodes).forEach(function(n){'
            'if(n===list){seen=true;return;}'
            '(seen?after:before).appendChild(n);'
            '});'
            'var parent=p.parentNode;'
            'if(before.childNodes.length)parent.insertBefore(before,p);'
            'parent.insertBefore(list,p);'
            'if(after.childNodes.length)parent.insertBefore(after,p);'
            'parent.removeChild(p);'
            '}'
            '["ol","ul"].forEach(function(tn){'
            'var again=true;'
            'while(again){'
            'again=false;'
            'var els=w.querySelectorAll(tn);'
            'for(var i=0;i<els.length;i++){'
            'var cur=els[i];var prev=cur.previousSibling;'
            'while(prev&&prev.nodeType===3&&!prev.textContent.trim())prev=prev.previousSibling;'
            'if(prev&&prev.nodeName&&prev.nodeName.toLowerCase()===tn){'
            'while(cur.firstChild)prev.appendChild(cur.firstChild);'
            'cur.parentNode.removeChild(cur);'
            'again=true;break;'
            '}'
            '}'
            '}'
            '});'
            'Array.prototype.slice.call(w.childNodes).forEach(function(n){'
            'if(n.nodeType===3&&n.textContent.trim()!==""){'
            'var np=document.createElement("p");'
            'n.parentNode.insertBefore(np,n);np.appendChild(n);'
            '}'
            '});'
            # リスト解除等で残る、段落間に浮いた孤立<br>(直下の子要素)を除去する
            '(function(){'
            'Array.prototype.slice.call(w.children).forEach(function(el){'
            'if(el.tagName==="BR")el.remove();'
            '});'
            '})();'
            'w.querySelectorAll("p:empty").forEach(function(e){e.remove();});'
            '};'
            # ── ブロック操作の共通部品 ──────────────────────────────
            #    execCommand("formatBlock") は空のブロックや、ツールバーへ
            #    フォーカスが移って選択が失われた状態では効かないことがある。
            #    対象ブロックを自前で特定して直接置き換えることで、どの状態
            #    からでも同じ結果になるようにする。
            'window._mdvHeadings={H1:1,H2:1,H3:1,H4:1,H5:1,H6:1};'
            # .wrap 直下まで遡って、そのノードが属するトップレベルブロックを返す
            'window._mdvTopBlock=function(node){'
            'var w=document.querySelector(".wrap");if(!w||!node)return null;'
            'var el=(node.nodeType===3)?node.parentNode:node;'
            'if(el===w){'
            # キャレットが .wrap 直下にある場合は子要素側へ寄せる
            'var s=window.getSelection();'
            'var i=(s&&s.rangeCount)?s.getRangeAt(0).startOffset:0;'
            'return w.children[Math.min(i,Math.max(0,w.children.length-1))]||null;'
            '}'
            'while(el&&el.parentNode&&el.parentNode!==w)el=el.parentNode;'
            'return(el&&el.parentNode===w)?el:null;'
            '};'
            # 直近にキャレットがあったブロックを覚えておく (ツールバー押下で
            # Web ビューからフォーカスが外れても対象を見失わないため)
            'window._mdvLastBlock=null;'
            # ツールバー押下で選択 (Range) 自体が失われるため、インライン用の
            # 選択範囲も複製して保持する (リンク・画像の挿入で復元する)。
            'window._mdvSavedRange=null;'
            'window._mdvSaveRange=function(){'
            'try{'
            'var w=document.querySelector(".wrap");if(!w)return;'
            'var s=window.getSelection();if(!s||!s.rangeCount)return;'
            'var r=s.getRangeAt(0);'
            'if(!w.contains(r.startContainer)||!w.contains(r.endContainer))return;'
            'window._mdvSavedRange=r.cloneRange();'
            '}catch(e){}'
            '};'
            'document.addEventListener("selectionchange",function(){'
            'var w=document.querySelector(".wrap");if(!w)return;'
            'var s=window.getSelection();if(!s||!s.rangeCount)return;'
            'if(!w.contains(s.getRangeAt(0).startContainer))return;'
            'var b=window._mdvTopBlock(s.getRangeAt(0).startContainer);'
            'if(b)window._mdvLastBlock=b;'
            'window._mdvSaveRange();'
            '});'
            # 書式を適用する対象ブロック (選択が失われていれば記憶した位置)
            'window._mdvTargetBlock=function(){'
            'var w=document.querySelector(".wrap");if(!w)return null;'
            'var s=window.getSelection();'
            'if(s&&s.rangeCount&&w.contains(s.getRangeAt(0).startContainer)){'
            'var b=window._mdvTopBlock(s.getRangeAt(0).startContainer);'
            'if(b)return b;'
            '}'
            'var last=window._mdvLastBlock;'
            'if(last&&last.isConnected&&w.contains(last))return last;'
            'return w.lastElementChild;'
            '};'
            # ブロックの先頭 (offset 指定があればその位置) にキャレットを置く
            'window._mdvCaretTo=function(el,toEnd){'
            'if(!el)return;'
            'var s=window.getSelection();if(!s)return;'
            'var r=document.createRange();'
            'r.selectNodeContents(el);r.collapse(!toEnd);'
            's.removeAllRanges();s.addRange(r);'
            'window._mdvLastBlock=window._mdvTopBlock(el);'
            '};'
            # ブロックの中身を保ったままタグだけ差し替える
            'window._mdvRetag=function(el,tagName){'
            'if(!el||!el.parentNode)return null;'
            'if(el.tagName===tagName.toUpperCase())return el;'
            'var nu=document.createElement(tagName);'
            'while(el.firstChild)nu.appendChild(el.firstChild);'
            'if(!nu.firstChild)nu.appendChild(document.createElement("br"));'
            'el.parentNode.replaceChild(nu,el);'
            'return nu;'
            '};'
            # ── URL の許可判定 (Python 側 _san_safe_url と同じ方針) ──
            #    javascript:/data:/vbscript: 等はリンク・画像に使わせない。
            'window._mdvSafeUrl=function(u){'
            'if(!u)return false;'
            'var v=String(u).trim();if(!v)return false;'
            'var low=v.toLowerCase().replace(/[\\t\\n\\r]/g,"");'
            'if(low.indexOf("#")===0||low.indexOf("/")===0'
            '||low.indexOf("./")===0||low.indexOf("../")===0)return true;'
            'if(low.indexOf("data:")===0)return false;'
            'var head=low.split("/",1)[0];'
            'if(head.indexOf(":")>=0){'
            'return(low.indexOf("http:")===0||low.indexOf("https:")===0'
            '||low.indexOf("mailto:")===0||low.indexOf("tel:")===0);'
            '}'
            'return true;'
            '};'
            # ── 保存済み Range を復元する (ツールバー押下で失った選択へ戻る) ──
            'window._mdvRestoreRange=function(){'
            'var w=document.querySelector(".wrap");if(!w)return false;'
            'var s=window.getSelection();if(!s)return false;'
            'var r=window._mdvSavedRange;'
            'if(r){try{'
            'var sc=r.startContainer,ec=r.endContainer;'
            'if(w.contains(sc)&&w.contains(ec)){'
            'w.focus();'
            's.removeAllRanges();s.addRange(r.cloneRange());'
            'return true;'
            '}'
            '}catch(e){}}'
            # 復元先がない場合は末尾にキャレットを置く
            'try{'
            'w.focus();'
            'var nr=document.createRange();'
            'nr.selectNodeContents(w);nr.collapse(false);'
            's.removeAllRanges();s.addRange(nr);'
            'return true;'
            '}catch(e){return false;}'
            '};'
            # ── リンク挿入 (Python 側のネイティブダイアログから URL を受け取る) ──
            #    選択範囲があればその文字列をリンク文言にし、なければ既定文言で挿入する。
            'window._mdvLink=function(url,label){'
            'if(!window._mdvSafeUrl(url))return false;'
            'if(!window._mdvRestoreRange())return false;'
            'var s=window.getSelection();if(!s||!s.rangeCount)return false;'
            'var r=s.getRangeAt(0);'
            'var txt=r.toString()||label||"link";'
            'try{r.deleteContents();}catch(e){return false;}'
            'var a=document.createElement("a");'
            'a.setAttribute("href",String(url).trim());'
            'a.textContent=txt;'
            'r.insertNode(a);'
            'try{'
            'var nr=document.createRange();'
            'nr.setStartAfter(a);nr.collapse(true);'
            's.removeAllRanges();s.addRange(nr);'
            '}catch(e){}'
            'window._mdvSaveRange();'
            'var w=document.querySelector(".wrap");'
            'if(w)w.dispatchEvent(new Event("input",{bubbles:true}));'
            'return true;'
            '};'
            # ── 画像挿入 (リンクと同様に Range 復元して <img> を挿入) ──
            'window._mdvImage=function(url,alt){'
            'if(!window._mdvSafeUrl(url))return false;'
            'if(!window._mdvRestoreRange())return false;'
            'var s=window.getSelection();if(!s||!s.rangeCount)return false;'
            'var r=s.getRangeAt(0);'
            'try{r.deleteContents();}catch(e){return false;}'
            'var img=document.createElement("img");'
            'img.setAttribute("src",String(url).trim());'
            'img.setAttribute("alt",alt||"");'
            'r.insertNode(img);'
            'try{'
            'var nr=document.createRange();'
            'nr.setStartAfter(img);nr.collapse(true);'
            's.removeAllRanges();s.addRange(nr);'
            '}catch(e){}'
            'window._mdvSaveRange();'
            'var w=document.querySelector(".wrap");'
            'if(w)w.dispatchEvent(new Event("input",{bubbles:true}));'
            'return true;'
            '};'
            # ── 書式コマンド (HR は <p> を後挿入してカーソル位置を安定させる) ──
            'window._mdvExec=function(cmd){'
            'if(cmd==="insertHorizontalRule"){'
            'document.execCommand("insertHTML",false,"<hr><p><br></p>");'
            '}else{'
            'document.execCommand(cmd,false,null);'
            '}'
            'window._mdvNormalize();'
            'var w=document.querySelector(".wrap");'
            'if(w)w.dispatchEvent(new Event("input",{bubbles:true}));'
            '};'
            'window._mdvBlock=function(tag){'
            'var w=document.querySelector(".wrap");if(!w)return;'
            'var s=window.getSelection();'
            'var multi=!!(s&&s.rangeCount&&!s.getRangeAt(0).collapsed);'
            'if(multi){'
            # 複数行にまたがる選択は execCommand の方が自然にまとまる
            'document.execCommand("formatBlock",false,tag);'
            '}else{'
            'var b=window._mdvTargetBlock();'
            'if(b&&b.tagName!=="PRE"&&b.tagName!=="UL"&&b.tagName!=="OL"'
            '&&b.tagName!=="TABLE"){'
            'var nu=window._mdvRetag(b,tag);'
            'window._mdvCaretTo(nu,true);'
            '}else{'
            'document.execCommand("formatBlock",false,tag);'
            '}'
            '}'
            'window._mdvNormalize();'
            'w.dispatchEvent(new Event("input",{bubbles:true}));'
            '};'
            # ── 本文ボタン: 現在ブロックを通常の段落に戻す ──
            #    リスト項目内ではリストそのものを解除し、引用・コードブロック内では
            #    直後に新しい本文段落を作って抜ける
            'window._mdvBody=function(){'
            'var w=document.querySelector(".wrap");if(!w)return;'
            'var sel=window.getSelection();'
            'var node=(sel&&sel.rangeCount)?sel.getRangeAt(0).startContainer:null;'
            'var el=(node&&node.nodeType===3)?node.parentNode:node;'
            'var li=(el&&el.closest&&w.contains(el))?el.closest("li"):null;'
            'if(li&&w.contains(li)){'
            'var listEl=li.closest("ol,ul");'
            'var cmd=(listEl&&listEl.tagName==="OL")?"insertOrderedList":"insertUnorderedList";'
            'document.execCommand(cmd,false,null);'
            'window._mdvNormalize();'
            # リスト解除後に残ったブロックが見出し等なら本文に直す
            'var after=window._mdvTargetBlock();'
            'if(after&&after.tagName!=="P"&&after.tagName!=="UL"&&after.tagName!=="OL"){'
            'window._mdvCaretTo(window._mdvRetag(after,"p"),true);'
            '}'
            '}else{'
            'var block=window._mdvTargetBlock();'
            'if(block){'
            'if(block.tagName==="PRE"||block.tagName==="BLOCKQUOTE"){'
            # コードブロック・引用は中身を壊さず、直後に新しい本文段落を作って抜ける
            'var p=document.createElement("p");p.appendChild(document.createElement("br"));'
            'block.insertAdjacentElement("afterend",p);'
            'window._mdvCaretTo(p,false);'
            '}else{'
            # 見出し等はタグを直接 <p> に置き換える。空のブロックでも、選択が
            # 失われていても確実に本文へ戻る (execCommand は両方で失敗する)。
            'window._mdvCaretTo(window._mdvRetag(block,"p"),true);'
            '}'
            '}'
            'window._mdvNormalize();'
            '}'
            'w.dispatchEvent(new Event("input",{bubbles:true}));'
            '};'
            # ── 外部からの貼り付け ──
            #    既定は書式なし(プレーンテキスト)で挿入するが、リンクは活かす:
            #    1) text/html 中の最初の <a href> をリンクとして挿入
            #    2) Markdown 記法 [文言](URL) の貼り付けをリンクに変換
            #    3) 素の URL だけの貼り付けを自動リンク化
            #    いずれも _mdvSafeUrl で危険スキームを弾く。
            'document.addEventListener("paste",function(e){'
            'var w=document.querySelector(".wrap");'
            'if(!w||!w.contains(e.target))return;'
            'e.preventDefault();'
            'var cd=e.clipboardData||window.clipboardData;'
            'var inserted=false;'
            'try{'
            'var html=cd?cd.getData("text/html"):"";'
            'if(html){'
            'var doc=new DOMParser().parseFromString(html,"text/html");'
            'var link=doc.querySelector("a[href]");'
            'if(link&&window._mdvSafeUrl(link.getAttribute("href"))){'
            'var label=(link.textContent||"").trim()||link.getAttribute("href");'
            'document.execCommand("insertHTML",false,'
            '\'<a href="\'+link.getAttribute("href").replace(/"/g,"&quot;")+\'">\''
            '+label.replace(/</g,"&lt;").replace(/>/g,"&gt;")+"</a>");'
            'inserted=true;'
            '}'
            '}'
            '}catch(err){}'
            'if(!inserted){'
            'var t=cd?cd.getData("text/plain"):"";'
            'if(t){'
            'var m=t.trim().match(/^\\[([^\\]]+)\\]\\((\\S+?)\\)$/);'
            'if(m&&window._mdvSafeUrl(m[2])){'
            'document.execCommand("insertHTML",false,'
            '\'<a href="\'+m[2].replace(/"/g,"&quot;")+\'">\''
            '+m[1].replace(/</g,"&lt;").replace(/>/g,"&gt;")+"</a>");'
            '}else if(window._mdvSafeUrl(t.trim())'
            '&&/^(https?:\\/\\/|mailto:|tel:|#[^\\s]*|\\/[^\\s]*)$/i.test(t.trim())){'
            'var u=t.trim();'
            'document.execCommand("insertHTML",false,'
            '\'<a href="\'+u.replace(/"/g,"&quot;")+\'">\''
            '+u.replace(/</g,"&lt;").replace(/>/g,"&gt;")+"</a>");'
            '}else{'
            'document.execCommand("insertText",false,t);'
            '}'
            '}'
            '}'
            'w.dispatchEvent(new Event("input",{bubbles:true}));'
            '},true);'
            # ── Enter の扱い ────────────────────────────────────────
            #    ・テーブルセル内 → <br> を挿入 (セルを割らない)
            #    ・見出し内       → 新しい行は必ず本文 <p> にする
            #      (ブラウザ既定は行末でしか見出しから抜けず、行頭・行中で
            #       改行すると見出しが複製されて本文に戻れなくなる)
            'document.addEventListener("keydown",function(e){'
            'if(e.key!=="Enter"||e.shiftKey)return;'
            # IME 変換中の Enter は確定操作なので触らない
            'if(e.isComposing||e.keyCode===229)return;'
            'var sel=window.getSelection();'
            'if(!sel||!sel.rangeCount)return;'
            'var wrap=document.querySelector(".wrap");'
            'if(!wrap)return;'
            'var rng=sel.getRangeAt(0);'
            'if(!wrap.contains(rng.startContainer))return;'
            'var n=rng.startContainer;'
            'while(n&&n!==wrap){'
            'if(n.nodeName==="TD"||n.nodeName==="TH"){'
            'e.preventDefault();'
            'document.execCommand("insertHTML",false,"<br>");'
            'wrap.dispatchEvent(new Event("input",{bubbles:true}));'
            'return;'
            '}'
            'n=n.parentNode;'
            '}'
            'var blk=window._mdvTopBlock(rng.startContainer);'
            'if(!blk||!window._mdvHeadings[blk.tagName])return;'
            'e.preventDefault();'
            'if(!rng.collapsed)rng.deleteContents();'
            # 中身が空の見出しで改行 → その行自体を本文に戻す
            # (リストの空項目で Enter を押すとリストを抜けるのと同じ感覚)
            'if(!blk.textContent&&!blk.querySelector("img")){'
            'window._mdvCaretTo(window._mdvRetag(blk,"p"),false);'
            'wrap.dispatchEvent(new Event("input",{bubbles:true}));'
            'return;'
            '}'
            # キャレットから見出し末尾までを切り出して本文段落にする
            'var tail=document.createRange();'
            'tail.setStart(rng.startContainer,rng.startOffset);'
            'tail.setEnd(blk,blk.childNodes.length);'
            'var frag=tail.extractContents();'
            'var p=document.createElement("p");'
            'p.appendChild(frag);'
            # 見出し側に <br> だけが残ることがあるので掃除する
            'var only=blk.childNodes.length===1&&blk.firstChild.nodeName==="BR";'
            'if(only)blk.removeChild(blk.firstChild);'
            'if(!p.textContent&&!p.querySelector("img"))'
            'p.innerHTML="<br>";'
            'if(!blk.textContent&&!blk.querySelector("img")){'
            # 行頭で改行した場合: 空の本文行を見出しの前に置き、見出しは残す
            'blk.appendChild(document.createElement("br"));'
            'var lead=document.createElement("p");'
            'lead.appendChild(document.createElement("br"));'
            'blk.parentNode.insertBefore(lead,blk);'
            'while(p.firstChild)blk.appendChild(p.firstChild);'
            'if(blk.childNodes.length>1&&blk.firstChild.nodeName==="BR")'
            'blk.removeChild(blk.firstChild);'
            'window._mdvCaretTo(blk,false);'
            '}else{'
            'blk.insertAdjacentElement("afterend",p);'
            'window._mdvCaretTo(p,false);'
            '}'
            'wrap.dispatchEvent(new Event("input",{bubbles:true}));'
            '},true);'
            # ── テーブルに +列 / +行 ボタンを追加 ──
            'window._mdvSetupTableBtns=function(){'
            'var wrap=document.querySelector(".wrap");'
            'if(!wrap)return;'
            'wrap.querySelectorAll(".mdv-table-ctrl").forEach(function(b){b.remove();});'
            'wrap.querySelectorAll("table").forEach(function(tbl){'
            'var ctrl=document.createElement("div");'
            'ctrl.className="mdv-table-ctrl";'
            'ctrl.contentEditable="false";'
            'ctrl.style.cssText="display:flex;gap:4px;margin:2px 0 10px 0;user-select:none;";'
            'var mkBtn=function(label,title,fn){'
            'var b=document.createElement("button");'
            'b.type="button";b.textContent=label;b.title=title;'
            'b.style.cssText="padding:2px 10px;font-size:11px;cursor:pointer;'
            'border:1px solid rgba(74,158,255,0.5);border-radius:3px;'
            'background:rgba(74,158,255,0.12);color:#4a9eff;font-weight:bold;";'
            'b.onmouseenter=function(){this.style.background="rgba(74,158,255,0.3)";};'
            'b.onmouseleave=function(){this.style.background="rgba(74,158,255,0.12)";};'
            'b.onclick=fn;return b;'
            '};'
            f'ctrl.appendChild(mkBtn({json.dumps(self._t("table_add_col"))},'
            f'{json.dumps(self._t("table_add_col_title"))},function(e){{'
            'e.stopPropagation();e.preventDefault();'
            'var rows=tbl.querySelectorAll("tr");'
            'rows.forEach(function(row,i){'
            'var isHead=tbl.querySelector("thead")&&row.closest("thead")!==null;'
            'var cell=document.createElement(isHead?"th":"td");'
            f'cell.textContent=isHead?{json.dumps(self._t("table_col"))}:{json.dumps(self._t("table_cell"))};'
            'row.appendChild(cell);'
            '});'
            'var w=document.querySelector(".wrap");'
            'if(w)w.dispatchEvent(new Event("input",{bubbles:true}));'
            'window._mdvSetupTableBtns();'
            '}));'
            f'ctrl.appendChild(mkBtn({json.dumps(self._t("table_add_row"))},'
            f'{json.dumps(self._t("table_add_row_title"))},function(e){{'
            'e.stopPropagation();e.preventDefault();'
            'var tbody=tbl.querySelector("tbody")||tbl;'
            'var lastRow=tbody.querySelector("tr:last-child");'
            'if(!lastRow)return;'
            'var newRow=document.createElement("tr");'
            'for(var j=0;j<lastRow.cells.length;j++){'
            'var td=document.createElement("td");'
            f'td.textContent={json.dumps(self._t("table_cell"))};'
            'newRow.appendChild(td);'
            '}'
            'tbody.appendChild(newRow);'
            'var w=document.querySelector(".wrap");'
            'if(w)w.dispatchEvent(new Event("input",{bubbles:true}));'
            'window._mdvSetupTableBtns();'
            '}));'
            'tbl.insertAdjacentElement("afterend",ctrl);'
            '});'
            '};'
            'window.addEventListener("load",function(){setTimeout(window._mdvSetupTableBtns,200);});'
            '</script>'
        )

    def _css(self, fs):
        p  = self._palette
        # 水平線の色: 枠線色と淡色テキストの中間
        _HR_COLOR = _mix_hex(p["border"], p["text_dim"], 0.5)
        fw = "600" if self.bold_mode else "400"
        if sys.platform == "win32":
            ff = ("'Yu Gothic UI', 'Meiryo', 'Segoe UI', "
                  "'Noto Sans JP', sans-serif")
        else:
            ff = ("'Helvetica Neue', '-apple-system', "
                  "'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif")
        if self.ui_font_family and self.ui_font_family not in (
                "Helvetica Neue", "-apple-system", "Yu Gothic UI", "Segoe UI"):
            ff = f"'{self.ui_font_family}', " + ff
        return (
            "*{box-sizing:border-box;margin:0;padding:0}"
            f"html,body{{background:{p['bg']};color:{p['text']};"
            f"font-family:{ff};font-size:{fs}px;line-height:1.8;font-weight:{fw};"
            # 横方向の溢れを文書幅に収める。長い表・URL・数式・コードが
            # 行の最小内容幅を押し広げ、右側に広い空白と水平スクロールが
            # 出るのを防ぐ (閲覧/MD編集/TXT編集の共通プレビューCSS)。
            "max-width:100%;overflow-x:hidden;}}"
            f"h1{{font-size:{int(fs*1.85)}px;color:{p['heading']};"
            f"margin:28px 0 16px}}"
            f"h2{{font-size:{int(fs*1.4)}px;color:{p['heading']};"
            f"margin:22px 0 12px}}"
            f"h3{{font-size:{int(fs*1.15)}px;color:{p['heading']};margin:18px 0 10px}}"
            f"h4,h5,h6{{color:{p['heading']};margin:14px 0 8px}}"
            "p{margin:10px 0;overflow-wrap:break-word}"
            "li{overflow-wrap:break-word}"
            f"a{{color:{p['accent']};text-decoration:none;overflow-wrap:anywhere}}"
            "a:hover{text-decoration:underline}"
            f"code{{background:{p['bg3']};color:{p['code_fg']};"
            "padding:2px 6px;border-radius:3px;overflow-wrap:anywhere;"
            "font-family:'Menlo','Monaco',monospace;font-size:.88em}"
            f"pre{{position:relative;background:{p['bg3']};border:1px solid {p['border']};"
            "border-radius:6px;padding:16px;overflow-x:auto;margin:14px 0;max-width:100%}"
            f"pre code{{background:none;padding:0;color:{p['text']}}}"
            "pre.mermaid{background:transparent;border:none;padding:12px 0;"
            "text-align:center;overflow-x:auto}"
            "pre.mermaid svg{max-width:100%;height:auto}"
            f".mdv-copy-btn{{position:absolute;top:6px;right:8px;padding:2px 10px;"
            f"font-size:11px;line-height:1.5;cursor:pointer;"
            f"border:1px solid {p['border']};border-radius:4px;"
            f"background:{p['copy_btn_bg']};color:{p['copy_btn_fg']};"
            "font-family:system-ui,sans-serif;user-select:none;opacity:.75;"
            "z-index:10;transition:opacity .15s}"
            f".mdv-copy-btn:hover{{opacity:1;color:{p['text']}}}"
            f"blockquote{{border-left:4px solid {p['accent']};background:{p['bg3']};"
            "margin:14px 0;padding:10px 18px;border-radius:0 4px 4px 0;"
            f"color:{p['text_dim']}}}"
            f"table{{border-collapse:collapse;width:100%;max-width:100%;margin:16px 0}}"
            f"th,td{{border:1px solid {p['border']};padding:9px 14px;text-align:left;"
            "overflow-wrap:break-word;word-break:break-word}}"
            f"th{{background:{p['bg3']};color:{p['heading']};font-weight:700}}"
            f"tr:nth-child(even){{background:{p['row_even']}}}"
            "ul,ol{padding-left:1.7em;margin:10px 0}"
            "li{margin:4px 0}"
            # 水平線: 1px の枠線色だと背景に溶けてほぼ見えなかったため、
            # 太さを 4px にし、色は枠線色と淡色テキストの中間にして
            # コントラストを少しだけ上げる (テーマごとの雰囲気は保つ)。
            f"hr{{border:none;height:4px;background:{_HR_COLOR};"
            f"margin:24px 0;border-radius:2px}}"
            "img{max-width:100%;height:auto;border-radius:4px}"
            "svg{max-width:100%;height:auto}"
            ".task-list-item{list-style:none;margin-left:-1.4em}"
            ".task-list-item input[type='checkbox']{margin-right:6px;vertical-align:middle}"
            + self._math_css() + self._front_matter_css()
        )

    def _math_css(self):
        """LaTeX 数式の組版用 CSS。

        数式は Computer Modern 系 (Latin Modern / CMU) を優先し、
        無ければ一般的なセリフ体にフォールバックする。本文フォントの
        設定に引きずられて数式だけ崩れることがないよう独立指定にする。"""
        return (
            ".mdv-math{font-family:'Latin Modern Math','Latin Modern Roman',"
            "'CMU Serif','Computer Modern','STIX Two Math','Times New Roman',"
            "'Hiragino Mincho ProN',serif;font-weight:400;line-height:1.2;"
            "white-space:nowrap;}"
            ".mdv-math-display{display:block;text-align:center;margin:18px 0;"
            "font-size:1.15em;overflow-x:auto;overflow-y:hidden;max-width:100%;}"
            ".mdv-math .mdv-var{font-style:italic;}"
            ".mdv-math .mdv-rm,.mdv-math .mdv-txt{font-style:normal;}"
            # 関数名は立体。直後の引数との間に LaTeX と同じ細い空きを入れる
            ".mdv-math .mdv-fn{font-style:normal;margin-right:.16em;}"
            ".mdv-math .mdv-txt{white-space:pre-wrap;}"
            ".mdv-math .mdv-bf{font-weight:700;}"
            ".mdv-math .mdv-it{font-style:italic;}"
            ".mdv-math .mdv-sf{font-family:system-ui,sans-serif;font-style:normal;}"
            ".mdv-math .mdv-tt{font-family:'Menlo','Monaco',monospace;font-style:normal;}"
            ".mdv-math .mdv-bb,.mdv-math .mdv-cal,.mdv-math .mdv-frak"
            "{font-style:normal;}"
            ".mdv-math .mdv-bin{margin:0 .22em;}"
            ".mdv-math .mdv-sp-punct{display:inline-block;width:.17em;}"
            # 上付き / 下付き
            ".mdv-math .mdv-sup,.mdv-math .mdv-sub{font-size:.72em;"
            "line-height:1;display:inline-block;}"
            ".mdv-math .mdv-sup{vertical-align:.62em;}"
            ".mdv-math .mdv-sub{vertical-align:-.34em;}"
            ".mdv-math .mdv-scripts{display:inline-flex;flex-direction:column;"
            "vertical-align:middle;align-items:flex-start;line-height:1;}"
            ".mdv-math .mdv-scripts>.mdv-sup,.mdv-math .mdv-scripts>.mdv-sub"
            "{vertical-align:baseline;}"
            # 分数
            ".mdv-math .mdv-frac{display:inline-flex;flex-direction:column;"
            "vertical-align:middle;text-align:center;margin:0 .18em;"
            "position:relative;top:-.05em;}"
            ".mdv-math .mdv-frac-n{padding:0 .3em .1em .3em;"
            "border-bottom:.055em solid currentColor;}"
            ".mdv-math .mdv-frac-d{padding:.1em .3em 0 .3em;}"
            ".mdv-math .mdv-frac-t{font-size:.85em;}"
            ".mdv-math .mdv-frac-nb>.mdv-frac-n{border-bottom:none;}"
            # 根号
            ".mdv-math .mdv-sqrt{display:inline-flex;align-items:flex-start;"
            "margin:0 .1em;}"
            ".mdv-math .mdv-sqrt-sign{display:inline-block;transform-origin:top;}"
            ".mdv-math .mdv-sqrt-idx{font-size:.6em;align-self:flex-start;"
            "margin-right:-.35em;position:relative;top:-.15em;}"
            ".mdv-math .mdv-sqrt-body{border-top:.055em solid currentColor;"
            "padding:.14em .2em 0 .1em;margin-left:-.06em;}"
            # 上線 / 下線 / アクセント
            ".mdv-math .mdv-over{border-top:.055em solid currentColor;"
            "padding-top:.12em;display:inline-block;}"
            ".mdv-math .mdv-under{border-bottom:.055em solid currentColor;"
            "padding-bottom:.06em;display:inline-block;}"
            ".mdv-math .mdv-acc{display:inline-block;position:relative;}"
            ".mdv-math .mdv-acc>.mdv-acc-m,.mdv-math .mdv-acc>.mdv-acc-wide"
            "{position:absolute;left:0;right:0;top:-.58em;text-align:center;"
            "line-height:1;pointer-events:none;}"
            ".mdv-math .mdv-acc>.mdv-acc-m{font-size:.95em;}"
            ".mdv-math .mdv-acc>.mdv-acc-wide{font-size:.7em;top:-.5em;}"
            # 大型演算子と上下の添字
            ".mdv-math .mdv-bigop{font-size:1.5em;line-height:1;"
            "vertical-align:-.22em;margin:0 .08em;}"
            ".mdv-math .mdv-bigop-int{font-size:1.7em;vertical-align:-.3em;}"
            ".mdv-math .mdv-lim{display:inline-flex;flex-direction:column;"
            "align-items:center;vertical-align:middle;line-height:1.05;"
            "margin:0 .12em;}"
            ".mdv-math .mdv-lim-up,.mdv-math .mdv-lim-lo{font-size:.68em;}"
            # 伸縮する区切り記号 (flex の stretch で自動的に高さが揃う)
            ".mdv-math .mdv-fence{display:inline-flex;align-items:stretch;"
            "vertical-align:middle;}"
            ".mdv-math .mdv-fence>.mdv-fb{display:inline-flex;"
            "align-items:center;padding:0 .1em;}"
            ".mdv-math .mdv-d{flex:0 0 auto;align-self:stretch;width:.3em;}"
            # 括弧は半楕円 (border-radius の水平/垂直を別指定) で描くことで
            # 高さが変わっても丸括弧らしい曲線になる
            ".mdv-math .mdv-d-lparen{border:.07em solid currentColor;"
            "border-right:0;border-radius:100% 0 0 100%/50% 0 0 50%;"
            "margin-right:.05em;}"
            ".mdv-math .mdv-d-rparen{border:.07em solid currentColor;"
            "border-left:0;border-radius:0 100% 100% 0/0 50% 50% 0;"
            "margin-left:.05em;}"
            ".mdv-math .mdv-d-lbrack{border:.07em solid currentColor;"
            "border-right:0;margin-right:.05em;}"
            ".mdv-math .mdv-d-rbrack{border:.07em solid currentColor;"
            "border-left:0;margin-left:.05em;}"
            ".mdv-math .mdv-d-vert{width:0;border-left:.06em solid currentColor;"
            "margin:0 .22em;}"
            ".mdv-math .mdv-d-dvert{width:.14em;"
            "border-left:.06em solid currentColor;"
            "border-right:.06em solid currentColor;margin:0 .22em;}"
            ".mdv-math .mdv-d-glyph{display:inline-block;align-self:center;"
            "transform-origin:center;font-weight:300;margin:0 .1em;}"
            # 行列 / 場合分け
            ".mdv-math .mdv-mtx{display:inline-grid;align-items:center;"
            "vertical-align:middle;}"
            ".mdv-math .mdv-mc{display:inline-block;}"
            ".mdv-math .mdv-unknown,.mdv-math .mdv-tex-raw"
            "{font-family:'Menlo','Monaco',monospace;font-size:.9em;"
            "font-style:normal;opacity:.8;}"
        )

    def _front_matter_css(self):
        p = self._palette
        return (
            f".mdv-fm{{background:{p['bg3']};border:1px solid {p['border']};"
            f"border-left:4px solid {p['accent']};border-radius:0 6px 6px 0;"
            f"padding:10px 16px 12px 16px;margin:0 0 20px 0;font-size:.9em;}}"
            f".mdv-fm-title{{color:{p['heading']};font-weight:700;"
            f"font-size:.92em;letter-spacing:.04em;text-transform:uppercase;"
            f"margin-bottom:6px;opacity:.85;}}"
            ".mdv-fm-row{display:flex;gap:10px;align-items:baseline;"
            "padding:2px 0;flex-wrap:wrap;}"
            f".mdv-fm-key{{color:{p['accent']};font-weight:700;"
            f"min-width:110px;flex:0 0 auto;}}"
            f".mdv-fm-val{{color:{p['text']};flex:1 1 auto;"
            f"word-break:break-word;}}"
            f".mdv-fm-tag{{display:inline-block;background:{p['bg2']};"
            f"border:1px solid {p['border']};border-radius:10px;"
            f"padding:0 9px;margin:1px 3px 1px 0;font-size:.9em;}}"
            f".mdv-fm-raw{{background:none;border:none;padding:0;margin:0;"
            f"white-space:pre-wrap;color:{p['text_dim']};}}"
        )

    def _tex_layout_css(self):
        """体裁コマンド (\\newpage 等) の見た目。

        通常はコマンドの存在を見せない。改ページは A4/B5 表示では
        _page_break_js が高さを入れて次ページ送りにし、PDF では
        print 側の break-after で実際にページを分ける。"""
        p = self._palette
        return (
            ".mdv-texcmd{-webkit-user-modify:read-only;}"
            ".mdv-newpage{display:block;height:0;clear:both;}"
            ".mdv-vspace{display:block;}"
            # MD編集モードでのみ、消したり動かしたりできるよう印を出す
            # (閲覧・書き出しでは editable_css を付けないので見えない)
            ".wrap[contenteditable] .mdv-newpage{"
            f"height:auto!important;min-height:1.6em;margin:.5em 0;"
            f"border-top:1px dashed {p['accent']};opacity:.65;}}"
            ".wrap[contenteditable] .mdv-newpage::after{"
            f"content:attr(data-tex);display:block;font-size:11px;"
            f"color:{p['accent']};padding-top:2px;}}"
            ".wrap[contenteditable] .mdv-vspace,"
            ".wrap[contenteditable] .mdv-texcmd:not(.mdv-newpage){"
            f"outline:1px dotted {p['border']};}}"
        )

    def _page_break_js(self, page_height_mm):
        _pg_prefix = json.dumps(self._t("page_label_prefix"))
        _pg_suffix = json.dumps(self._t("page_label_suffix"))
        return (
            f'<script>'
            f'window.addEventListener("load",function(){{'
            f'var w=document.querySelector(".wrap");'
            f'if(!w)return;'
            f'w.style.position="relative";'
            f'var pH={page_height_mm};'
            f'var mm2px=96/25.4;'
            f'var pgH=pH*mm2px;'
            f'function upd(){{'
            f'document.querySelectorAll(".pg-brk").forEach(function(e){{e.remove();}});'
            # \\newpage 等の改ページ指示を、次のページの先頭まで送る詰め物にする。
            # 前の詰め物が後ろの位置をずらすので、一度 0 に戻してから
            # 上から順に高さを決め直す。
            f'var nps=w.querySelectorAll(".mdv-newpage");'
            f'nps.forEach(function(e){{e.style.height="0px";}});'
            f'nps.forEach(function(e){{'
            f'var y=e.offsetTop;'
            f'var rem=y%pgH;'
            f'e.style.height=(rem<1?0:Math.round(pgH-rem))+"px";'
            f'}});'
            f'var tot=Math.max(w.scrollHeight,w.offsetHeight);'
            f'if(tot<pgH)return;'
            f'var n=Math.ceil(tot/pgH);'
            f'for(var i=1;i<n;i++){{'
            f'var d=document.createElement("div");'
            f'd.className="pg-brk";'
            f'd.style.cssText="position:absolute;top:"+Math.round(i*pgH)+"px;'
            f'left:-8px;right:-8px;height:0;pointer-events:none;z-index:200;'
            f'border-top:2px dashed rgba(100,140,255,0.55);";'
            f'var s=document.createElement("span");'
            f's.style.cssText="position:absolute;right:6px;top:-11px;'
            f'font-size:10px;font-family:system-ui,sans-serif;font-weight:normal;'
            f'color:rgba(70,110,210,0.9);'
            f'background:rgba(200,215,255,0.25);'
            f'border:1px solid rgba(100,140,255,0.35);'
            f'padding:0 6px;border-radius:8px;white-space:nowrap;";'
            f's.textContent={_pg_prefix}+(i+1)+{_pg_suffix};'
            f'd.appendChild(s);w.appendChild(d);'
            f'}}}}'
            f'upd();'
            f'if(window.ResizeObserver){{new ResizeObserver(upd).observe(w);}}'
            f'}});'
            f'</script>'
        )

    @staticmethod
    def _render_checklist(html):
        html = re.sub(
            r'<li>\s*\[ \]\s*',
            '<li class="task-list-item"><input type="checkbox" disabled> ',
            html,
        )
        html = re.sub(
            r'<li>\s*\[x\]\s*',
            '<li class="task-list-item"><input type="checkbox" checked disabled> ',
            html,
            flags=re.IGNORECASE,
        )
        return html

    def _embed_remote_images(self, html: str) -> str:
        def replace_src(m):
            url = m.group(1)
            if url in self._image_cache:
                return f'<img src="{self._image_cache[url]}"'
            return m.group(0)
        return re.sub(r'<img\s+src="(https?://[^"]+)"', replace_src, html)

    # ════════════════════════════════════════════
    #  TXT編集: プレビュー行同期 (編集中の行をプレビューでハイライト/自動スクロール)
    # ════════════════════════════════════════════
    @staticmethod
    def _split_source_blocks(text):
        """空行区切りでソースをおおよそのMarkdownブロック単位に分割し、
        各ブロックの開始行番号 (0-indexed) の一覧を返す。
        markdown.markdown() が生成する `.wrap` 直下のトップレベル要素の並び順と
        概ね対応するため、行番号 ⇔ DOM要素の近似マッピングに使う。"""
        lines = text.split('\n')
        n = len(lines)
        starts = []
        i = 0
        while i < n:
            if lines[i].strip() == '':
                i += 1
                continue
            start = i
            fence_m = re.match(r'^\s{0,3}(```+|~~~+)', lines[i])
            if fence_m:
                fence = fence_m.group(1)[0] * 3
                i += 1
                while i < n and fence not in lines[i]:
                    i += 1
                i = min(i + 1, n)
                starts.append(start)
                continue
            is_list = bool(_LIST_ITEM_RE.match(lines[i]))
            while i < n and lines[i].strip() != '':
                i += 1
            # 空行を挟んでも次がリスト項目なら同一ブロック(loose list)として扱う。
            # インデントされた継続行はここではリストに併合しない (実際の
            # markdown パーサーの継続判定はインデント幅次第で分かれるため、
            # 誤って併合するより素直に別ブロック扱いにした方がずれが小さい)。
            while is_list and i < n:
                j = i
                while j < n and lines[j].strip() == '':
                    j += 1
                if j < n and _LIST_ITEM_RE.match(lines[j]):
                    i = j
                    while i < n and lines[i].strip() != '':
                        i += 1
                else:
                    break
            starts.append(start)
        return starts

    @staticmethod
    def _tag_src_lines(body: str, block_starts: List[int]) -> str:
        """body内のトップレベル要素それぞれに data-src-line 属性を付与する。"""
        if not block_starts:
            return body
        lines = body.split('\n')
        line_offsets = [0] * (len(lines) + 1)
        off = 0
        for i, ln in enumerate(lines):
            off += len(ln) + 1
            line_offsets[i + 1] = off

        state = {"depth": 0, "block_idx": 0}
        inserts = []

        class _Tagger(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if state["depth"] == 0 and state["block_idx"] < len(block_starts):
                    line, col = self.getpos()
                    insert_at = line_offsets[line - 1] + col + 1 + len(tag)
                    inserts.append(
                        (insert_at, f' data-src-line="{block_starts[state["block_idx"]]}"')
                    )
                    state["block_idx"] += 1
                state["depth"] += 1

            def handle_startendtag(self, tag, attrs):
                self.handle_starttag(tag, attrs)
                state["depth"] -= 1

            def handle_endtag(self, tag):
                state["depth"] = max(0, state["depth"] - 1)

        try:
            parser = _Tagger()
            parser.feed(body)
        except Exception:
            return body
        result = body
        for ins_off, ins_text in sorted(inserts, key=lambda x: -x[0]):
            result = result[:ins_off] + ins_text + result[ins_off:]
        return result

    @staticmethod
    def _line_sync_js():
        return (
            '<script>'
            'window._mdvHighlightLine=function(line){'
            'var wrap=document.querySelector(".wrap");'
            'if(!wrap)return;'
            'var els=wrap.querySelectorAll("[data-src-line]");'
            'var target=null;'
            'for(var i=0;i<els.length;i++){'
            'var ln=parseInt(els[i].getAttribute("data-src-line"),10);'
            'if(ln<=line){target=els[i];}else{break;}'
            '}'
            'var prev=wrap.querySelector(".mdv-line-hl");'
            'if(prev)prev.classList.remove("mdv-line-hl");'
            'if(target){'
            'target.classList.add("mdv-line-hl");'
            'var r=target.getBoundingClientRect();'
            'if(r.top<0||r.bottom>window.innerHeight){'
            'target.scrollIntoView({behavior:"smooth",block:"center"});'
            '}'
            '}'
            '};'
            '</script>'
        )

    def _mermaid_html(self, mermaid_store):
        """mermaid.js 本体とダイアグラム描画を行う <script> を返す。

        mermaid_store が空 (ダイアグラムなし、または編集モード) なら何も
        返さない — 通常ドキュメントの表示コストに影響しないため。"""
        if not mermaid_store:
            return ""
        src = _mermaid_js_source()
        if not src:
            return ""
        p = self._palette
        dark = _hex_is_dark(p.get("bg2", p.get("bg", "#ffffff")))
        cfg = json.dumps({
            "startOnLoad": False,
            "securityLevel": "strict",
            "theme": "dark" if dark else "default",
            "themeVariables": {
                "background":         p["bg2"],
                "primaryColor":       p["bg3"],
                "primaryTextColor":   p["text"],
                "primaryBorderColor": p["border"],
                "lineColor":          p["text_dim"],
                "textColor":          p["text"],
                "fontFamily":         "Menlo, Monaco, monospace",
            },
        })
        return (
            f'<script>{src}</script>'
            '<script>'
            'window._mdvMermaidReady=false;'
            f'try{{mermaid.initialize({cfg});}}catch(e){{}}'
            'window.addEventListener("load",function(){'
            'try{'
            'mermaid.run({querySelector:".wrap pre.mermaid"})'
            '.then(function(){window._mdvMermaidReady=true;})'
            '.catch(function(){window._mdvMermaidReady=true;});'
            '}catch(e){window._mdvMermaidReady=true;}'
            '});'
            '</script>'
        )

    def _build_md_html(self, text, editable=False, strip_images=False, sync_lines=False):
        p   = self._palette
        fs  = int(16 * SCALE_STEPS[self.scale_idx])
        # 編集モードでは codehilite を使わず fenced_code のみ使用する。
        # codehilite はコードを色付き <span> に変換して言語情報を失わせるため、
        # ビジュアル編集→Markdown 逆変換で言語指定 (```python 等) が壊れる。
        # fenced_code は <code class="language-xxx"> を出力し _HTML2MD が言語を復元できる。
        # nl2br は既定でオン: 素の Markdown 仕様では単一の改行が段落内で連結されて
        # しまい、エディタで Enter を押して作った改行が閲覧・HTML/PDF 書き出しで
        # 消える (v1.4.1 の不具合)。<br> は _HTML2MD が改行として復元するため
        # 往復も保たれる。素の Markdown の挙動が要る文書のために、詳細設定
        # (hard_breaks) でオフにできる。
        if editable:
            _exts = ["tables", "fenced_code"]
            _cfg = {}
        else:
            _exts = ["tables", "fenced_code", "codehilite"]
            _cfg = {"codehilite": {"guess_lang": False, "noclasses": True}}
        if self.hard_breaks:
            _exts.append("nl2br")

        # ── YAML ドキュメントは全文を yaml コードブロックとして描画する ──
        if self.doc_kind == "yaml":
            fm_text, md_text, body_line_off = None, "```yaml\n" + text + "\n```", 0
        else:
            # ── YAML フロントマターを本文から切り離す ──
            #    (切り離さないと `---` が水平線、`key: value` が段落として
            #     描画されてしまい、目次の Setext 見出し判定も誤作動する)
            fm_text, md_text, body_line_off = _split_front_matter(text)

        # ── mermaid ダイアグラムを退避 (プレビュー限定。編集モードでは
        #    他言語同様、生フェンスのまま編集させるため抽出しない)。
        #    md_text 自体は書き換えない ( _split_source_blocks(md_text) の
        #    行番号がずれ、TXT編集モードの行ハイライトが壊れるため)。──
        if editable:
            mermaid_store = []
            md_source = md_text
        else:
            md_source, mermaid_store = _extract_mermaid(md_text)
        # ── LaTeX 数式を退避 (Markdown が `_`/`\` を書き換えるのを防ぐ) ──
        md_source, math_store = _extract_math(md_source)
        # ── \newpage 等の体裁コマンドを退避 (数式の後。数式の中身は
        #    既にプレースホルダに逃げているので巻き込まない) ──
        md_source, layout_store = _extract_tex_layout(md_source)

        try:
            body = markdown.markdown(md_source, extensions=_exts, extension_configs=_cfg)
        except Exception:
            try:
                body = markdown.markdown(
                    md_source,
                    extensions=["tables", "fenced_code"]
                               + (["nl2br"] if self.hard_breaks else []))
            except Exception:
                body = markdown.markdown(md_source)
        # Markdown 由来の生 HTML/JavaScript を無害化 (信頼済みの自前スクリプト/CSS は
        # この body の外側で付加されるためサニタイズ対象外)。
        body = _sanitize_html(body)
        body = self._render_checklist(body)
        # 数式 HTML はサニタイズ後に差し込む (自前生成なので無害化の対象外。
        # 先に差し込むと <span> の属性やクラスが落とされてしまう)。
        body = _restore_math(body, math_store)
        body = _restore_tex_layout(body, layout_store)
        body = _restore_mermaid(body, mermaid_store)
        body = self._embed_remote_images(body)
        if strip_images:
            body = re.sub(r'<img[^>]*>', '', body)

        # ── 行 ⇔ 表示要素の対応付け ──
        #    TXT編集の行ハイライトに加え、モード切替時のスクロール位置の
        #    引き継ぎ (_capture_scroll_anchor / _restore_scroll_anchor) でも使うため
        #    全モードで付与する。
        if fm_text is not None:
            body = _front_matter_html(fm_text, self._t("front_matter")) + body
        try:
            starts = [s + body_line_off
                      for s in self._split_source_blocks(md_text)]
            if fm_text is not None:
                starts.insert(0, 0)   # フロントマターのパネルは 0 行目に対応
            body = self._tag_src_lines(body, starts)
        except Exception:
            pass

        # 印刷/PDF 時の体裁コマンド。画面用に入れた高さ (次ページ送りの
        # 詰め物・編集用の目印) は捨てて、ブラウザ本来の改ページに任せる。
        _pg_print = (
            ".mdv-newpage{height:0!important;min-height:0!important;"
            "margin:0!important;padding:0!important;border:0!important;"
            "opacity:1!important;"
            "break-after:page!important;page-break-after:always!important;}"
            ".mdv-newpage::after{content:none!important;display:none!important;}"
            ".mdv-texcmd{outline:none!important;}"
            # 印刷時の体裁: 背景の有無を画面表示どおりに保ち、
            # 表・コード・図・数式・引用が見開きで切断されにくくする。
            "*{print-color-adjust:exact!important;"
            "-webkit-print-color-adjust:exact!important;}"
            "thead{display:table-header-group;}"
            "tr{break-inside:avoid;page-break-inside:avoid;}"
            "pre,blockquote,figure,table,"
            ".mdv-math-display,pre.mermaid,.mdv-fm"
            "{break-inside:avoid;page-break-inside:avoid;}"
            "h1,h2,h3,h4,h5,h6{break-after:avoid;page-break-after:avoid;}"
        )

        if self.page_mode == "a4":
            t, r, b, l = self.a4_margins
            page_h, page_w, page_css_name = 297, 210, "A4"
            wrap = (
                f"max-width:{page_w}mm;margin:24px auto;background:{p['bg2']};"
                f"padding:{t}mm {r}mm {b}mm {l}mm;"
                f"box-shadow:0 2px 20px rgba(0,0,0,.4);min-height:{page_h}mm;"
            )
            # PDF印刷時: 余白(body背景)と本文エリアを同色に統一
            print_css = (
                f"@media print{{"
                # 余白は printToPdf() に渡す QPageLayout (ユーザー設定値) が管理する。
                # CSS 側 @page でも余白を指定すると二重適用の恐れがあるため 0 にする。
                f"@page{{size:{page_css_name} portrait;margin:0;}}"
                f"body{{margin:0!important;background:{p['bg']}!important;}}"
                f".wrap{{max-width:100%!important;margin:0!important;"
                f"padding:0!important;box-shadow:none!important;"
                f"min-height:auto!important;background:{p['bg']}!important;}}"
                f".pg-brk{{display:none!important;}}"
                + _pg_print +
                f"}}"
            )
            pg_js = self._page_break_js(page_h)
        elif self.page_mode == "b5":
            t, r, b, l = self.b5_margins
            page_h, page_w = 257, 182
            wrap = (
                f"max-width:{page_w}mm;margin:24px auto;background:{p['bg2']};"
                f"padding:{t}mm {r}mm {b}mm {l}mm;"
                f"box-shadow:0 2px 20px rgba(0,0,0,.4);min-height:{page_h}mm;"
            )
            print_css = (
                f"@media print{{"
                # 余白は QPageLayout が管理 (CSS 側は 0 にして二重適用を防ぐ)
                f"@page{{size:{page_w}mm {page_h}mm portrait;margin:0;}}"
                f"body{{margin:0!important;background:{p['bg']}!important;}}"
                f".wrap{{max-width:100%!important;margin:0!important;"
                f"padding:0!important;box-shadow:none!important;"
                f"min-height:auto!important;background:{p['bg']}!important;}}"
                f".pg-brk{{display:none!important;}}"
                + _pg_print +
                f"}}"
            )
            pg_js = self._page_break_js(page_h)
        else:
            # width:100% でビューポート幅に追従させ、max-width:920px で
            # 上限を抑える。中央寄せの両側は地色になるが、行内容が幅を
            # 押し広げて右側へ広い空白と水平スクロールが出ることはない。
            wrap = "padding:32px 48px;max-width:920px;width:100%;margin:0 auto;"
            print_css = (
                # 余白は QPageLayout が管理 (CSS 側は 0 にして二重適用を防ぐ)
                f"@media print{{@page{{margin:0;}}"
                f"body{{background:{p['bg']}!important;}}"
                f".wrap{{background:{p['bg']}!important;}}"
                + _pg_print +
                f"}}"
            )
            pg_js = ""

        editable_css = ""
        if editable:
            editable_css = (
                f".wrap[contenteditable]{{cursor:text;caret-color:{p['accent']}}}"
                ".wrap[contenteditable]:focus{outline:none}"
                ".mdv-copy-btn{display:none}"
            )

        sync_css = ""
        if sync_lines and not editable:
            sync_css = (
                ".mdv-line-hl{background:rgba(255,60,60,.16)!important;"
                "transition:background .15s;border-radius:3px;}"
            )

        # 体裁コマンドの CSS は print_css より前に置く。改ページの
        # break-after は print 側で上書きする必要があるため。
        css = (self._css(fs) + f".wrap{{{wrap}}}" + self._tex_layout_css()
               + editable_css + sync_css + print_css)

        wrap_attrs = ' contenteditable="true" spellcheck="false"' if editable else ""

        # 全モードでクリップボードブリッジを初期化。編集モード時はコンテンツブリッジも初期化
        _ch_content = ""
        if editable:
            _ch_content = (
                # Enter で <div> ではなく <p> を生成させ、段落境界の解釈を
                # HTML→Markdown 変換側 (<p>/<div> どちらも \n\n) と揃える。
                'try{document.execCommand("defaultParagraphSeparator",false,"p");}catch(e){}'
                'var br=ch.objects.bridge;'
                'var w=document.querySelector(".wrap");'
                'if(w){'
                # タイマーは window に持たせる。保存や書き出しの直前に
                # Python 側 (_JS_GRAB_WRAP) から解除して、取り込んだ後に
                # 古い内容が遅れて届くのを防ぐため。
                'window._mdvTmr=null;window._mdvDirty=false;'
                'w.addEventListener("input",function(){'
                'window._mdvDirty=true;'
                'clearTimeout(window._mdvTmr);'
                'window._mdvTmr=setTimeout('
                'function(){br.contentChanged(w.innerHTML);},400);'
                '});}'
            )
        webchannel_js = (
            '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'
            '<script>'
            'var _mdvClipboard=null;'
            'document.addEventListener("DOMContentLoaded",function(){'
            'if(typeof QWebChannel==="undefined"||typeof qt==="undefined")return;'
            'new QWebChannel(qt.webChannelTransport,function(ch){'
            '_mdvClipboard=ch.objects.clipboard;'
            + _ch_content +
            '});});'
            '</script>'
        )

        # 閲覧モードのみプレビュー内オーバーレイのTOCを使う。
        # TXT編集モード (sync_lines) や MD編集モード (editable) は
        # 左側のネイティブTOCパネル (_toc_panel) を使うため重複表示しない。
        toc_js = self._toc_js() if (self._show_toc and not editable and not sync_lines) else ""
        sync_js = self._line_sync_js() if (sync_lines and not editable) else ""
        return (
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<style>{css}</style></head>'
            f'<body><div class="wrap"{wrap_attrs}>{body}</div>'
            f'{pg_js}'
            f'{self._copy_code_btn_js()}'
            f'{(self._md_edit_fmt_js() if editable else "")}'
            f'{sync_js}'
            f'{webchannel_js}'
            f'{self._copy_plain_js()}'
            f'{toc_js}'
            f'{self._mermaid_html(mermaid_store)}'
            '</body></html>'
        )

    def _html_to_markdown(self, html_content: str) -> str:
        processed = html_content
        for url, data_uri in self._image_cache.items():
            processed = processed.replace(data_uri, url)
        # 改行設定に合わせて <br> を復元する。nl2br オフ時は行末の
        # 半角スペース 2 個へ戻す (素の Markdown として有効な明示改行)。
        return _html_to_md(processed, hard_breaks=self.hard_breaks)

    # ════════════════════════════════════════════
    #  テーマ適用
    # ════════════════════════════════════════════
    def _resolve_palette(self) -> dict:
        """current_theme に対応するパレットを返す"""
        if self.current_theme == "dark":
            return DARK_PALETTE
        elif self.current_theme == "light":
            return LIGHT_PALETTE
        elif self.current_theme in self._plugin_themes:
            return self._plugin_themes[self.current_theme]
        return DARK_PALETTE

    def _apply_theme(self, refresh=True):
        p = self._resolve_palette()
        self._palette = p
        scale = SCALE_STEPS[self.scale_idx]
        ed_fs = int(18 * scale)
        ff    = (f"'{self.ui_font_family}', monospace"
                 if self.ui_font_family else "monospace")
        fw_editor = "600" if self.bold_mode else "normal"

        editor_ss = (
            f"QPlainTextEdit{{"
            f"background-color:{p['bg']};color:{p['text']};"
            f"font-family:{ff};font-size:{ed_fs}px;font-weight:{fw_editor};"
            f"border:none;"
            f"selection-background-color:{p['select']};}}"
        )

        sz = self._ui_sizes()
        tb_fs   = sz["tb_fs"]
        btn_pad = f"0 {sz['btn_pad']}px"
        fmt_fs  = sz["fmt_fs"]
        fmt_pad = f"0 {sz['fmt_pad']}px"
        lbl_fs  = sz["lbl_fs"]
        min_w   = sz["min_w"]

        app_ss = (
            f"QMainWindow,QWidget{{background-color:{p['bg']};color:{p['text']};"
            f"font-weight:bold;font-size:{tb_fs}px;}}"
            f"QWidget#mainTB{{background-color:{p['toolbar']};"
            f"border-bottom:1px solid {p['sep']};}}"
            f"QPushButton#mainBtn{{background-color:{p['btn']};color:{p['text']};"
            f"border:none;border-radius:0;padding:{btn_pad};"
            f"font-size:{tb_fs}px;font-weight:bold;min-width:{min_w}px;}}"
            f"QPushButton#mainBtn:hover{{background-color:{p['btn_hover']};}}"
            f"QPushButton#mainBtn[active=true]{{background-color:{p['btn_active_bg']};"
            f"color:{p['btn_active_fg']};}}"
            f"QPushButton#mainBtn:disabled{{color:{p['text_dim']};"
            f"background-color:{p['btn']};}}"
            f"QLabel#tbLabel{{color:{p['text']};font-size:{lbl_fs}px;font-weight:bold;"
            f"padding:0 6px;background-color:{p['toolbar']};border:none;}}"
            f"QSlider#scaleSlider{{background:transparent;}}"
            f"QSlider#scaleSlider::groove:horizontal{{height:3px;"
            f"background:{p['sep']};border-radius:2px;}}"
            f"QSlider#scaleSlider::handle:horizontal{{background:{p['text']};"
            f"width:13px;height:13px;margin:-5px 0;border-radius:7px;border:none;}}"
            f"QWidget#fmtTB{{background-color:{p['bg2']};"
            f"border-bottom:1px solid {p['sep']};}}"
            f"QPushButton#fmtBtn{{background-color:{p['bg2']};color:{p['text']};"
            f"border:none;border-radius:0;padding:{fmt_pad};"
            f"font-size:{fmt_fs}px;font-weight:bold;min-width:{min_w-14}px;}}"
            f"QPushButton#fmtBtn:hover{{background-color:{p['accent']};color:#ffffff;}}"
            f"QWidget#vSep{{background-color:{p['sep']};border:none;}}"
            f"QMenuBar{{background-color:{p['toolbar']};color:{p['text']};"
            f"border-bottom:1px solid {p['sep']};font-weight:bold;font-size:{lbl_fs+1}px;}}"
            f"QMenuBar::item{{background:transparent;padding:4px 10px;}}"
            f"QMenuBar::item:selected{{background-color:{p['btn_hover']};}}"
            f"QMenu{{background-color:{p['bg2']};color:{p['text']};"
            f"border:1px solid {p['sep']};font-weight:bold;font-size:{lbl_fs+1}px;}}"
            f"QMenu::item{{padding:6px 20px;}}"
            f"QMenu::item:selected{{background-color:{p['select']};}}"
            f"QMenu::separator{{height:1px;background:{p['sep']};margin:4px 0;}}"
            f"QScrollBar:vertical{{background:{p['bg']};width:7px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{p['sep']};border-radius:3px;"
            f"min-height:20px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"
            f"QScrollBar:horizontal{{background:{p['bg']};height:7px;border:none;}}"
            f"QScrollBar::handle:horizontal{{background:{p['sep']};border-radius:3px;}}"
            f"QScrollBar::add-line:horizontal,"
            f"QScrollBar::sub-line:horizontal{{width:0;}}"
            f"QSplitter::handle{{background-color:{p['sep']};border:none;}}"
            f"QWidget#tocPanel{{background-color:{p['bg2']};"
            f"border-right:1px solid {p['sep']};}}"
            f"QLabel#tocTitle{{color:{p['heading']};"
            f"font-size:{self._toc_base_font_px()}px;"
            f"font-weight:bold;padding:10px 12px 8px 12px;"
            f"border-bottom:1px solid {p['sep']};background:transparent;}}"
            # font-size はウィジェット側にだけ指定する。::item に書くと
            # 見出しレベルごとに setFont() で付けた大きさを打ち消してしまう。
            f"QListWidget#tocList{{background-color:{p['bg2']};color:{p['text']};"
            f"border:none;outline:none;padding:4px 0;font-size:16px;}}"
            f"QListWidget#tocList::item{{padding:5px 12px;border-radius:3px;"
            f"margin:1px 6px;}}"
            f"QListWidget#tocList::item:hover{{background-color:{p['btn_hover']};"
            f"color:{p['accent']};}}"
            f"QListWidget#tocList::item:selected{{background-color:{p['select']};"
            f"color:{p['text']};}}"
            f"QDialog{{background-color:{p['bg2']};color:{p['text']};}}"
            f"QGroupBox{{border:1px solid {p['sep']};border-radius:4px;"
            f"margin-top:8px;padding-top:8px;font-weight:bold;font-size:{lbl_fs}px;}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}"
            f"QSpinBox,QComboBox,QFontComboBox{{background-color:{p['btn']};"
            f"color:{p['text']};border:1px solid {p['sep']};border-radius:4px;"
            f"padding:4px 8px;font-size:{lbl_fs}px;font-weight:bold;}}"
            f"QComboBox::drop-down{{border:none;}}"
            f"QComboBox QAbstractItemView{{background-color:{p['bg2']};color:{p['text']};"
            f"border:1px solid {p['sep']};selection-background-color:{p['select']};}}"
            f"QLabel{{font-weight:bold;font-size:{lbl_fs}px;background:transparent;border:none;}}"
            f"QLabel#fontHint{{color:{p['text_dim']};font-weight:normal;"
            f"font-size:{max(10, lbl_fs - 2)}px;padding-top:4px;}}"
            f"QCheckBox{{font-size:{lbl_fs}px;font-weight:bold;color:{p['text']};}}"
            f"QDialogButtonBox QPushButton{{background-color:{p['btn']};color:{p['text']};"
            f"border:1px solid {p['sep']};border-radius:4px;padding:6px 20px;"
            f"font-weight:bold;font-size:{lbl_fs}px;min-width:70px;}}"
            f"QDialogButtonBox QPushButton:hover{{background-color:{p['accent']};"
            f"color:#ffffff;border-color:{p['accent']};}}"
        )

        self.setStyleSheet(app_ss)
        self._md_editor.setStyleSheet(editor_ss)
        # padding:14px の代わりに document margin を使う（| 文字の座標ズレを防ぐ）
        self._md_editor.document().setDocumentMargin(16)
        # スケールスライダ周りも幅の段階に合わせて詰める
        # (これを固定のままにすると狭いウィンドウでボタンを押し出してしまう)
        self._scale_slider.setFixedWidth(sz["slider_w"])
        self._scale_val_lbl.setFixedWidth(sz["val_w"])
        # 最も狭い段階では「スケール」の見出しを畳む。スライダーと
        # パーセント表示だけで意味が通り、その分をボタンに回せる。
        self._scale_lbl.setVisible(self._get_ui_scale_cat() != "xsmall")
        self._apply_btn_fit_metrics(sz)
        if hasattr(self, "_loader"):
            self._loader.set_background(p["bg"])
        self._sync_tb_labels()
        self._refresh_btn_states()
        if refresh:
            # 言語 / テーマ / フォント / 文字サイズの変更による描き直し。
            # MD編集中なら先に編集内容を取り込む (取り込まないと、直前に
            # 入れた改行や見出しが描き直しで消える)。
            self._refresh_view_keeping_edits()

    def _sync_tb_labels(self):
        self._back_btn.setText(self._t("back"))
        for k, tk in [("view","view"), ("md","md_edit"), ("txt","txt_edit")]:
            self._mode_btns[k].setText(self._t(tk))
        for k, tk in [("free","free"), ("a4","a4"), ("b5","b5")]:
            self._layout_btns[k].setText(self._t(tk))
        self._margin_btn.setText(self._t("margin"))
        self._scale_lbl.setText(self._t("scale"))
        self._scale_val_lbl.setText(SCALE_LABELS[self.scale_idx])
        self._settings_btn.setText(self._t("settings"))
        self._toc_btn.setText(self._t("toc"))
        self._pdf_btn.setText(self._t("pdf_export"))
        self._toc_title_lbl.setText(self._t("toc_title"))
        if self._toc_panel.isVisible():
            self._rebuild_toc_list()

    def _mode_available(self, mode):
        """そのモードに切り替えられるか。

        読み取り専用ファイルは編集不可。YAML ドキュメントは Markdown の
        リッチテキスト編集 (MD編集) が意味を持たないため TXT編集のみとする。"""
        if self._readonly_file and mode in ("md", "txt"):
            return False
        if self.doc_kind == "yaml" and mode == "md":
            return False
        return True

    def _refresh_btn_states(self):
        for k, b in self._mode_btns.items():
            b.set_active(k == self.edit_mode)
            b.setEnabled(self._mode_available(k))
        for k, b in self._layout_btns.items():
            b.set_active(k == self.page_mode)
        self._back_btn.setEnabled(self.edit_mode != "view")
        self._margin_btn.setEnabled(self.page_mode in ("a4", "b5"))
        self._scale_val_lbl.setText(SCALE_LABELS[self.scale_idx])
        self._toc_btn.set_active(self._show_toc)

    # ════════════════════════════════════════════
    #  表示更新
    # ════════════════════════════════════════════
    def _refresh_view(self):
        if self._toc_panel.isVisible():
            self._rebuild_toc_list()
        text = self._content_text
        editable = (self.edit_mode == "md")
        sync_lines = (self.edit_mode == "txt")
        html = self._build_md_html(text, editable=editable, sync_lines=sync_lines)
        base_path = None
        if self.current_file_path:
            base_path = os.path.dirname(os.path.abspath(self.current_file_path)) + os.sep
        self._loader.load_html(html, base_path)

    def _on_editor_changed(self):
        if self.edit_mode != "txt":
            return
        self._content_text = self._md_editor.toPlainText()
        # 編集中のネットワークアクセスはしない。リモート画像はファイルを開く時に
        # ユーザー確認のうえで取得する (_check_and_fetch_images_for_file)。
        self.is_modified = True
        self._update_title()
        self._timer.start()

    def _on_md_content_changed(self, html_content: str):
        if self.edit_mode != "md":
            return
        self._content_text = self._html_to_markdown(html_content)
        self.is_modified = True
        self._update_title()
        # MD編集モードでは _refresh_view() が走らない(プレビュー欄がそのまま
        # 編集領域のため)。見出しを増減しても目次が古いままにならないよう、
        # ここで作り直す (中身が変わっていなければ _rebuild_toc_list 側で握り潰す)。
        if self._toc_panel.isVisible():
            self._rebuild_toc_list()

    def _refresh_view_keeping_edits(self):
        """表示設定を変えたときの再描画。

        MD編集モードでは画面がそのまま編集領域なので、_refresh_view() は
        いま編集している内容を _content_text から作り直して丸ごと置き換える。
        取り込みが済んでいない編集 (改行や見出し) はそこで消えてしまうため、
        描き直す前に必ず取り込む。
        ※ 別の文書を読み込んだ直後など「中身を入れ替える」再描画では、
           古い画面から取り込んでしまうので使ってはいけない。"""
        if self.edit_mode == "md":
            if not self._save_buf():
                QMessageBox.warning(self, self._t("save_error"), self._t("capture_error"))
                return
        self._refresh_view()

    def _flush_preview(self):
        if self.edit_mode == "txt":
            self._preview_web.page().runJavaScript(
                "document.documentElement.scrollTop || document.body.scrollTop || 0;",
                self._do_flush_preserve_scroll
            )
        else:
            self._refresh_view_keeping_edits()

    def _do_flush_preserve_scroll(self, scroll_y):
        self._saved_scroll_y = int(scroll_y) if scroll_y else 0
        if self._saved_scroll_y > 0:
            try:
                self._preview_web.loadFinished.disconnect(self._restore_scroll_after_flush)
            except Exception:
                pass
            self._restore_scroll_pending = True
            self._preview_web.loadFinished.connect(self._restore_scroll_after_flush)
        self._refresh_view()

    def _restore_scroll_after_flush(self, ok):
        try:
            self._preview_web.loadFinished.disconnect(self._restore_scroll_after_flush)
        except Exception:
            pass
        if self._restore_scroll_pending and self._saved_scroll_y > 0:
            self._restore_scroll_pending = False
            self._preview_web.page().runJavaScript(
                f"window.scrollTo(0, {self._saved_scroll_y});"
            )

    # ════════════════════════════════════════════
    #  画像フェッチ
    # ════════════════════════════════════════════
    def _fetch_remote_images(self, urls: List[str]):
        """リモート画像をバックグラウンドで取得する (非同期・UI を固めない)。"""
        new_urls = [u for u in urls if u not in self._image_cache]
        if not new_urls:
            return
        prev = getattr(self, "_img_worker", None)
        if prev is not None and prev.isRunning():
            prev.cancel()
        worker = ImageFetchWorker(new_urls, self)
        self._img_worker = worker
        worker.fetched.connect(self._on_images_fetched)
        worker.start()

    def _on_images_fetched(self, results: dict):
        if results:
            self._image_cache.update(results)
            self._refresh_view_keeping_edits()

    def _check_and_fetch_images_for_file(self, text: str):
        all_urls = _extract_remote_image_urls(text)
        new_urls = [u for u in all_urls if u not in self._image_cache]
        if not new_urls:
            return
        reply = QMessageBox.question(
            self,
            self._t("img_confirm_title"),
            self._t("img_confirm_msg").format(n=len(new_urls)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._fetch_remote_images(new_urls)

    # ════════════════════════════════════════════
    #  モード切替
    # ════════════════════════════════════════════
    # ─── モード切替時のスクロール位置の引き継ぎ ─────────────
    #  すべての表示要素には data-src-line (元テキストの行番号) が付いている。
    #  「画面最上部に見えている要素の行番号 + その要素内での位置の割合」を
    #  アンカーとして持ち回ることで、閲覧 ⇔ MD編集 ⇔ TXT編集 のどの向きの
    #  切替でも、今見ている場所をほぼそのまま引き継げる。

    _JS_CAPTURE_ANCHOR = (
        "(function(){"
        "var w=document.querySelector('.wrap');if(!w)return '';"
        "var els=w.querySelectorAll('[data-src-line]');"
        "var best=null,br=null;"
        "for(var i=0;i<els.length;i++){"
        "var r=els[i].getBoundingClientRect();"
        "if(r.bottom>0){best=els[i];br=r;break;}}"
        "if(!best)return '';"
        "var f=br.height>0?Math.max(0,Math.min(1,(-br.top)/br.height)):0;"
        "return (parseInt(best.getAttribute('data-src-line'),10)||0)+':'+f.toFixed(4);"
        "})()"
    )

    # MD編集モードの編集内容 (.wrap の中身) を取り出す JS。
    # エディタが差し込む制御要素は Markdown に残さないよう複製から除く。
    # 保留中の反映タイマーもここで解除し、取り込んだ後に古い内容が
    # 遅れて届いて上書きされないようにする。
    _JS_GRAB_WRAP = (
        "(function(){"
        "try{clearTimeout(window._mdvTmr);}catch(e){}"
        "var w=document.querySelector('.wrap');if(!w)return null;"
        "var c=w.cloneNode(true);"
        "c.querySelectorAll('.mdv-copy-btn,.pg-brk,.mdv-table-ctrl')"
        ".forEach(function(el){el.remove();});"
        "return JSON.stringify({html:c.innerHTML,dirty:window._mdvDirty===true});})()"
    )

    def _flush_md_buf(self) -> str:
        """MD編集モードの編集内容を _content_text に取り込む (同期)。

        ブラウザ側からの通知は入力が途切れて 400ms 後に届く。保存や
        書き出しがその前に走ると、直前の編集 (Enter で入れた改行など) が
        ファイルに入らないまま書かれてしまう。閉じるときの確認も
        「変更なし」と誤判定して黙って捨ててしまう。ここで待ち合わせる。

        戻り値: "ok" (取得・反映成功) / "empty" (画面が空 = 有効な空文書)
        / "failed" (タイムアウト等で取得できず、現在値を維持すべき失敗)。
        空文書と取得失敗を区別しないと、全消しの編集が保存されなかったり
        逆にタイムアウトで既存内容が壊れたりする。"""
        web = getattr(self, "_preview_web", None)
        if web is None or self._md_flushing:
            return "failed"
        self._md_flushing = True
        box, loop = {}, QEventLoop()

        def done(html):
            box["html"] = html
            loop.quit()

        guard = QTimer(self)
        guard.setSingleShot(True)
        guard.timeout.connect(loop.quit)
        try:
            web.page().runJavaScript(self._JS_GRAB_WRAP, done)
            guard.start(self._MD_FLUSH_TIMEOUT_MS)
            loop.exec()
        finally:
            guard.stop()
            self._md_flushing = False
        if "html" not in box or not isinstance(box["html"], str):
            # タイムアウト: 取得失敗。画面の内容で置き換えず現状を維持する
            return "failed"
        try:
            snapshot = json.loads(box["html"])
        except (ValueError, TypeError):
            return "failed"
        if not isinstance(snapshot, dict):
            return "failed"
        if not snapshot.get("dirty"):
            return "ok"  # rendered HTML is not a lossless representation of the source
        html = snapshot.get("html")
        if not isinstance(html, str):
            return "failed"
        # "" は JS が .wrap を見つけられなかった場合と空文書の両方で返る。
        # 空文書のときは DOM 上も空 (<p><br></p> 等が無い) なので、
        # 逆変換結果が空でもこれは「有効な空」として反映してよい。
        text = self._html_to_markdown(html) if html else ""
        if text != self._content_text:
            self._content_text = text
            self.is_modified = True
            self._update_title()
        return "ok"

    # 取り込みの待ち時間の上限 (描画側が応答しなくても固まらないための保険)
    _MD_FLUSH_TIMEOUT_MS = 2000

    @staticmethod
    def _js_restore_anchor(line, frac):
        return (
            "(function(){"
            "var w=document.querySelector('.wrap');if(!w)return;"
            "var els=w.querySelectorAll('[data-src-line]');"
            "if(!els.length)return;"
            f"var line={int(line)},frac={float(frac):.4f};"
            "var t=els[0];"
            "for(var i=0;i<els.length;i++){"
            "var ln=parseInt(els[i].getAttribute('data-src-line'),10);"
            "if(ln<=line){t=els[i];}else{break;}}"
            "var r=t.getBoundingClientRect();"
            "var sy=window.pageYOffset||document.documentElement.scrollTop||0;"
            "window.scrollTo(0,Math.max(0,r.top+sy+frac*r.height));"
            "})()"
        )

    @staticmethod
    def _parse_anchor(raw):
        """JS が返す "line:frac" 文字列を (line, frac) に変換する。"""
        try:
            line_s, frac_s = str(raw).split(':')
            return int(line_s), float(frac_s)
        except Exception:
            return None

    # スクロール位置の微調整ループの上限 (病的な入力で固まらないための保険)
    _MAX_SCROLL_FIXUP = 300

    def _editor_anchor(self):
        """TXT編集モードのエディタから、最上部に見えている行を取得する。"""
        try:
            return self._md_editor.firstVisibleBlock().blockNumber(), 0.0
        except Exception:
            return None

    def _arm_anchor_restore(self):
        """次のプレビュー読み込み完了時に一度だけスクロール位置を復元する。"""
        try:
            self._preview_web.loadFinished.disconnect(self._on_load_restore_anchor)
        except Exception:
            pass
        self._preview_web.loadFinished.connect(self._on_load_restore_anchor)

    def _on_load_restore_anchor(self, ok):
        try:
            self._preview_web.loadFinished.disconnect(self._on_load_restore_anchor)
        except Exception:
            pass
        anchor = self._pending_anchor
        self._pending_anchor = None
        if not ok or anchor is None:
            return
        line, frac = anchor
        js = self._js_restore_anchor(line, frac)
        # レイアウト確定 (画像・フォントの反映) を待ってからスクロールする
        QTimer.singleShot(30, lambda: self._preview_web.page().runJavaScript(js))

    def _scroll_editor_to_anchor(self, anchor):
        """TXT編集モードのエディタを、指定行が最上部に来るようスクロールする。"""
        if anchor is None:
            return
        line, frac = anchor
        doc = self._md_editor.document()
        if doc.blockCount() == 0:
            return
        block = doc.findBlockByNumber(max(0, min(int(line), doc.blockCount() - 1)))
        if not block.isValid():
            return
        target = block.blockNumber()
        cur = QTextCursor(block)
        self._md_editor.setTextCursor(cur)
        self._md_editor.ensureCursorVisible()
        # ensureCursorVisible() は「見える所まで」しか動かさないため、
        # 対象行が最上部に来るよう残りの差分だけ追加でスクロールする。
        vs = self._md_editor.verticalScrollBar()
        lh = max(1, self._md_editor.fontMetrics().lineSpacing())
        delta = self._md_editor.cursorRect().top() // lh
        if delta:
            vs.setValue(vs.value() + int(delta))
        # スクロールバーの 1 目盛りは「表示行」で、折り返しのある行では
        # 文書の行数と一致しない。またモード切替直後はレイアウトが確定して
        # おらずピクセル換算がずれることがある。実際の先頭行を見ながら
        # 1 目盛りずつ詰めて、狙った行をきっちり最上部に持ってくる。
        for _ in range(self._MAX_SCROLL_FIXUP):
            first = self._md_editor.firstVisibleBlock().blockNumber()
            if first == target:
                break
            before = vs.value()
            vs.setValue(before + (1 if first < target else -1))
            if vs.value() == before:   # 文末/文頭でこれ以上動かせない
                break

    def _set_mode(self, mode):
        if not self._mode_available(mode):
            return
        if self.edit_mode == mode:
            return
        self._timer.stop()
        if self.edit_mode == "md":
            self._pending_mode = mode
            # コピーボタン等を除去してからinnerHTMLを取得（テーブル変換の精度向上）。
            # 同時にスクロールアンカーも取得し、往復の runJavaScript を 1 回で済ませる。
            self._preview_web.page().runJavaScript(
                "(function(){"
                "var a=" + self._JS_CAPTURE_ANCHOR + ";"
                "return JSON.stringify([a," + self._JS_GRAB_WRAP + "]);"
                "})()",
                lambda res: self._finish_mode_switch_from_md(res, mode)
            )
        elif self.edit_mode == "txt":
            self._save_buf()
            self._do_set_mode(mode, anchor=self._editor_anchor())
        else:
            self._preview_web.page().runJavaScript(
                self._JS_CAPTURE_ANCHOR,
                lambda raw: self._do_set_mode(mode, anchor=self._parse_anchor(raw))
            )

    def _finish_mode_switch_from_md(self, res, mode):
        try:
            raw, data = json.loads(res)
            snapshot = json.loads(data)
        except (ValueError, TypeError):
            QMessageBox.warning(self, self._t("save_error"), self._t("capture_error"))
            return  # never leave the editor when its contents cannot be retrieved
        if not isinstance(snapshot, dict):
            QMessageBox.warning(self, self._t("save_error"), self._t("capture_error"))
            return
        anchor = self._parse_anchor(raw)
        if snapshot.get("dirty"):
            html_content = snapshot.get("html")
            if not isinstance(html_content, str):
                QMessageBox.warning(self, self._t("save_error"), self._t("capture_error"))
                return
            text = self._html_to_markdown(html_content)
            if text != self._content_text:
                self._content_text = text
                self.is_modified = True
                self._update_title()
        self._do_set_mode(mode, anchor=anchor)

    def _do_set_mode(self, mode, anchor=None):
        self.edit_mode = mode
        self._pending_anchor = anchor
        if anchor is not None:
            self._arm_anchor_restore()
        idx = 1 if mode == "txt" else 0
        self._editor_stack.setCurrentIndex(idx)
        # 閲覧・MD編集モードではエディタ欄が空のまま残るため隠す
        # (可視のままだとスプリッターのハンドルをドラッグして空白パネルを
        # 引き出せてしまう)。
        self._editor_stack.setVisible(mode == "txt")

        # 書式ツールバーはTXT編集・MD編集モードの両方で表示
        self._fmt_container.setVisible(mode in ("txt", "md"))

        self._md_page.set_mode(mode)

        if mode == "txt":
            self._md_editor.blockSignals(True)
            self._md_editor.setPlainText(self._content_text)
            self._md_editor.blockSignals(False)

        self._update_toc_panel_visibility()
        self._update_splitter_sizes()
        self._refresh_btn_states()
        self._refresh_view()

        if mode == "txt" and anchor is not None:
            # スプリッターのサイズ確定後でないとエディタの表示行数が
            # 決まらないため、次のイベントループで位置を合わせる。
            QTimer.singleShot(0, lambda a=anchor: self._scroll_editor_to_anchor(a))

    def _toggle_toc(self):
        self._show_toc = not self._show_toc
        self._toc_btn.set_active(self._show_toc)
        self._update_toc_panel_visibility()
        self._update_splitter_sizes()
        self._save_app_settings()   # 次回起動時も同じ状態で開く
        self._refresh_view_keeping_edits()

    # ─── 見出し(TOC)パネル ─────────────────────────
    def _update_toc_panel_visibility(self):
        show = self._show_toc and self.edit_mode in ("md", "txt")
        self._toc_panel.setVisible(show)
        if show:
            self._rebuild_toc_list()

    def _toc_panel_width(self):
        """本文が最大幅まで広がった状態でウィンドウを横に広げた場合、
        目次パネルの幅もある程度追従して広がるようにする(220〜420pxの範囲)。"""
        base, grow_from, ratio, cap = 220, 900, 0.18, 420
        extra = max(0, self.width() - grow_from) * ratio
        return int(min(cap, base + extra))

    def _splitter_total_width(self):
        """setSizes() に渡す合計幅。QSplitter は渡された値の合計を実幅に
        比例スケールするため、ここが実幅より小さいと目次だけが不当に広くなる。
        レイアウト前は QSplitter が既定幅のままのことがあるので、その場合は
        ウィンドウ幅を使う (スプリッターは余白なしで全幅を占める)。"""
        w = self._splitter.width()
        win_w = max(1, self.width())
        return w if w >= win_w * 0.5 else win_w

    def _update_splitter_sizes(self):
        """モード切替・目次トグル時にスプリッターを初期配分に戻す。"""
        toc_w = (self._toc_panel_width()
                 if (self._show_toc and self.edit_mode in ("md", "txt")) else 0)
        rest = max(1, self._splitter_total_width() - toc_w)
        if self.edit_mode == "txt":
            # エディタ:プレビュー = 4:6。実ピクセルで渡すことで、目次の幅が
            # 比率に巻き込まれて _toc_panel_width() どおりにならないのを防ぐ。
            edit_w = int(rest * 0.4)
            self._splitter.setSizes([toc_w, edit_w, rest - edit_w])
        else:
            self._splitter.setSizes([toc_w, 0, rest])

    def _sync_toc_width_on_resize(self):
        """ウィンドウ幅の変化に合わせて目次の幅だけを追従させる。
        エディタ/プレビューはユーザーがドラッグした比率を保つ
        (_update_splitter_sizes をそのまま呼ぶと手動調整が毎回失われる)。"""
        if not (self._show_toc and self.edit_mode in ("md", "txt")):
            return
        sizes = self._splitter.sizes()
        if len(sizes) != 3:
            return
        toc_w = self._toc_panel_width()
        rest = max(1, self._splitter_total_width() - toc_w)
        old_rest = sizes[1] + sizes[2]
        if old_rest <= 0:
            self._update_splitter_sizes()
            return
        mid = int(rest * sizes[1] / old_rest)
        self._splitter.setSizes([toc_w, mid, rest - mid])

    @staticmethod
    def _extract_headings(text):
        """本文から見出し(ATX形式の# ... および Setext形式の下線見出し)を抽出する。
        markdown.markdown() が実際にレンダリングする見出し (先頭の空白なしATX、
        #の後にスペースがないATX、Setext見出し) と一致するように検出する。
        フェンスコードブロック内、およびブロック引用/リスト等にネストした見出しは
        対象外 (querySelectorAll('.wrap>h1,...') 側もトップレベルのみを見るため)。"""
        heads = []
        lines = text.split("\n")
        n = len(lines)

        # ── 0th pass: YAML フロントマターは走査対象から外す ──
        # 閉じの `---` を Setext 見出し(下線 `-`)と誤認して、直前の
        # `key: value` 行が見出しとして目次に紛れ込むのを防ぐ。
        # 行番号は本文と同じ絶対値のまま扱う (目次のジャンプ先に使うため)。
        _fm, _body, fm_end = _split_front_matter(text)
        skip_until = fm_end if _fm is not None else 0

        # ── 1st pass: 実際に閉じているフェンスの行範囲だけを求める ──
        # python-markdown は「行頭(インデントなし)で始まり、開始と全く同じ記号列で
        # 閉じられた」フェンスのみをコードブロックとして扱う。閉じていないフェンスや
        # インデントされたフェンスは通常の本文として解釈され、中の `# ...` は
        # 見出しとして描画される。これらを誤ってスキップすると見出しを取りこぼし、
        # TOC のジャンプ先がずれる。
        fenced = [False] * n
        i = skip_until
        while i < n:
            m_open = re.match(r'^(`{3,}|~{3,})', lines[i])
            if m_open:
                marker = m_open.group(1)
                close_re = re.compile(r'^' + re.escape(marker) + r'[ \t]*$')
                j = i + 1
                while j < n and not close_re.match(lines[j]):
                    j += 1
                if j < n:                       # 閉じている → フェンスとして扱う
                    for k in range(i, j + 1):
                        fenced[k] = True
                    i = j + 1
                    continue
            i += 1

        # ── 1.5th pass: 字下げコードブロック (4スペース/タブ) も除外する ──
        # 空行の後に 4 スペース以上下げて始まる行は、Markdown ではコードブロックに
        # なる。ここを見落とすと、コード中の `---` を下線形式の見出しと誤認して
        # 直前の行が目次に紛れ込む (段落の直後の字下げ行は継続行なので対象外)。
        i = skip_until
        prev_blank = True
        while i < n:
            if fenced[i]:
                prev_blank = False
                i += 1
                continue
            expanded = lines[i].expandtabs(4)
            if prev_blank and expanded.strip() and expanded[:4] == "    ":
                j = i
                while j < n and not fenced[j]:
                    e = lines[j].expandtabs(4)
                    if e.strip() and e[:4] != "    ":
                        break
                    fenced[j] = True
                    j += 1
                # 末尾の空行はコードブロックに含めない
                while j - 1 > i and not lines[j - 1].strip():
                    fenced[j - 1] = False
                    j -= 1
                i = j
                prev_blank = False
                continue
            prev_blank = not lines[i].strip()
            i += 1

        # ── 2nd pass: 見出しを抽出 ──
        prev_text = None
        prev_line_no = None
        i = skip_until
        while i < n:
            line = lines[i]
            stripped = line.strip()

            if fenced[i]:
                prev_text = None
                i += 1
                continue

            if stripped == "":
                prev_text = None
                i += 1
                continue

            m = re.match(r'^(#{1,6})(.*)$', line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip().rstrip('#').strip()
                heads.append((level, title, i))
                prev_text = None
                i += 1
                continue

            if prev_text is not None and re.match(r'^=+\s*$', stripped):
                heads.append((1, prev_text.strip(), prev_line_no))
                prev_text = None
                i += 1
                continue
            if prev_text is not None and re.match(r'^-+\s*$', stripped):
                heads.append((2, prev_text.strip(), prev_line_no))
                prev_text = None
                i += 1
                continue

            prev_text = line
            prev_line_no = i
            i += 1
        return heads

    def _rebuild_toc_list(self, force=False):
        heads = self._extract_headings(self._content_text)
        # 編集のたびに呼ばれるため、見出しに変化がなければ作り直さない
        # (作り直すと選択やスクロール位置が毎回リセットされてちらつく)。
        cache_key = (heads, self._toc_base_font_px(), self.lang)
        if not force and cache_key == getattr(self, "_toc_cache_key", None):
            return
        self._toc_cache_key = cache_key

        scroll = self._toc_list.verticalScrollBar().value()
        self._toc_list.clear()
        if not heads:
            item = QListWidgetItem(self._t("toc_empty"))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable
                          & ~Qt.ItemFlag.ItemIsEnabled)
            self._toc_list.addItem(item)
            return
        base_fs = self._toc_base_font_px()
        for i, (level, title, line_no) in enumerate(heads):
            label = ("  " * (level - 1)) + (title or f"H{level}")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setData(Qt.ItemDataRole.UserRole + 1, line_no)
            f = item.font()
            f.setPixelSize(max(16, base_fs - (level - 1)))
            item.setFont(f)
            self._toc_list.addItem(item)
        self._toc_list.verticalScrollBar().setValue(scroll)

    def _on_toc_item_clicked(self, item):
        line_no = item.data(Qt.ItemDataRole.UserRole + 1)
        heading_idx = item.data(Qt.ItemDataRole.UserRole)
        if line_no is None or heading_idx is None:
            return
        if self.edit_mode == "txt":
            block = self._md_editor.document().findBlockByNumber(line_no)
            if block.isValid():
                cur = self._md_editor.textCursor()
                cur.setPosition(block.position())
                self._md_editor.setTextCursor(cur)
                self._md_editor.centerCursor()
            self._md_editor.setFocus()
        elif self.edit_mode == "md":
            self._preview_web.page().runJavaScript(
                "(function(){"
                "var hs=document.querySelectorAll("
                "'.wrap>h1,.wrap>h2,.wrap>h3,.wrap>h4,.wrap>h5,.wrap>h6');"
                f"var idx={int(heading_idx)};"
                "if(hs[idx]){hs[idx].scrollIntoView({behavior:'smooth',block:'start'});}"
                "})();"
            )

    def _on_txt_cursor_moved(self):
        if self.edit_mode != "txt" or not hasattr(self, "_preview_web"):
            return
        line = self._md_editor.textCursor().blockNumber()
        self._preview_web.page().runJavaScript(
            f"window._mdvHighlightLine && window._mdvHighlightLine({line});"
        )

    def _go_back(self):
        self._set_mode("view")

    def _save_buf(self):
        """保存・書き出しの前に、編集中の内容を _content_text へ確定させる。"""
        if self.edit_mode == "txt":
            self._content_text = self._md_editor.toPlainText()
        elif self.edit_mode == "md":
            return self._flush_md_buf() != "failed"
        return True

    def _set_layout(self, layout):
        self.page_mode = layout
        self._refresh_btn_states()
        self._refresh_view_keeping_edits()

    def _open_margin_dialog(self):
        if self.page_mode == "b5":
            margins = self.b5_margins
            title = self._t("margin_title_b5")
        else:
            margins = self.a4_margins
            title = self._t("margin_title")
        dlg = MarginDialog(self, margins, I18N[self.lang], title=title)
        if dlg.exec():
            if self.page_mode == "b5":
                self.b5_margins = dlg.get_margins()
            else:
                self.a4_margins = dlg.get_margins()
            self._refresh_view_keeping_edits()

    def _on_scale_slider(self, v):
        self.scale_idx = v
        self._scale_val_lbl.setText(SCALE_LABELS[v])
        self._apply_theme(refresh=False)
        self._timer.start()

    def _save_app_settings(self):
        geom_b64 = self.saveGeometry().toBase64().data().decode("ascii")
        save_settings({
            "lang":             self.lang,
            "theme":            self.current_theme,
            "font_family":      self.ui_font_family,
            "bold_mode":        self.bold_mode,
            "hard_breaks":      self.hard_breaks,
            "scale_idx":        self.scale_idx,
            "last_pdf_dir":     self._last_pdf_dir,
            "pdf_embed_images": self._pdf_embed_images,
            "window_geometry":  geom_b64,
            "show_toc":         self._show_toc,
        })

    def _open_settings(self):
        # プラグインを再スキャン
        self._plugin_themes = load_plugin_themes()
        dlg = SettingsDialog(
            self, self.ui_font_family, self.lang,
            self.current_theme, self.bold_mode,
            I18N[self.lang], self._plugin_themes,
            hard_breaks=self.hard_breaks,
        )
        if dlg.exec():
            fam, lang, theme, bold, hard_breaks = dlg.get_result()
            changed_font = (fam != self.ui_font_family)
            self.ui_font_family = fam
            changed_lang = (lang != self.lang)
            self.lang      = lang
            self.bold_mode = bold
            self.hard_breaks = hard_breaks
            self.current_theme = theme
            if changed_font:
                # 再起動しなくても UI 全体に反映されるようにする
                self._apply_app_font()
            if changed_lang:
                self.menuBar().clear()
                self._build_menu()
                self._rebuild_fmt_tb()
            self._apply_theme(refresh=True)
            self._save_app_settings()

    # ════════════════════════════════════════════
    #  クラウドアップロード
    # ════════════════════════════════════════════
    def _upload_gdrive(self):
        self._save_buf()
        fname = (os.path.basename(self.current_file_path)
                 if self.current_file_path else self._t("unsaved_file"))
        QMessageBox.information(self, "Google Drive",
                                self._t("gdrive_msg").format(fname=fname))
        webbrowser.open("https://drive.google.com/drive/my-drive")

    def _upload_onedrive(self):
        self._save_buf()
        fname = (os.path.basename(self.current_file_path)
                 if self.current_file_path else self._t("unsaved_file"))
        QMessageBox.information(self, "OneDrive",
                                self._t("onedrive_msg").format(fname=fname))
        webbrowser.open("https://onedrive.live.com")

    # ════════════════════════════════════════════
    #  MD 書式ヘルパー (TXT編集モード用)
    # ════════════════════════════════════════════
    def _md_wrap(self, pre, post):
        cur = self._md_editor.textCursor()
        sel = cur.selectedText().replace("\u2029", "\n") or self._t("link_text_default")
        cur.insertText(f"{pre}{sel}{post}")
        self._md_editor.setTextCursor(cur)
        self._md_editor.setFocus()

    @staticmethod
    def _split_block_markers(line: str):
        """行を (インデント, 行頭マーカーの一覧, 中身) に分解する。

        マーカーは繰り返し剥がす。"## # 見出し" のように過去のバージョンで
        積み重なってしまった行も、一度で本文に戻せるようにするため。"""
        indent = re.match(r'^[ \t]*', line).group(0)
        rest = line[len(indent):]
        markers = []
        while True:
            m = _BLOCK_MARKER_RE.match(rest)
            if not m:
                break
            markers.append(m.group(0))
            rest = rest[m.end():]
        return indent, markers, rest

    def _current_line(self):
        """カーソル行(ブロック)を選択したカーソルと、その行の文字列を返す。

        StartOfLine/EndOfLine は折り返し後の「見た目の行」を指すため、
        長い行では書式が行の途中に入ってしまう。ブロック単位で扱う。"""
        cur = self._md_editor.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cur.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                         QTextCursor.MoveMode.KeepAnchor)
        return cur, cur.selectedText()

    def _md_set_block(self, prefix):
        """カーソル行のブロック書式を prefix に「置き換える」。

        v1.4.1 は前に足すだけだったため、H1 の行で H2 を押すと "## # 本文" の
        ように書式が積み重なり、本文ボタンでも 1 段しか外れなかった。
        同じ書式をもう一度押したときは解除して本文に戻す。"""
        cur, line = self._current_line()
        indent, markers, rest = self._split_block_markers(line)
        same = (len(markers) == 1 and markers[0].rstrip() == prefix.rstrip())
        new = indent + rest if same else indent + prefix + rest
        if new != line:
            cur.insertText(new)
        self._md_editor.setTextCursor(cur)
        self._md_editor.setFocus()

    def _md_insert(self, text):
        cur = self._md_editor.textCursor()
        cur.insertText(text)
        self._md_editor.setTextCursor(cur)
        self._md_editor.setFocus()

    def _md_toggle_ordered(self):
        """現在行の番号付きリスト書式をトグルする。既に番号付きなら解除し、
        付けるときは直前行の番号を見て連番になるようにする。"""
        cur, line = self._current_line()
        indent, markers, rest = self._split_block_markers(line)
        if len(markers) == 1 and re.match(r'^\d+\.', markers[0]):
            new = indent + rest
        else:
            n = 1
            prev = cur.block().previous()
            if prev.isValid():
                pm = re.match(r'^(\s*)(\d+)\.\s+', prev.text())
                if pm and pm.group(1) == indent:
                    n = int(pm.group(2)) + 1
            new = f"{indent}{n}. {rest}"
        if new != line:
            cur.insertText(new)
        self._md_editor.setTextCursor(cur)
        self._md_editor.setFocus()

    def _md_toggle_unordered(self):
        """現在行の箇条書きリスト書式をトグルする。"""
        cur, line = self._current_line()
        indent, markers, rest = self._split_block_markers(line)
        if len(markers) == 1 and re.match(r'^[-*+]\s', markers[0]):
            new = indent + rest
        else:
            new = f"{indent}- {rest}"
        if new != line:
            cur.insertText(new)
        self._md_editor.setTextCursor(cur)
        self._md_editor.setFocus()

    def _md_body(self):
        """現在行を本文(通常テキスト)に戻す。

        見出し/引用/リスト等の行頭マーカーを「すべて」除去する。1 つだけ外す
        実装だと、書式が積み重なった行 ("## # 本文") が本文に戻らなかった。"""
        cur, line = self._current_line()
        indent, markers, rest = self._split_block_markers(line)
        new = indent + rest
        if new != line:
            cur.insertText(new)
        self._md_editor.setTextCursor(cur)
        self._md_editor.setFocus()

    def _md_insert_table(self):
        col, cell = self._t("table_col"), self._t("table_cell")
        self._md_insert(
            f"\n| {col}1 | {col}2 | {col}3 |\n"
            "| :--- | :--- | :--- |\n"
            f"| {cell} | {cell} | {cell} |\n"
            f"| {cell} | {cell} | {cell} |\n"
        )

    # ── MD編集 (WYSIWYG) のリンク・画像挿入 ──
    #    QWebEngine 内の JS prompt() はダイアログが出ないため、Python 側の
    #    ネイティブ入力ダイアログでURLを受け取り、JS (_mdvLink/_mdvImage)
    #    で保存済み選択範囲へ挿入する。URL は _san_safe_url と同じ方針で検証する。
    def _on_md_link_button(self):
        if self.edit_mode != "md":
            return
        url, ok = QInputDialog.getText(
            self, self._t("link_dialog_title"),
            self._t("link_url_label"), text="https://")
        if not ok:
            return
        url = (url or "").strip()
        if not url or not _san_safe_url(url):
            QMessageBox.warning(self, self._t("link_dialog_title"),
                                self._t("link_invalid_url"))
            return
        label = self._t("link_text_default")
        try:
            self._preview_web.page().runJavaScript(
                f"window._mdvLink({json.dumps(url)}, {json.dumps(label)})")
        except Exception:
            QMessageBox.warning(self, self._t("save_error"),
                                self._t("capture_error"))

    def _on_md_image_button(self):
        if self.edit_mode != "md":
            return
        url, ok = QInputDialog.getText(
            self, self._t("img_dialog_title"),
            self._t("img_url_prompt"), text="https://")
        if not ok:
            return
        url = (url or "").strip()
        if not url or not _san_safe_url(url, allow_data_image=True):
            QMessageBox.warning(self, self._t("img_dialog_title"),
                                self._t("img_invalid_url"))
            return
        alt = self._t("img_alt_default")
        try:
            self._preview_web.page().runJavaScript(
                f"window._mdvImage({json.dumps(url)}, {json.dumps(alt)})")
        except Exception:
            QMessageBox.warning(self, self._t("save_error"),
                                self._t("capture_error"))

    def _wait_mermaid_then(self, page, callback, attempts=0):
        """mermaid.js の非同期描画 (window._mdvMermaidReady) が終わるまで
        短間隔でポーリングしてから callback を呼ぶ。printToPdf() はページの
        現在の DOM をそのまま撮るため、SVG挿入前に呼ぶと図が空欄になる。
        上限 (約3秒) を超えたら描画未完了でも印刷を実行する
        (失敗時に無限待機させないための保険)。"""
        def check(ready):
            if ready or attempts >= 40:
                callback()
            else:
                QTimer.singleShot(
                    75, lambda: self._wait_mermaid_then(page, callback, attempts + 1))
        page.runJavaScript("window._mdvMermaidReady===true", check)

    # ════════════════════════════════════════════
    #  PDF書き出し
    # ════════════════════════════════════════════
    def _export_pdf(self):
        if not self._save_buf():
            QMessageBox.warning(self, self._t("save_error"), self._t("capture_error"))
            return
        dlg = PdfExportDialog(
            self, self.page_mode,
            self.a4_margins, self.b5_margins,
            I18N[self.lang],
            embed_images=self._pdf_embed_images,
            current_theme=self.current_theme,
            plugin_themes=self._plugin_themes,
        )
        if not dlg.exec():
            return
        page_size_name, landscape, margins, embed_images, pdf_theme = dlg.get_settings()
        self._pdf_embed_images = embed_images
        self._save_app_settings()
        t_m, r_m, b_m, l_m = margins

        path, _ = QFileDialog.getSaveFileName(
            self, self._t("pdf_export_menu"),
            self._last_pdf_dir,
            "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self._last_pdf_dir = os.path.dirname(path)
        self._save_app_settings()

        if page_size_name == "B5":
            page_size = QPageSize(QSizeF(182, 257), QPageSize.Unit.Millimeter, "JIS B5")
        else:
            page_size = QPageSize(QPageSize.PageSizeId.A4)

        orient = (QPageLayout.Orientation.Landscape
                  if landscape else QPageLayout.Orientation.Portrait)
        layout = QPageLayout(
            page_size, orient,
            QMarginsF(l_m, t_m, r_m, b_m),
            QPageLayout.Unit.Millimeter,
        )

        self._pdf_layout_ref = layout  # prevent GC while Chromium processes

        # 選択テーマのパレットを一時的に適用してクリーンなHTML生成
        # (カーソル/contenteditable除去 + テーマ適用)
        orig_palette = self._palette
        if pdf_theme == "dark":
            self._palette = DARK_PALETTE
        elif pdf_theme == "light":
            self._palette = LIGHT_PALETTE
        elif pdf_theme in self._plugin_themes:
            self._palette = self._plugin_themes[pdf_theme]
        pdf_palette = self._palette

        strip_img = not embed_images
        try:
            pdf_html = self._build_md_html(self._content_text, editable=False, strip_images=strip_img)
        finally:
            self._palette = orig_palette  # パレットを元に戻す

        base_path = None
        if self.current_file_path:
            base_path = os.path.dirname(os.path.abspath(self.current_file_path)) + os.sep

        # ── PDF印刷は表示とは別のオフスクリーンViewで行う ──
        #    従来は表示中の _preview_web にPDF用HTMLを上書き→印刷→復元して
        #    いたため、スクロール/カーソル喪失・操作競合・画面とPDFでの改ページ
        #    ずれが起きていた。独立Viewにすることで表示状態に一切触れない。
        try:
            pdf_view = QWebEngineView()
        except Exception:
            QMessageBox.warning(self, "PDF", self._t("pdf_error"))
            self._pdf_layout_ref = None
            return
        # self の子にして寿命を管理する (レイアウトに入れないので不可視のまま)。
        # 終了時は deleteLater で破棄し、参照を外してメモリを解放する。
        pdf_view.setParent(self)
        self._pdf_view = pdf_view
        try:
            pdf_view.page().setBackgroundColor(QColor(pdf_palette.get("bg", "#ffffff")))
        except Exception:
            pass
        try:
            pdf_loader = SafeWebLoader(pdf_view, dark=bool(_hex_is_dark(pdf_palette.get("bg", "#ffffff"))))
        except Exception:
            pdf_loader = None
        self._pdf_loader = pdf_loader

        # PDF 書き出しの状態管理 ("loading" → "printing" → 終了)。
        # 小さい HTML では setHtml/load が即座に loadFinished を発火しうるため、
        # 接続はロードより「前」に行い、取りこぼしを防ぐ。
        self._pdf_state = "loading"

        def _cleanup_pdf_view():
            try:
                pdf_view.page().pdfPrintingFinished.disconnect(_on_pdf_done)
            except Exception:
                pass
            try:
                pdf_view.loadFinished.disconnect(_do_print)
            except Exception:
                pass
            if getattr(self, "_pdf_view", None) is pdf_view:
                self._pdf_view = None
            self._pdf_loader = None
            self._pdf_layout_ref = None
            try:
                pdf_view.setParent(None)
                pdf_view.deleteLater()
            except Exception:
                pass

        def _on_pdf_done(pdf_path, ok):
            if self._pdf_state != "printing":
                return
            self._pdf_state = "done"
            _cleanup_pdf_view()
            if ok:
                QMessageBox.information(self, "PDF", self._t("pdf_success"))
            else:
                QMessageBox.warning(self, "PDF", self._t("pdf_error"))

        def _do_print(ok=True):
            if self._pdf_state != "loading":
                return
            # loadFinished の切断は _cleanup_pdf_view に一本化する
            # (ここで切断すると後続の切断が警告になる。再入は状態で防ぐ)。
            if not ok:
                self._pdf_state = "done"
                _cleanup_pdf_view()
                QMessageBox.warning(self, "PDF", self._t("pdf_error"))
                return
            self._pdf_state = "printing"
            page = pdf_view.page()
            page.pdfPrintingFinished.connect(_on_pdf_done)
            if "_mdvMermaidReady" in pdf_html:
                self._wait_mermaid_then(page, lambda: page.printToPdf(path, layout))
            else:
                page.printToPdf(path, layout)

        def _on_pdf_timeout():
            # ロードが完了しないまま固まった場合の保険: Viewを破棄して通知。
            # 表示側には触っていないため復元は不要。
            if self._pdf_state != "loading":
                return
            self._pdf_state = "done"
            _cleanup_pdf_view()
            QMessageBox.warning(self, "PDF", self._t("pdf_error"))

        # 接続 → ロード の順序を厳守する
        pdf_view.loadFinished.connect(_do_print)
        try:
            if pdf_loader is not None:
                pdf_loader.load_html(pdf_html, base_path)
            else:
                base_url = QUrl.fromLocalFile(base_path) if base_path else QUrl()
                pdf_view.setHtml(pdf_html, base_url)
        except Exception:
            self._pdf_state = "done"
            _cleanup_pdf_view()
            QMessageBox.warning(self, "PDF", self._t("pdf_error"))
            return
        QTimer.singleShot(20000, _on_pdf_timeout)

    # ════════════════════════════════════════════
    #  HTML書き出し
    # ════════════════════════════════════════════
    def _export_html(self):
        if not self._save_buf():
            QMessageBox.warning(self, self._t("save_error"), self._t("capture_error"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self._t("html_export_menu"),
            os.path.expanduser("~"),
            "HTML (*.html *.htm)"
        )
        if not path:
            return
        if not (path.lower().endswith(".html") or path.lower().endswith(".htm")):
            path += ".html"
        try:
            html = self._build_md_html(self._content_text, editable=False)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "HTML", self._t("html_export_success"))
        except Exception as e:
            QMessageBox.warning(self, self._t("html_save_error"), str(e))

    # ════════════════════════════════════════════
    #  スタートアップ
    # ════════════════════════════════════════════
    def _startup_open(self):
        """スタートアップダイアログ（新規作成 or ファイルを開く）"""
        # コマンドライン / Apple Events 経由でファイルが指定された場合はダイアログをスキップ
        if self._initial_file and os.path.isfile(self._initial_file):
            path = self._initial_file
            self._initial_file = None
            self._load_file(path)
            return

        dlg = StartupDialog(self, I18N[self.lang], self.lang)
        dlg.setStyleSheet(self.styleSheet())
        result = dlg.exec()

        if result:
            new_lang = dlg.selected_lang
            if new_lang != self.lang:
                self.lang = new_lang
                self.menuBar().clear()
                self._build_menu()
                self._rebuild_fmt_tb()
                self._apply_theme(refresh=False)

        if result and dlg.action == StartupDialog.ACTION_NEW:
            self.file_new()
        elif result and dlg.action == StartupDialog.ACTION_OPEN:
            path, _ = QFileDialog.getOpenFileName(
                self, self._t("open"), os.path.expanduser("~"),
                OPEN_FILTER
            )
            if path:
                self._load_file(path)
            else:
                self._set_sample()
                self._refresh_view()
        elif result and dlg.action == StartupDialog.ACTION_GUIDE:
            self._open_guide()
        else:
            # フォールバック（通常ここには来ない）
            self.file_new()

    # ════════════════════════════════════════════
    #  ファイル操作
    # ════════════════════════════════════════════
    def file_new(self):
        if not self._maybe_save():
            return
        self._readonly_file = False
        self.doc_kind = "md"
        self._content_text = ""
        self.current_file_path = None
        self.is_modified = False
        self._md_editor.blockSignals(True)
        self._md_editor.setPlainText("")
        self._md_editor.blockSignals(False)
        self._do_set_mode("md")
        self._update_title()

    def _load_file(self, path):
        text = None
        read_error = None
        for enc in ("utf-8-sig", "utf-8", "shift_jis", "cp932", "euc-jp", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    text = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue
            # PermissionError / IsADirectoryError / OSError 等はデコード不能とは
            # 別の失敗。errors="replace" へのフォールバックで黙って開かず、
            # 現在の文書をそのまま維持する。
            except OSError as e:
                read_error = e
                break
        if text is None and read_error is None:
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                text = raw.decode("utf-8", errors="replace")
            except OSError as e:
                read_error = e
            except Exception as e:
                read_error = e
        if read_error is not None:
            QMessageBox.warning(self, self._t("read_error"), str(read_error))
            return
        self._content_text = text
        # YAML ファイルは Markdown ではなく YAML として構文強調表示する
        self.doc_kind = "yaml" if path.lower().endswith(YAML_EXTS) else "md"
        self._md_editor.blockSignals(True)
        self._md_editor.setPlainText(text)
        self._md_editor.blockSignals(False)
        self.current_file_path = path
        self.is_modified = False
        self._update_title()
        self.edit_mode = "view"
        self._md_page.set_mode("view")
        self._editor_stack.setCurrentIndex(0)
        self._editor_stack.setVisible(False)
        self._update_toc_panel_visibility()
        self._update_splitter_sizes()
        self._fmt_container.setVisible(False)
        self._refresh_btn_states()
        self._check_and_fetch_images_for_file(text)
        self._refresh_view()

    def file_open(self):
        if not self._maybe_save():
            return
        self._readonly_file = False
        path, _ = QFileDialog.getOpenFileName(
            self, self._t("open"), os.path.expanduser("~"),
            OPEN_FILTER
        )
        if path:
            self._load_file(path)

    def file_save(self) -> bool:
        if self.current_file_path:
            return self._write(self.current_file_path)
        else:
            return self.file_save_as()

    def file_save_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, self._t("save_as"), os.path.expanduser("~"),
            SAVE_FILTER
        )
        if path:
            ok = self._write(path)
            if ok:
                self.current_file_path = path
                # 拡張子が変わったら描画の種類も追従させる
                new_kind = "yaml" if path.lower().endswith(YAML_EXTS) else "md"
                if new_kind != self.doc_kind:
                    self.doc_kind = new_kind
                    if not self._mode_available(self.edit_mode):
                        self._do_set_mode("txt")
                    self._refresh_btn_states()
                    self._refresh_view()
                self._update_title()
            return ok
        return False

    def _write(self, path) -> bool:
        if not self._save_buf():
            QMessageBox.warning(self, self._t("save_error"), self._t("capture_error"))
            return False
        try:
            # 直接 open(path, "w") で書くと、書込み中にプロセスが落ちたり
            # ディスクが一杯になったりしたときに既存ファイルが失われる。
            # 同一フォルダの一時ファイルへ書いてから原子的に置換する。
            # os.replace は同一ボリュームでのみ原子的なので、tmp は必ず
            # 対象と同じフォルダに作る ( tempfile は /tmp 等へ置くので不可 )。
            import uuid as _uuid
            tmp_path = f"{path}.{_uuid.uuid4().hex[:8]}.tmp"
            # 改行は LF に統一する。text mode の既定では Windows で CRLF 化され、
            # macOS/Linux 版との差分が出るため (読取側は universal newlines で両対応)。
            with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(self._content_text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception as e:
            # 失敗したときは tmp を掃除し、既存ファイル・dirty状態を維持する
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            QMessageBox.warning(self, self._t("save_error"), str(e))
            return False
        self.is_modified = False
        self._update_title()
        return True

    def _maybe_save(self) -> bool:
        # MD編集モードの未反映の編集を先に取り込む。これをしないと、
        # 入力直後に閉じたときに「変更なし」と判定して黙って捨ててしまう。
        if not self._readonly_file and self.edit_mode == "md":
            if not self._save_buf():
                QMessageBox.warning(self, self._t("save_error"), self._t("capture_error"))
                return False
        if self._readonly_file or not self.is_modified:
            return True
        r = QMessageBox.question(
            self, self._t("unsaved"), self._t("unsaved_msg"),
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if r == QMessageBox.StandardButton.Save:
            return self.file_save()
        return r == QMessageBox.StandardButton.Discard

    # ════════════════════════════════════════════
    #  ユーティリティ
    # ════════════════════════════════════════════
    def _update_title(self):
        name = (os.path.basename(self.current_file_path)
                if self.current_file_path else self._t("untitled"))
        mark = " ●" if self.is_modified else ""
        ro = f" [{self._t('readonly_notice')}]" if self._readonly_file else ""
        self.setWindowTitle(f"{name}{mark}{ro} — MD Viewer Pro v{APP_VERSION}")

    def _set_sample(self):
        _samples = {
            "ja": (
                "# MD Viewer Pro へようこそ\n\n"
                "上部バーでモード・レイアウト・スケールを切り替えられます。\n\n"
                "## 機能一覧\n\n"
                "| 機能 | 説明 |\n"
                "| :--- | :--- |\n"
                "| 閲覧モード | Markdown をきれいにレンダリング |\n"
                "| MD編集 | レンダリングフォーマットのままテキストを直接編集 |\n"
                "| TXT編集 | 左エディタ + 右リアルタイムプレビュー |\n"
                "| A4文書 | 印刷向けA4レイアウト・余白設定 |\n"
                "| 詳細設定 | フォント・言語・テーマ・太字変更 |\n"
                "| プラグインテーマ | ~/.mdviewer/themes/ にJSONを置いて配色追加 |\n\n"
                "## チェックリスト\n\n"
                "- [x] Markdown 表示\n"
                "- [x] リアルタイムプレビュー\n"
                "- [x] コードブロックのコピーボタン\n"
                "- [x] PDF/HTML書き出し\n"
                "- [x] プラグインテーマ\n"
                "- [ ] クラウド同期（予定）\n\n"
                "## コードブロック\n\n"
                "```python\n"
                "def hello():\n"
                "    print('Hello, MD Viewer Pro!')\n"
                "```\n\n"
                "> TXT編集またはMD編集モードに切り替えると書式ツールバーが表示されます。\n"
            ),
            "en": (
                "# Welcome to MD Viewer Pro\n\n"
                "Use the top bar to switch mode, layout, and scale.\n\n"
                "## Features\n\n"
                "| Feature | Description |\n"
                "| :--- | :--- |\n"
                "| View | Renders Markdown beautifully |\n"
                "| MD Edit | Edit text directly in rendered format |\n"
                "| TXT Edit | Left editor + right live preview |\n"
                "| A4 Doc | Print-ready A4 layout with margin settings |\n"
                "| Settings | Font, language, theme, bold toggle |\n"
                "| Plugin Themes | Add palettes via JSON in ~/.mdviewer/themes/ |\n\n"
                "## Checklist\n\n"
                "- [x] Markdown rendering\n"
                "- [x] Live preview\n"
                "- [x] Code block copy button\n"
                "- [x] PDF/HTML export\n"
                "- [x] Plugin themes\n"
                "- [ ] Cloud sync (planned)\n\n"
                "## Code Block\n\n"
                "```python\n"
                "def hello():\n"
                "    print('Hello, MD Viewer Pro!')\n"
                "```\n\n"
                "> Switch to TXT Edit or MD Edit mode to show the format toolbar.\n"
            ),
            "de": (
                "# Willkommen bei MD Viewer Pro\n\n"
                "Verwenden Sie die obere Leiste, um Modus, Layout und Skalierung zu wechseln.\n\n"
                "## Funktionen\n\n"
                "| Funktion | Beschreibung |\n"
                "| :--- | :--- |\n"
                "| Ansicht | Rendert Markdown übersichtlich |\n"
                "| MD Bearbeiten | Text direkt im gerenderten Format bearbeiten |\n"
                "| TXT Bearbeiten | Linker Editor + rechte Live-Vorschau |\n"
                "| A4 Dok. | Druckfertiges A4-Layout mit Randeinstellungen |\n"
                "| Einstellungen | Schrift, Sprache, Thema, Fettdruck |\n"
                "| Plugin-Themen | Paletten als JSON in ~/.mdviewer/themes/ hinzufügen |\n\n"
                "## Checkliste\n\n"
                "- [x] Markdown-Rendering\n"
                "- [x] Live-Vorschau\n"
                "- [x] Kopier-Schaltfläche für Codeblöcke\n"
                "- [x] PDF/HTML-Export\n"
                "- [x] Plugin-Themen\n"
                "- [ ] Cloud-Synchronisierung (geplant)\n\n"
                "## Codeblock\n\n"
                "```python\n"
                "def hello():\n"
                "    print('Hello, MD Viewer Pro!')\n"
                "```\n\n"
                "> Wechseln Sie in den TXT- oder MD-Bearbeitungsmodus, um die Formatierungsleiste anzuzeigen.\n"
            ),
            "fr": (
                "# Bienvenue dans MD Viewer Pro\n\n"
                "Utilisez la barre supérieure pour changer le mode, la mise en page et l'échelle.\n\n"
                "## Fonctionnalités\n\n"
                "| Fonctionnalité | Description |\n"
                "| :--- | :--- |\n"
                "| Vue | Rendu Markdown élégant |\n"
                "| Édition MD | Modifier le texte directement au format rendu |\n"
                "| Édition TXT | Éditeur gauche + aperçu en direct à droite |\n"
                "| Doc A4 | Mise en page A4 pour impression avec réglage des marges |\n"
                "| Paramètres | Police, langue, thème, gras |\n"
                "| Thèmes plugin | Ajouter des palettes JSON dans ~/.mdviewer/themes/ |\n\n"
                "## Liste de contrôle\n\n"
                "- [x] Rendu Markdown\n"
                "- [x] Aperçu en direct\n"
                "- [x] Bouton copier pour les blocs de code\n"
                "- [x] Export PDF/HTML\n"
                "- [x] Thèmes plugin\n"
                "- [ ] Synchronisation cloud (prévu)\n\n"
                "## Bloc de code\n\n"
                "```python\n"
                "def hello():\n"
                "    print('Hello, MD Viewer Pro!')\n"
                "```\n\n"
                "> Passez en mode Édition TXT ou MD pour afficher la barre de formatage.\n"
            ),
            "zh": (
                "# 欢迎使用 MD Viewer Pro\n\n"
                "可以在顶部工具栏切换模式、版式和缩放。\n\n"
                "## 功能一览\n\n"
                "| 功能 | 说明 |\n"
                "| :--- | :--- |\n"
                "| 阅读模式 | 清晰地渲染 Markdown |\n"
                "| MD编辑 | 保持渲染后的样子直接编辑 |\n"
                "| TXT编辑 | 左侧编辑器 + 右侧实时预览 |\n"
                "| A4文档 | 适合打印的 A4 版式与页边距设置 |\n"
                "| 设置 | 字体、语言、主题、加粗的切换 |\n"
                "| 插件主题 | 在 ~/.mdviewer/themes/ 放入 JSON 即可添加 |\n\n"
                "## 清单\n\n"
                "- [x] Markdown 渲染\n"
                "- [x] 实时预览\n"
                "- [x] 代码块的复制按钮\n"
                "- [x] 导出 PDF / HTML\n"
                "- [x] 插件主题\n"
                "- [ ] 云端同步（计划中）\n\n"
                "## 代码块\n\n"
                "```python\n"
                "def hello():\n"
                "    print('Hello, MD Viewer Pro!')\n"
                "```\n\n"
                "> 切换到 TXT编辑 或 MD编辑 模式即可显示格式工具栏。\n"
            ),
        }
        s = _samples.get(self.lang, _samples["en"])
        if sys.platform == "win32":
            # Windowsでは設定場所が %APPDATA%/MDViewerPro のため表示を合わせる
            s = s.replace("~/.mdviewer/themes/",
                          "%APPDATA%\\MDViewerPro\\themes")
        self._content_text = s
        self._md_editor.blockSignals(True)
        self._md_editor.setPlainText(s)
        self._md_editor.blockSignals(False)
        self.is_modified = False
        self._update_title()

    def _open_guide(self):
        """選択中の言語のsampleファイルを読み取り専用で開く"""
        lang_to_file = {
            # ファイル名はASCIIのみにする。非ASCII名 (ç 等の合成可能文字) は
            # コピー時にUnicode正規化で別名になり、署名シールが壊れて
            # Gatekeeper に「壊れている」と判定される (v1.4.7で発覚)。
            "ja": "sample_ja.md",
            "en": "sample_en.md",
            "de": "sample_de.md",
            "fr": "sample_fr.md",
            "zh": "sample_zh.md",
        }
        filename = lang_to_file.get(self.lang, "sample_en.md")
        candidates = []
        # 開発時: スクリプトと同じディレクトリの資料箱
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(script_dir, "資料箱", filename))
        # PyInstaller bundle: Contents/Resources/ (macOSバンドルのdataパス)
        if hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, "資料箱", filename))
        # macOSバンドル: executable の ../Resources/
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, "..", "Resources", "資料箱", filename))
        for path in candidates:
            path = os.path.normpath(path)
            if os.path.exists(path):
                self._load_file_readonly(path)
                return
        self._set_sample()
        self._refresh_view()

    def _load_file_readonly(self, path: str):
        """ファイルを読み取り専用モードで開く"""
        self._load_file(path)
        self._readonly_file = True
        self._refresh_btn_states()
        self._update_title()

    # ════════════════════════════════════════════
    #  新規ウィンドウ
    # ════════════════════════════════════════════
    def new_window(self):
        app = QApplication.instance()
        if isinstance(app, MDApplication):
            app.new_window()

    def closeEvent(self, event):
        self._timer.stop()
        self._resize_timer.stop()
        if self._maybe_save():
            self._save_app_settings()
            worker = getattr(self, "_img_worker", None)
            if worker is not None and worker.isRunning():
                worker.cancel()
                worker.wait(2000)
            loader = getattr(self, "_loader", None)
            if loader is not None:
                loader.cleanup()
            event.accept()
            self.window_closed.emit()
        else:
            event.ignore()


# ════════════════════════════════════════════════
if __name__ == "__main__":
    app = MDApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
    app.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    # コマンドライン引数でファイルが指定された場合
    args = app.arguments()
    _arg_path = args[1] if len(args) > 1 and os.path.isfile(args[1]) else None

    if not app.is_primary_instance():
        # 既存プロセスへ転送して終了。転送できなければ残骸とみなし通常起動。
        if app.forward_to_primary(_arg_path):
            sys.exit(0)
        app.take_over_as_primary()

    win = app.new_window()

    if _arg_path is not None:
        win._initial_file = _arg_path

    sys.exit(app.exec())
