
import sys
import os
import re
import json
import glob as glob_mod
import shutil
import tempfile
import webbrowser
import base64
import urllib.request
import urllib.error
from typing import Optional, Dict, List
import markdown
from html.parser import HTMLParser

os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QFileDialog,
    QSplitter, QMessageBox, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QSpinBox, QDialog, QDialogButtonBox, QFormLayout,
    QStackedWidget, QPushButton, QSizePolicy, QSlider,
    QComboBox, QGroupBox, QFontComboBox, QCheckBox,
)
from PySide6.QtGui import (
    QAction, QKeySequence, QTextCursor,
    QPageLayout, QPageSize, QFont, QColor, QDesktopServices,
    QFileOpenEvent,
)
from PySide6.QtCore import Qt, QMarginsF, QTimer, QUrl, QSizeF, QObject, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebChannel import QWebChannel

# ════════════════════════════════════════════════
#  定数
# ════════════════════════════════════════════════
SCALE_STEPS  = [0.5, 0.75, 1.0, 1.25, 1.5]
SCALE_LABELS = ["50%", "75%", "100%", "125%", "150%"]
DEFAULT_SCALE_IDX = 2  # 100%
TB_H  = 64
FMT_H = 48
LANGS = {"日本語": "ja", "English": "en", "Deutsch": "de", "Français": "fr"}
PLUGIN_DIR    = os.path.expanduser("~/.mdviewer/themes")
SETTINGS_DIR  = os.path.expanduser("~/.mdviewer")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
APP_VERSION   = "1.0.0"

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
        "settings_title": "詳細設定",
        "font_label": "フォント", "lang_label": "言語", "theme_label": "テーマ",
        "dark": "ダークモード", "light": "ライトモード",
        "bold_label": "テキスト太字強調",
        "plugin_label": "プラグインテーマ",
        "plugin_dir_btn": "テーマフォルダを開く",
        "untitled": "無題",
        "margin_title": "A4余白設定 (mm)",
        "margin_title_b5": "B5余白設定 (mm)",
        "margin_top": "上", "margin_right": "右",
        "margin_bottom": "下", "margin_left": "左",
        "fmt_bold": "B", "fmt_italic": "I", "fmt_strike": "~~", "fmt_code": "コード",
        "fmt_h1": "H1", "fmt_h2": "H2", "fmt_h3": "H3",
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
        "settings_title": "Settings",
        "font_label": "Font", "lang_label": "Language", "theme_label": "Theme",
        "dark": "Dark Mode", "light": "Light Mode",
        "bold_label": "Bold Text Emphasis",
        "plugin_label": "Plugin Theme",
        "plugin_dir_btn": "Open Theme Folder",
        "untitled": "Untitled",
        "margin_title": "A4 Margins (mm)",
        "margin_title_b5": "B5 Margins (mm)",
        "margin_top": "Top", "margin_right": "Right",
        "margin_bottom": "Bottom", "margin_left": "Left",
        "fmt_bold": "B", "fmt_italic": "I", "fmt_strike": "~~", "fmt_code": "Code",
        "fmt_h1": "H1", "fmt_h2": "H2", "fmt_h3": "H3",
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
        "settings_title": "Einstellungen",
        "font_label": "Schriftart", "lang_label": "Sprache", "theme_label": "Thema",
        "dark": "Dunkelmodus", "light": "Hellmodus",
        "bold_label": "Fettschrift-Hervorhebung",
        "plugin_label": "Plugin-Thema",
        "plugin_dir_btn": "Themenordner öffnen",
        "untitled": "Unbenannt",
        "margin_title": "A4-Ränder (mm)",
        "margin_title_b5": "B5-Ränder (mm)",
        "margin_top": "Oben", "margin_right": "Rechts",
        "margin_bottom": "Unten", "margin_left": "Links",
        "fmt_bold": "B", "fmt_italic": "I", "fmt_strike": "~~", "fmt_code": "Code",
        "fmt_h1": "H1", "fmt_h2": "H2", "fmt_h3": "H3",
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
        "settings_title": "Paramètres",
        "font_label": "Police", "lang_label": "Langue", "theme_label": "Thème",
        "dark": "Mode sombre", "light": "Mode clair",
        "bold_label": "Emphase en gras",
        "plugin_label": "Thème plugin",
        "plugin_dir_btn": "Ouvrir le dossier des thèmes",
        "untitled": "Sans titre",
        "margin_title": "Marges A4 (mm)",
        "margin_title_b5": "Marges B5 (mm)",
        "margin_top": "Haut", "margin_right": "Droite",
        "margin_bottom": "Bas", "margin_left": "Gauche",
        "fmt_bold": "G", "fmt_italic": "I", "fmt_strike": "~~", "fmt_code": "Code",
        "fmt_h1": "H1", "fmt_h2": "H2", "fmt_h3": "H3",
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
    },
}


# ════════════════════════════════════════════════
#  設定の読み書き
# ════════════════════════════════════════════════
_SETTINGS_DEFAULTS: dict = {
    "lang":        "ja",
    "theme":       "dark",
    "font_family": "Helvetica Neue",
    "bold_mode":   False,
    "scale_idx":   DEFAULT_SCALE_IDX,
    "last_pdf_dir": "",
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
        if result["lang"] not in ("ja", "en", "de", "fr"):
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
#  QApplication サブクラス — macOS ファイルオープンイベント対応
# ════════════════════════════════════════════════
class MDApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self._main_win: Optional["MDViewerPro"] = None

    def event(self, e):
        if isinstance(e, QFileOpenEvent):
            path = e.file()
            if path and os.path.isfile(path):
                win = self._main_win
                if win is not None:
                    if win._startup_done:
                        win._load_file(path)
                    else:
                        win._initial_file = path
                return True
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
_REMOTE_IMG_RE = re.compile(r'!\[[^\]]*\]\((https?://[^)\s]+)\)')

def _extract_remote_image_urls(text: str) -> List[str]:
    return list(dict.fromkeys(_REMOTE_IMG_RE.findall(text)))

def _safe_fetch_image(url: str, max_bytes: int = 10 * 1024 * 1024, timeout: int = 10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MDViewerPro/1.3"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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


# ════════════════════════════════════════════════
#  カスタム WebEnginePage — リンク制御
# ════════════════════════════════════════════════
class MDWebPage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "view"

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
#  HTML → Markdown 変換 (標準ライブラリのみ使用)
# ════════════════════════════════════════════════
class _HTML2MD(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: List[str] = []
        self._stack: List[str] = []
        self._in_pre = False
        self._pending_href: Optional[str] = None
        self._list_depth = 0
        self._ol_counters: List[int] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_d = dict(attrs)
        self._stack.append(tag)
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.parts.append('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'p':
            self.parts.append('\n\n')
        elif tag == 'br':
            self.parts.append('\n')
        elif tag in ('strong', 'b'):
            self.parts.append('**')
        elif tag in ('em', 'i'):
            self.parts.append('*')
        elif tag in ('s', 'del', 'strike'):
            self.parts.append('~~')
        elif tag == 'code' and not self._in_pre:
            self.parts.append('`')
        elif tag == 'pre':
            self._in_pre = True
            self.parts.append('\n\n```\n')
        elif tag == 'a':
            self._pending_href = attrs_d.get('href', '')
            self.parts.append('[')
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
            indent = '  ' * (self._list_depth - 1)
            parent = next((t for t in reversed(self._stack[:-1]) if t in ('ul', 'ol')), 'ul')
            if parent == 'ol' and self._ol_counters:
                self._ol_counters[-1] += 1
                self.parts.append(f'\n{indent}{self._ol_counters[-1]}. ')
            else:
                self.parts.append(f'\n{indent}- ')
        elif tag == 'blockquote':
            self.parts.append('\n\n> ')
        elif tag == 'hr':
            self.parts.append('\n\n---\n\n')
        elif tag == 'tr':
            self.parts.append('\n|')
        elif tag in ('th', 'td'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.parts.append('\n\n')
        elif tag == 'p':
            self.parts.append('\n\n')
        elif tag in ('strong', 'b'):
            self.parts.append('**')
        elif tag in ('em', 'i'):
            self.parts.append('*')
        elif tag in ('s', 'del', 'strike'):
            self.parts.append('~~')
        elif tag == 'code' and not self._in_pre:
            self.parts.append('`')
        elif tag == 'pre':
            self._in_pre = False
            self.parts.append('\n```\n\n')
        elif tag == 'a':
            href = self._pending_href or ''
            self.parts.append(f']({href})')
            self._pending_href = None
        elif tag in ('th', 'td'):
            self.parts.append(' |')
        elif tag == 'ul':
            self._list_depth = max(0, self._list_depth - 1)
            self.parts.append('\n')
        elif tag == 'ol':
            self._list_depth = max(0, self._list_depth - 1)
            if self._ol_counters:
                self._ol_counters.pop()
            self.parts.append('\n')

    def handle_data(self, data):
        self.parts.append(data)

    def get_result(self) -> str:
        text = ''.join(self.parts)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def _html_to_md(html: str) -> str:
    parser = _HTML2MD()
    parser.feed(html)
    return parser.get_result()


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
                self._web.setHtml(html[:self._MAX_BYTES].decode("utf-8", errors="replace"), QUrl())
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
    def __init__(self, parent, font_family, lang, current_theme, bold_mode, t, plugin_themes: Dict[str, dict]):
        super().__init__(parent)
        self.setWindowTitle(t["settings_title"])
        self.setMinimumWidth(380)
        root = QVBoxLayout(self)
        root.setSpacing(14)

        # フォント
        fg = QGroupBox(t["font_label"])
        fl = QVBoxLayout(fg)
        self._font_cb = QFontComboBox()
        self._font_cb.setCurrentFont(QFont(font_family))
        fl.addWidget(self._font_cb)
        root.addWidget(fg)

        # 言語
        lg = QGroupBox(t["lang_label"])
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

    def get_result(self):
        font = self._font_cb.currentFont().family()
        lang = LANGS[self._lang_cb.currentText()]
        bold = self._bold_cb.isChecked()
        idx  = self._theme_cb.currentIndex()
        if idx == 0:
            theme = "dark"
        elif idx == 1:
            theme = "light"
        else:
            theme = self._theme_items[idx]
        return font, lang, theme, bold


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

        title_lbl = QLabel(t["startup_title"])
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tf = title_lbl.font()
        tf.setPointSize(20)
        tf.setBold(True)
        title_lbl.setFont(tf)
        root.addWidget(title_lbl)

        hint_lbl = QLabel(t["startup_hint"])
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hint_lbl)

        root.addSpacing(8)

        open_btn = QPushButton(t["startup_open"])
        open_btn.setFixedHeight(44)
        open_btn.clicked.connect(self._on_open)
        root.addWidget(open_btn)

        new_btn = QPushButton(t["startup_new"])
        new_btn.setFixedHeight(44)
        new_btn.clicked.connect(self._on_new)
        root.addWidget(new_btn)

        # Language selector row
        lang_row = QWidget()
        lang_lay = QHBoxLayout(lang_row)
        lang_lay.setContentsMargins(0, 0, 0, 0)
        lang_lbl = QLabel(t.get("startup_language", "言語"))
        lang_lay.addWidget(lang_lbl)
        self._lang_cb = QComboBox()
        self._lang_cb.addItems(list(LANGS.keys()))
        cur_key = [k for k, v in LANGS.items() if v == current_lang]
        if cur_key:
            self._lang_cb.setCurrentText(cur_key[0])
        lang_lay.addWidget(self._lang_cb)
        root.addWidget(lang_row)

        guide_btn = QPushButton(t.get("startup_guide", "説明を開く"))
        guide_btn.setFixedHeight(44)
        guide_btn.clicked.connect(self._on_guide)
        root.addWidget(guide_btn)

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


# ════════════════════════════════════════════════
#  PDF書き出し設定ダイアログ
# ════════════════════════════════════════════════
class PdfExportDialog(QDialog):
    def __init__(self, parent, page_mode, a4_margins, b5_margins, t):
        super().__init__(parent)
        self.setWindowTitle(t.get("pdf_settings_title", "PDF書き出し設定"))
        self.setMinimumWidth(320)
        self._a4_margins = a4_margins
        self._b5_margins = b5_margins
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
        return page, landscape, margins


# ════════════════════════════════════════════════
#  PianoBtn
# ════════════════════════════════════════════════
class PianoBtn(QPushButton):
    def __init__(self, label="", parent=None):
        super().__init__(label, parent)
        sp = self.sizePolicy()
        sp.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        self.setSizePolicy(sp)
        self.setProperty("active", False)

    def set_active(self, on):
        if self.property("active") != on:
            self.setProperty("active", on)
            self.style().unpolish(self)
            self.style().polish(self)


# ════════════════════════════════════════════════
#  メインウィンドウ
# ════════════════════════════════════════════════
class MDViewerPro(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MD Viewer Pro")
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
        self._last_pdf_dir     = _s["last_pdf_dir"]
        self._content_text     = ""
        self._palette          = DARK_PALETTE
        self._plugin_themes: Dict[str, dict] = {}
        self._image_cache: Dict[str, str] = {}
        self._readonly_file    = False
        self._saved_scroll_y   = 0
        self._restore_scroll_pending = False
        self._initial_file: Optional[str] = None

        # UI スケール管理
        self._last_ui_scale_cat = "large"

        # プラグインテーマ読み込み
        self._plugin_themes = load_plugin_themes()

        af = QFont(self.ui_font_family if self.ui_font_family else "Helvetica Neue")
        af.setPointSize(15)
        af.setBold(True)
        QApplication.setFont(af)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._flush_preview)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(80)
        self._resize_timer.timeout.connect(self._apply_responsive_style)

        self._build_ui()

        self._loader = SafeWebLoader(self._preview_web, dark=True)

        self._bridge = ContentBridge(self._on_md_content_changed, self)
        self._channel = QWebChannel(self)
        self._channel.registerObject("bridge", self._bridge)
        self._md_page.setWebChannel(self._channel)

        self._apply_theme(refresh=False)

        self._startup_done = False
        self._preview_web.loadFinished.connect(self._on_initial_load_finished)
        self._loader.load_html("<html><body></body></html>")

        # フォールバック: WebEngine が loadFinished を発火しない場合の保険
        self._startup_fallback = QTimer(self)
        self._startup_fallback.setSingleShot(True)
        self._startup_fallback.setInterval(4000)
        self._startup_fallback.timeout.connect(self._ensure_startup)
        self._startup_fallback.start()

        # MDApplication に自身を登録（QFileOpenEvent 対応）
        app_inst = QApplication.instance()
        if isinstance(app_inst, MDApplication):
            app_inst._main_win = self

    def _t(self, key):
        return (I18N[self.lang].get(key)
                or I18N["ja"].get(key)
                or key)

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

        self._editor_stack = QStackedWidget()
        self._view_placeholder = QWidget()
        self._editor_stack.addWidget(self._view_placeholder)
        self._md_editor = QPlainTextEdit()
        self._md_editor.textChanged.connect(self._on_editor_changed)
        self._editor_stack.addWidget(self._md_editor)
        self._splitter.addWidget(self._editor_stack)

        self._md_page = MDWebPage()
        self._preview_web = QWebEngineView()
        self._preview_web.setPage(self._md_page)
        self._splitter.addWidget(self._preview_web)

        self._splitter.setSizes([0, 1])
        self._build_menu()

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

        self._pdf_btn = PianoBtn(self._t("pdf_export"))
        self._pdf_btn.setObjectName("mainBtn")
        self._pdf_btn.clicked.connect(self._export_pdf)
        lay.addWidget(self._pdf_btn)

        lay.addStretch(1)
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
                        self._md_prefix(_tp)
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
        fb("fmt_code",   txt_wrap="wrap",   txt_pre="`",       txt_post="`",
           md_js="(function(){var s=window.getSelection();if(s&&s.rangeCount){var r=s.getRangeAt(0);var t=r.toString()||'code';r.deleteContents();var c=document.createElement('code');c.textContent=t;r.insertNode(c);var w=document.querySelector('.wrap');if(w)w.dispatchEvent(new Event('input',{bubbles:true}));}})();")
        fs()
        fb("fmt_h1",     txt_wrap="prefix", txt_pre="# ",      md_block="h1")
        fb("fmt_h2",     txt_wrap="prefix", txt_pre="## ",     md_block="h2")
        fb("fmt_h3",     txt_wrap="prefix", txt_pre="### ",    md_block="h3")
        fs()
        fb("fmt_list",   txt_wrap="prefix", txt_pre="- ",      md_cmd="insertUnorderedList")
        fb("fmt_num",    txt_wrap="prefix", txt_pre="1. ",     md_cmd="insertOrderedList")
        fb("fmt_check",  txt_wrap="prefix", txt_pre="- [ ] ",
           md_js="(function(){var w=document.querySelector('.wrap');if(w){document.execCommand('insertHTML',false,'<p>☐ テキスト</p>');w.dispatchEvent(new Event('input',{bubbles:true}));}})();")
        fs()
        fb("fmt_quote",  txt_wrap="prefix", txt_pre="> ",      md_block="blockquote")
        fb("fmt_hr",     txt_wrap="insert", txt_pre="\n---\n", md_cmd="insertHorizontalRule")
        fb("fmt_link",   txt_wrap="insert", txt_pre="[テキスト](URL)",
           md_js="(function(){var u=prompt('URL','https://');if(u)document.execCommand('createLink',false,u);var w=document.querySelector('.wrap');if(w)w.dispatchEvent(new Event('input',{bubbles:true}));})();")
        fb("fmt_img",    txt_wrap="insert", txt_pre="![説明](URL)",
           md_js="(function(){var u=prompt('画像URL','https://');if(u)document.execCommand('insertImage',false,u);var w=document.querySelector('.wrap');if(w)w.dispatchEvent(new Event('input',{bubbles:true}));})();")
        fs()

        # テーブルボタン（特殊）
        tbl_btn = PianoBtn(self._t("fmt_table"))
        tbl_btn.setObjectName("fmtBtn")
        def on_table():
            if self.edit_mode == "txt":
                self._md_insert_table()
            elif self.edit_mode == "md":
                tbl_html = (
                    "<table><thead><tr><th>列1</th><th>列2</th><th>列3</th></tr></thead>"
                    "<tbody><tr><td>セル</td><td>セル</td><td>セル</td></tr>"
                    "<tr><td>セル</td><td>セル</td><td>セル</td></tr></tbody></table>"
                )
                self._preview_web.page().runJavaScript(
                    f"(function(){{document.execCommand('insertHTML',false,{json.dumps(tbl_html)});"
                    "var w=document.querySelector('.wrap');if(w)w.dispatchEvent(new Event('input',{bubbles:true}));}})()"
                )
        tbl_btn.clicked.connect(on_table)
        lay.addWidget(tbl_btn)

        lay.addStretch(1)
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

    def _get_ui_scale_cat(self):
        w = self.width()
        if w >= 1100: return "large"
        elif w >= 780: return "medium"
        else:          return "small"

    def _apply_responsive_style(self):
        cat = self._get_ui_scale_cat()
        if cat == self._last_ui_scale_cat:
            return
        self._last_ui_scale_cat = cat

        if cat == "large":
            tb_h, fmt_h = TB_H, FMT_H
        elif cat == "medium":
            tb_h, fmt_h = 50, 38
        else:
            tb_h, fmt_h = 40, 32

        self._main_tb.setFixedHeight(tb_h)
        self._fmt_tb.setFixedHeight(fmt_h)
        self._fmt_container.setFixedHeight(fmt_h)
        self._apply_theme(refresh=False)

    def _ui_sizes(self):
        cat = self._get_ui_scale_cat()
        if cat == "large":
            return {"tb_fs": 17, "btn_pad": "0 20px", "fmt_fs": 16,
                    "fmt_pad": "0 13px", "lbl_fs": 15, "min_w": 68}
        elif cat == "medium":
            return {"tb_fs": 14, "btn_pad": "0 12px", "fmt_fs": 13,
                    "fmt_pad": "0 8px",  "lbl_fs": 12, "min_w": 50}
        else:
            return {"tb_fs": 12, "btn_pad": "0 7px",  "fmt_fs": 11,
                    "fmt_pad": "0 5px",  "lbl_fs": 10, "min_w": 36}

    # ════════════════════════════════════════════
    #  HTML ビルダー
    # ════════════════════════════════════════════
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
            'var code=pre.querySelector("code")||pre;'
            'var text=(code.innerText||code.textContent||"");'
            'function fb(){'
            'var ta=document.createElement("textarea");'
            'ta.value=text;'
            'ta.style.cssText="position:fixed;top:0;left:0;opacity:0;pointer-events:none;";'
            'document.body.appendChild(ta);ta.focus();ta.select();'
            'try{document.execCommand("copy");}catch(e){}'
            'document.body.removeChild(ta);}'
            'if(navigator.clipboard&&navigator.clipboard.writeText){'
            'navigator.clipboard.writeText(text).then(function(){})'
            '.catch(fb);}else{fb();}'
            'var orig=btn.textContent;'
            'btn.textContent="✓";btn.style.opacity="1";'
            'setTimeout(function(){btn.textContent=orig;btn.style.opacity="";},1500);}'
            'window.addEventListener("load",function(){'
            'document.querySelectorAll("pre").forEach(function(p){'
            'if(p.querySelector(".mdv-copy-btn"))return;'
            'var b=document.createElement("button");'
            'b.className="mdv-copy-btn";'
            'b.textContent="copy";'
            'b.setAttribute("type","button");'
            'b.onclick=function(e){e.stopPropagation();_mdvCopy(this);};'
            'p.appendChild(b);});});'
            '</script>'
        )

    @staticmethod
    def _md_edit_fmt_js():
        """MD編集モード用の書式JS関数群"""
        return (
            '<script>'
            'window._mdvExec=function(cmd){'
            'document.execCommand(cmd,false,null);'
            'var w=document.querySelector(".wrap");'
            'if(w)w.dispatchEvent(new Event("input",{bubbles:true}));'
            '};'
            'window._mdvBlock=function(tag){'
            'document.execCommand("formatBlock",false,tag);'
            'var w=document.querySelector(".wrap");'
            'if(w)w.dispatchEvent(new Event("input",{bubbles:true}));'
            '};'
            '</script>'
        )

    def _css(self, fs):
        p  = self._palette
        fw = "600" if self.bold_mode else "400"
        ff = ("'Helvetica Neue', '-apple-system', "
              "'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif")
        if self.ui_font_family and self.ui_font_family not in ("Helvetica Neue", "-apple-system"):
            ff = f"'{self.ui_font_family}', " + ff
        return (
            "*{box-sizing:border-box;margin:0;padding:0}"
            f"html,body{{background:{p['bg']};color:{p['text']};"
            f"font-family:{ff};font-size:{fs}px;line-height:1.8;font-weight:{fw};}}"
            f"h1{{font-size:{int(fs*1.85)}px;color:{p['heading']};"
            f"border-bottom:2px solid {p['border']};padding-bottom:8px;margin:28px 0 16px}}"
            f"h2{{font-size:{int(fs*1.4)}px;color:{p['heading']};"
            f"border-bottom:1px solid {p['border']};padding-bottom:5px;margin:22px 0 12px}}"
            f"h3{{font-size:{int(fs*1.15)}px;color:{p['heading']};margin:18px 0 10px}}"
            f"h4,h5,h6{{color:{p['heading']};margin:14px 0 8px}}"
            "p{margin:10px 0}"
            f"a{{color:{p['accent']};text-decoration:none}}"
            "a:hover{text-decoration:underline}"
            f"code{{background:{p['bg3']};color:{p['code_fg']};"
            "padding:2px 6px;border-radius:3px;"
            "font-family:'Menlo','Monaco',monospace;font-size:.88em}"
            f"pre{{position:relative;background:{p['bg3']};border:1px solid {p['border']};"
            "border-radius:6px;padding:16px;overflow-x:auto;margin:14px 0}"
            f"pre code{{background:none;padding:0;color:{p['text']}}}"
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
            f"table{{border-collapse:collapse;width:100%;margin:16px 0}}"
            f"th,td{{border:1px solid {p['border']};padding:9px 14px;text-align:left}}"
            f"th{{background:{p['bg3']};color:{p['heading']};font-weight:700}}"
            f"tr:nth-child(even){{background:{p['row_even']}}}"
            "ul,ol{padding-left:1.7em;margin:10px 0}"
            "li{margin:4px 0}"
            f"hr{{border:none;border-top:1px solid {p['border']};margin:24px 0}}"
            "img{max-width:100%;border-radius:4px}"
            ".task-list-item{list-style:none;margin-left:-1.4em}"
            ".task-list-item input[type='checkbox']{margin-right:6px;vertical-align:middle}"
        )

    @staticmethod
    def _page_break_js(page_height_mm):
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
            f's.textContent=(i+1)+" ページ目";'
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

    def _build_md_html(self, text, editable=False):
        p   = self._palette
        fs  = int(16 * SCALE_STEPS[self.scale_idx])
        body = markdown.markdown(
            text,
            extensions=["tables", "fenced_code", "codehilite"],
            extension_configs={"codehilite": {"guess_lang": False, "noclasses": True}},
        )
        body = self._render_checklist(body)
        body = self._embed_remote_images(body)

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
                f"@page{{size:{page_css_name} portrait;"
                f"margin:{t}mm {r}mm {b}mm {l}mm;}}"
                f"body{{margin:0!important;background:{p['bg']}!important;}}"
                f".wrap{{max-width:100%!important;margin:0!important;"
                f"padding:0!important;box-shadow:none!important;"
                f"min-height:auto!important;background:{p['bg']}!important;}}"
                f".pg-brk{{display:none!important;}}"
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
                f"@page{{size:{page_w}mm {page_h}mm portrait;"
                f"margin:{t}mm {r}mm {b}mm {l}mm;}}"
                f"body{{margin:0!important;background:{p['bg']}!important;}}"
                f".wrap{{max-width:100%!important;margin:0!important;"
                f"padding:0!important;box-shadow:none!important;"
                f"min-height:auto!important;background:{p['bg']}!important;}}"
                f".pg-brk{{display:none!important;}}"
                f"}}"
            )
            pg_js = self._page_break_js(page_h)
        else:
            wrap = "padding:32px 48px;max-width:920px;margin:0 auto;"
            print_css = (
                f"@media print{{@page{{margin:15mm;}}"
                f"body{{background:{p['bg']}!important;}}"
                f".wrap{{background:{p['bg']}!important;}}}}"
            )
            pg_js = ""

        editable_css = ""
        if editable:
            editable_css = (
                f".wrap[contenteditable]{{cursor:text;caret-color:{p['accent']}}}"
                ".wrap[contenteditable]:focus{outline:none}"
                ".mdv-copy-btn{display:none}"
            )

        css = self._css(fs) + f".wrap{{{wrap}}}" + print_css + editable_css

        wrap_attrs = ' contenteditable="true" spellcheck="false"' if editable else ""

        webchannel_js = ""
        if editable:
            webchannel_js = (
                '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'
                '<script>'
                'document.addEventListener("DOMContentLoaded",function(){'
                'if(typeof QWebChannel==="undefined")return;'
                'new QWebChannel(qt.webChannelTransport,function(ch){'
                'var br=ch.objects.bridge;'
                'var w=document.querySelector(".wrap");'
                'if(!w)return;'
                'var tmr=null;'
                'w.addEventListener("input",function(){'
                'clearTimeout(tmr);'
                'tmr=setTimeout(function(){br.contentChanged(w.innerHTML);},400);'
                '});'
                '});});'
                '</script>'
            )

        return (
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<style>{css}</style></head>'
            f'<body><div class="wrap"{wrap_attrs}>{body}</div>'
            f'{pg_js}'
            f'{self._copy_code_btn_js()}'
            f'{(self._md_edit_fmt_js() if editable else "")}'
            f'{webchannel_js}'
            f'{("" if editable else self._copy_plain_js())}'
            '</body></html>'
        )

    def _build_txt_html(self, text):
        return self._build_md_html(text, editable=False)

    def _html_to_markdown(self, html_content: str) -> str:
        processed = html_content
        for url, data_uri in self._image_cache.items():
            processed = processed.replace(data_uri, url)
        return _html_to_md(processed)

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
            f"padding:14px;border:none;"
            f"selection-background-color:{p['select']};}}"
        )

        sz = self._ui_sizes()
        tb_fs   = sz["tb_fs"]
        btn_pad = sz["btn_pad"]
        fmt_fs  = sz["fmt_fs"]
        fmt_pad = sz["fmt_pad"]
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
            f"QCheckBox{{font-size:{lbl_fs}px;font-weight:bold;color:{p['text']};}}"
            f"QDialogButtonBox QPushButton{{background-color:{p['btn']};color:{p['text']};"
            f"border:1px solid {p['sep']};border-radius:4px;padding:6px 20px;"
            f"font-weight:bold;font-size:{lbl_fs}px;min-width:70px;}}"
            f"QDialogButtonBox QPushButton:hover{{background-color:{p['accent']};"
            f"color:#ffffff;border-color:{p['accent']};}}"
        )

        self.setStyleSheet(app_ss)
        self._md_editor.setStyleSheet(editor_ss)
        if hasattr(self, "_loader"):
            self._loader.set_background(p["bg"])
        self._sync_tb_labels()
        self._refresh_btn_states()
        if refresh:
            self._refresh_view()

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
        self._pdf_btn.setText(self._t("pdf_export"))

    def _refresh_btn_states(self):
        for k, b in self._mode_btns.items():
            b.set_active(k == self.edit_mode)
            if self._readonly_file and k in ("md", "txt"):
                b.setEnabled(False)
            else:
                b.setEnabled(True)
        for k, b in self._layout_btns.items():
            b.set_active(k == self.page_mode)
        self._back_btn.setEnabled(self.edit_mode != "view")
        self._margin_btn.setEnabled(self.page_mode in ("a4", "b5"))
        self._scale_val_lbl.setText(SCALE_LABELS[self.scale_idx])

    # ════════════════════════════════════════════
    #  表示更新
    # ════════════════════════════════════════════
    def _refresh_view(self):
        text = self._content_text
        editable = (self.edit_mode == "md")
        html = self._build_md_html(text, editable=editable)
        base_path = None
        if self.current_file_path:
            base_path = os.path.dirname(os.path.abspath(self.current_file_path)) + os.sep
        self._loader.load_html(html, base_path)

    def _on_editor_changed(self):
        if self.edit_mode != "txt":
            return
        self._content_text = self._md_editor.toPlainText()
        self._auto_fetch_new_images(self._content_text)
        self.is_modified = True
        self._update_title()
        self._timer.start()

    def _on_md_content_changed(self, html_content: str):
        if self.edit_mode != "md":
            return
        self._content_text = self._html_to_markdown(html_content)
        self.is_modified = True
        self._update_title()

    def _flush_preview(self):
        if self.edit_mode == "txt":
            self._preview_web.page().runJavaScript(
                "document.documentElement.scrollTop || document.body.scrollTop || 0;",
                self._do_flush_preserve_scroll
            )
        else:
            self._refresh_view()

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
        for url in urls:
            if url not in self._image_cache:
                result = _safe_fetch_image(url)
                if result:
                    mime, data = result
                    b64 = base64.b64encode(data).decode("ascii")
                    self._image_cache[url] = f"data:{mime};base64,{b64}"

    def _auto_fetch_new_images(self, text: str):
        new_urls = [u for u in _extract_remote_image_urls(text)
                    if u not in self._image_cache]
        if new_urls:
            self._fetch_remote_images(new_urls)

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
    def _set_mode(self, mode):
        if self._readonly_file and mode in ("md", "txt"):
            return
        if self.edit_mode == mode:
            return
        self._timer.stop()
        if self.edit_mode == "md":
            self._pending_mode = mode
            self._preview_web.page().runJavaScript(
                "var w=document.querySelector('.wrap');w?w.innerHTML:'';",
                lambda html: self._finish_mode_switch_from_md(html, mode)
            )
        else:
            self._save_buf()
            self._do_set_mode(mode)

    def _finish_mode_switch_from_md(self, html_content, mode):
        if html_content:
            self._content_text = self._html_to_markdown(html_content)
        self._do_set_mode(mode)

    def _do_set_mode(self, mode):
        self.edit_mode = mode
        idx = 1 if mode == "txt" else 0
        self._editor_stack.setCurrentIndex(idx)

        # 書式ツールバーはTXT編集・MD編集モードの両方で表示
        self._fmt_container.setVisible(mode in ("txt", "md"))

        if mode in ("view", "md"):
            self._splitter.setSizes([0, 1])
        else:
            self._splitter.setSizes([480, 720])

        self._md_page.set_mode(mode)

        if mode == "txt":
            self._md_editor.blockSignals(True)
            self._md_editor.setPlainText(self._content_text)
            self._md_editor.blockSignals(False)

        self._refresh_btn_states()
        self._refresh_view()

    def _go_back(self):
        self._set_mode("view")

    def _save_buf(self):
        if self.edit_mode == "txt":
            self._content_text = self._md_editor.toPlainText()

    def _set_layout(self, layout):
        self.page_mode = layout
        self._refresh_btn_states()
        self._refresh_view()

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
            self._refresh_view()

    def _on_scale_slider(self, v):
        self.scale_idx = v
        self._scale_val_lbl.setText(SCALE_LABELS[v])
        self._apply_theme(refresh=False)
        self._timer.start()

    def _save_app_settings(self):
        save_settings({
            "lang":        self.lang,
            "theme":       self.current_theme,
            "font_family": self.ui_font_family,
            "bold_mode":   self.bold_mode,
            "scale_idx":   self.scale_idx,
            "last_pdf_dir": self._last_pdf_dir,
        })

    def _open_settings(self):
        # プラグインを再スキャン
        self._plugin_themes = load_plugin_themes()
        dlg = SettingsDialog(
            self, self.ui_font_family, self.lang,
            self.current_theme, self.bold_mode,
            I18N[self.lang], self._plugin_themes,
        )
        if dlg.exec():
            fam, lang, theme, bold = dlg.get_result()
            self.ui_font_family = fam
            changed_lang = (lang != self.lang)
            self.lang      = lang
            self.bold_mode = bold
            self.current_theme = theme
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
        sel = cur.selectedText().replace("\u2029", "\n") or "テキスト"
        cur.insertText(f"{pre}{sel}{post}")
        self._md_editor.setTextCursor(cur)
        self._md_editor.setFocus()

    def _md_prefix(self, prefix):
        cur = self._md_editor.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cur.insertText(prefix)
        cur.movePosition(QTextCursor.MoveOperation.EndOfLine)
        self._md_editor.setTextCursor(cur)
        self._md_editor.setFocus()

    def _md_insert(self, text):
        cur = self._md_editor.textCursor()
        cur.insertText(text)
        self._md_editor.setTextCursor(cur)
        self._md_editor.setFocus()

    def _md_insert_table(self):
        self._md_insert(
            "\n| 列1 | 列2 | 列3 |\n"
            "| :--- | :--- | :--- |\n"
            "| セル | セル | セル |\n"
            "| セル | セル | セル |\n"
        )

    # ════════════════════════════════════════════
    #  PDF書き出し
    # ════════════════════════════════════════════
    def _export_pdf(self):
        self._save_buf()
        dlg = PdfExportDialog(
            self, self.page_mode,
            self.a4_margins, self.b5_margins,
            I18N[self.lang]
        )
        if not dlg.exec():
            return
        page_size_name, landscape, margins = dlg.get_settings()
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

        def _on_pdf_done(pdf_path, ok):
            try:
                self._preview_web.page().pdfPrintingFinished.disconnect(_on_pdf_done)
            except Exception:
                pass
            if ok:
                QMessageBox.information(self, "PDF", self._t("pdf_success"))
            else:
                QMessageBox.warning(self, "PDF", self._t("pdf_error"))

        self._preview_web.page().pdfPrintingFinished.connect(_on_pdf_done)
        self._preview_web.page().printToPdf(path, layout)

    # ════════════════════════════════════════════
    #  HTML書き出し
    # ════════════════════════════════════════════
    def _export_html(self):
        self._save_buf()
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
    def _on_initial_load_finished(self, ok):
        if not self._startup_done:
            self._startup_fallback.stop()
            self._startup_done = True
            try:
                self._preview_web.loadFinished.disconnect(self._on_initial_load_finished)
            except Exception:
                pass
            QTimer.singleShot(0, self._startup_open)

    def _ensure_startup(self):
        """フォールバック: loadFinished が発火しない場合"""
        if not self._startup_done:
            self._startup_done = True
            try:
                self._preview_web.loadFinished.disconnect(self._on_initial_load_finished)
            except Exception:
                pass
            self._startup_open()

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
                "Markdown / Text (*.md *.txt);;All Files (*)"
            )
            if path:
                self._load_file(path)
            else:
                self._set_sample()
                self._refresh_view()
        elif result and dlg.action == StartupDialog.ACTION_GUIDE:
            self._open_guide()
        else:
            self._set_sample()
            self._refresh_view()

    # ════════════════════════════════════════════
    #  ファイル操作
    # ════════════════════════════════════════════
    def file_new(self):
        if not self._maybe_save():
            return
        self._readonly_file = False
        self._content_text = ""
        self.current_file_path = None
        self.is_modified = False
        self._md_editor.blockSignals(True)
        self._md_editor.setPlainText("")
        self._md_editor.blockSignals(False)
        self._do_set_mode("txt")
        self._update_title()

    def _load_file(self, path):
        text = None
        for enc in ("utf-8-sig", "utf-8", "shift_jis", "cp932", "euc-jp", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    text = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if text is None:
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                text = raw.decode("utf-8", errors="replace")
            except Exception as e:
                QMessageBox.warning(self, self._t("read_error"), str(e))
                return
        self._content_text = text
        self._md_editor.blockSignals(True)
        self._md_editor.setPlainText(text)
        self._md_editor.blockSignals(False)
        self.current_file_path = path
        self.is_modified = False
        self._update_title()
        self.edit_mode = "view"
        self._md_page.set_mode("view")
        self._editor_stack.setCurrentIndex(0)
        self._splitter.setSizes([0, 1])
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
            "Markdown / Text (*.md *.txt);;All Files (*)"
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
            "Markdown (*.md);;Text (*.txt);;All Files (*)"
        )
        if path:
            self._save_buf()
            ok = self._write(path)
            if ok:
                self.current_file_path = path
                self._update_title()
            return ok
        return False

    def _write(self, path) -> bool:
        self._save_buf()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._content_text)
        except Exception as e:
            QMessageBox.warning(self, self._t("save_error"), str(e))
            return False
        self.is_modified = False
        self._update_title()
        return True

    def _maybe_save(self) -> bool:
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
        self.setWindowTitle(f"{name}{mark}{ro} — MD Viewer Pro")

    def _set_sample(self):
        s = (
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
        )
        self._content_text = s
        self._md_editor.blockSignals(True)
        self._md_editor.setPlainText(s)
        self._md_editor.blockSignals(False)
        self.is_modified = False
        self._update_title()

    def _open_guide(self):
        """選択中の言語のsampleファイルを読み取り専用で開く"""
        lang_to_file = {
            "ja": "sample_日本語.md",
            "en": "sample_English.md",
            "de": "sample_Deutsch.md",
            "fr": "sample_français.md",
        }
        filename = lang_to_file.get(self.lang, "sample_English.md")
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

    def closeEvent(self, event):
        self._timer.stop()
        self._resize_timer.stop()
        if self._maybe_save():
            self._save_app_settings()
            self._loader.cleanup()
            event.accept()
        else:
            event.ignore()


# ════════════════════════════════════════════════
if __name__ == "__main__":
    app = MDApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
    app.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    win = MDViewerPro()
    win.show()

    # コマンドライン引数でファイルが指定された場合
    args = app.arguments()
    if len(args) > 1:
        _arg_path = args[1]
        if os.path.isfile(_arg_path):
            win._initial_file = _arg_path

    sys.exit(app.exec())
