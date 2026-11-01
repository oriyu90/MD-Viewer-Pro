//! Tauri コマンド層。UI から呼べる操作はここに集約し、権限は capability で絞る。

use std::path::{Path, PathBuf};

use mdv_core::doc::{self, Document};
use mdv_core::render::{render_markdown, RenderOptions, Rendered};
use mdv_core::settings::{self, Settings};
use mdv_core::theme::{self, effective_accent, effective_heading, hex_is_dark, palette_for, Palette, ThemeMode};
use serde::Serialize;
use tauri::{AppHandle, Manager, State, WebviewWindow};

use crate::state::{self, AppState, OpenDocument, MAX_CLIPS, MAX_CLIP_LEN};

fn version_label(v: &str) -> String {
    if let Some(pos) = v.find("-alpha.") {
        return format!("α{}", &v[pos + 7..]);
    }
    if let Some(pos) = v.find("-beta.") {
        return format!("β{}", &v[pos + 6..]);
    }
    v.to_string()
}

#[derive(Serialize)]
pub struct Paths {
    pub config: String,
    pub themes: String,
    pub fonts: String,
    pub clips: String,
}

#[derive(Serialize)]
pub struct Bootstrap {
    pub version: String,
    pub version_label: String,
    pub settings: Settings,
    pub palette: Palette,
    pub accent: String,
    pub heading: String,
    pub dark: bool,
    pub fonts: Vec<String>,
    pub themes: Vec<ThemeInfo>,
    pub recent: Vec<String>,
    pub paths: Paths,
    pub platform: String,
    pub default_fonts: Vec<String>,
    pub selftest_fixture: Option<String>,
    pub screenshot: Option<ScreenshotArgs>,
    pub pdf_export: Option<(String, String)>,
    pub dialog: Option<String>,
    pub initial: Option<String>,
}

#[derive(Serialize, Clone, Debug)]
pub struct ScreenshotArgs {
    pub output: String,
    pub mode: String,
    pub theme: String,
    pub page: String,
}

#[derive(Serialize, Clone)]
pub struct ThemeInfo {
    pub name: String,
    pub accent: String,
    pub dark: bool,
}

#[derive(Serialize)]
pub struct OpenedDoc {
    pub path: Option<String>,
    pub source: String,
    pub kind: String,
    pub readonly: bool,
    pub warning: Option<String>,
    pub rendered: Rendered,
}

fn dark_now() -> bool {
    #[cfg(target_os = "macos")]
    {
        if let Ok(out) = std::process::Command::new("defaults")
            .args(["read", "-g", "AppleInterfaceStyle"])
            .output()
        {
            return String::from_utf8_lossy(&out.stdout).to_lowercase().contains("dark");
        }
        false
    }
    #[cfg(not(target_os = "macos"))]
    {
        true
    }
}

fn plugin_palettes() -> std::collections::BTreeMap<String, Palette> {
    let mut out = std::collections::BTreeMap::new();
    let Ok(entries) = std::fs::read_dir(state::themes_dir()) else {
        return out;
    };
    for entry in entries.flatten() {
        let p = entry.path();
        if p.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        let Ok(text) = std::fs::read_to_string(&p) else { continue };
        let Ok(v) = serde_json::from_str::<serde_json::Value>(&text) else { continue };
        let Some(obj) = v.as_object() else { continue };
        let mut map = std::collections::BTreeMap::new();
        for (k, val) in obj {
            if let Some(s) = val.as_str() {
                map.insert(k.clone(), s.to_string());
            }
        }
        let name = obj
            .get("name")
            .and_then(|n| n.as_str())
            .map(|s| s.to_string())
            .or_else(|| p.file_stem().map(|s| s.to_string_lossy().to_string()))
            .unwrap_or_default();
        if let Some(pal) = theme::palette_from_map(&map) {
            out.insert(name, pal);
        }
    }
    out
}

fn build_palette(s: &Settings) -> (Palette, String, String, bool) {
    let plugins = plugin_palettes();
    let (base, dark) = match s.theme.as_str() {
        "light" => (theme::light_palette(), false),
        "system" => {
            let d = dark_now();
            (palette_for(ThemeMode::System, d), d)
        }
        "dark" => (theme::dark_palette(), true),
        name => match plugins.get(name) {
            Some(p) => (p.clone(), hex_is_dark(&p.bg)),
            None => (theme::dark_palette(), true),
        },
    };
    let accent = effective_accent(&s.accent_color, dark);
    let heading = effective_heading(&accent, dark, if dark { "#c0c0c0" } else { "#000000" });
    let mut p = base;
    p.accent = accent.clone();
    p.heading = heading.clone();
    p.select = theme::mix_hex(&accent, &p.bg, 0.72);
    (p, accent, heading, dark)
}

#[tauri::command]
pub fn bootstrap(state: State<'_, AppState>) -> Bootstrap {
    let s = state.settings.lock().unwrap().clone();
    let (palette, accent, heading, dark) = build_palette(&s);
    let themes = read_themes();
    Bootstrap {
        version: env!("CARGO_PKG_VERSION").to_string(),
        version_label: version_label(env!("CARGO_PKG_VERSION")),
        settings: s,
        palette,
        accent,
        heading,
        dark,
        fonts: state.fonts.lock().unwrap().clone(),
        themes,
        recent: Vec::new(),
        paths: Paths {
            config: state::app_dir().to_string_lossy().to_string(),
            themes: state::themes_dir().to_string_lossy().to_string(),
            fonts: state::fonts_dir().to_string_lossy().to_string(),
            clips: state::clips_path().to_string_lossy().to_string(),
        },
        selftest_fixture: selftest_fixture(),
        screenshot: screenshot_args(),
        pdf_export: pdf_export_args(),
        dialog: dialog_arg(),
        initial: std::env::args()
            .skip(1)
            .find(|a| !a.starts_with('-') && std::path::Path::new(a).is_file())
            ,
        platform: std::env::consts::OS.to_string(),
        default_fonts: vec![
            "Helvetica Neue".into(),
            "Hiragino Sans".into(),
            "Hiragino Mincho ProN".into(),
            "IPAmj明朝".into(),
            "Source Han Serif".into(),
            "Times New Roman".into(),
        ],
    }
}

fn dialog_arg() -> Option<String> {
    let args: Vec<String> = std::env::args().collect();
    let i = args.iter().position(|a| a == "--dialog")?;
    args.get(i + 1).cloned()
}

fn pdf_export_args() -> Option<(String, String)> {
    let args: Vec<String> = std::env::args().collect();
    let i = args.iter().position(|a| a == "--export-pdf")?;
    Some((args.get(i + 1)?.clone(), args.get(i + 2)?.clone()))
}

pub fn screenshot_args() -> Option<ScreenshotArgs> {
    let args: Vec<String> = std::env::args().collect();
    let i = args.iter().position(|a| a == "--screenshot")?;
    let output = args.get(i + 1)?.clone();
    let get = |flag: &str, default: &str| -> String {
        args.iter()
            .position(|a| a == flag)
            .and_then(|j| args.get(j + 1))
            .cloned()
            .unwrap_or_else(|| default.to_string())
    };
    Some(ScreenshotArgs {
        output,
        mode: get("--mode", "view"),
        theme: get("--theme", "dark"),
        page: get("--page", "free"),
    })
}

fn selftest_fixture() -> Option<String> {
    if !std::env::args().any(|a| a == "--selftest") {
        return None;
    }
    let path = std::env::temp_dir().join("mdvp-selftest.md");
    let body = "# 自動作成ドキュメント\n\nこれはセルフテスト用の本文です。\n\n## 節\n\n- 箇条書き\n- 二つ目\n\n| 列A | 列B |\n|---|---|\n| 1 | 2 |\n";
    std::fs::write(&path, body).ok()?;
    Some(path.to_string_lossy().to_string())
}

fn open_document(state: &AppState, label: &str, path: &Path) -> Result<OpenedDoc, String> {
    let (mut d, warning) = Document::from_path(path).map_err(|e| e.to_string())?;
    d.bump();
    let s = state.settings.lock().unwrap().clone();
    let rendered = render_markdown(&d.source, RenderOptions {
        hard_breaks: s.hard_breaks,
        allow_raw_html: true,
    });
    state.approve(path);
    let out = OpenedDoc {
        path: Some(path.to_string_lossy().to_string()),
        source: d.source.clone(),
        kind: if d.kind.is_yaml() { "yaml".into() } else { "md".into() },
        readonly: d.readonly,
        warning,
        rendered,
    };
    state.doc.lock().unwrap().insert(
        label.to_string(),
        OpenDocument { path: Some(path.to_path_buf()), source: d.source.clone(), dirty: false },
    );
    Ok(out)
}

#[tauri::command]
pub fn open_path(state: State<'_, AppState>, window: WebviewWindow, path: String) -> Result<OpenedDoc, String> {
    let mut s = state.settings.lock().unwrap().clone();
    let p = PathBuf::from(&path);
    if let Some(dir) = p.parent() {
        s.last_dir = dir.to_string_lossy().to_string();
    }
    s.recent.retain(|r| r != &path);
    s.recent.insert(0, path.clone());
    s.recent.truncate(12);
    *state.settings.lock().unwrap() = s.clone();
    let _ = settings::save(&s);
    if let Some(name) = p.file_name().and_then(|s| s.to_str()) {
        let _ = window.set_title(&format!("{name} — MD Viewer Pro {}", version_label(env!("CARGO_PKG_VERSION"))));
    }
    open_document(&state, window.label(), &p)
}

#[tauri::command]
pub fn new_window(app: AppHandle) -> Result<(), String> {
    use std::sync::atomic::{AtomicU32, Ordering};
    static COUNTER: AtomicU32 = AtomicU32::new(1);
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let label = format!("win-{n}");
    tauri::WebviewWindowBuilder::new(&app, &label, tauri::WebviewUrl::App("index.html".into()))
        .title("MD Viewer Pro")
        .inner_size(1280.0, 900.0)
        .min_inner_size(480.0, 360.0)
        .build()
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn pick_file(state: State<'_, AppState>) -> Option<String> {
    let p = rfd::FileDialog::new()
        .add_filter("Markdown / Text / YAML", &["md", "markdown", "txt", "yml", "yaml"])
        .add_filter("All Files", &["*"])
        .pick_file()?;
    state.approve(&p);
    Some(p.to_string_lossy().to_string())
}

#[tauri::command]
pub fn pick_save(state: State<'_, AppState>, suggested: String) -> Option<String> {
    let p = rfd::FileDialog::new()
        .set_file_name(&suggested)
        .add_filter("Markdown", &["md"])
        .add_filter("Text", &["txt"])
        .add_filter("HTML", &["html"])
        .save_file()?;
    state.approve(&p);
    Some(p.to_string_lossy().to_string())
}

#[tauri::command]
pub fn read_file_text(path: String) -> Result<String, String> {
    let (s, _w) = doc::read_file(Path::new(&path)).map_err(|e| e.to_string())?;
    Ok(s)
}

#[tauri::command]
pub fn render(source: String, hard_breaks: bool) -> Rendered {
    render_markdown(&source, RenderOptions { hard_breaks, allow_raw_html: true })
}

#[tauri::command]
pub fn save_document(
    state: State<'_, AppState>,
    window: WebviewWindow,
    path: Option<String>,
    source: String,
) -> Result<String, String> {
    let target = match path {
        Some(p) if !p.is_empty() => PathBuf::from(p),
        _ => return Err("保存先が指定されていません".into()),
    };
    if !state.is_approved(&target) {
        return Err("保存先が許可されていません（保存ダイアログから選び直してください）".into());
    }
    doc::write_file(&target, &source).map_err(|e| e.to_string())?;
    {
        let mut d = state.doc.lock().unwrap();
        if let Some(doc) = d.get_mut(window.label()) {
            doc.source = source.clone();
            doc.path = Some(target.clone());
            doc.dirty = false;
        }
    }
    if let Some(name) = target.file_name().and_then(|s| s.to_str()) {
        let _ = window.set_title(&format!("{name} — MD Viewer Pro {}", version_label(env!("CARGO_PKG_VERSION"))));
    }
    let mut s = state.settings.lock().unwrap().clone();
    let p = target.to_string_lossy().to_string();
    if let Some(dir) = target.parent() {
        s.last_dir = dir.to_string_lossy().to_string();
    }
    s.recent.retain(|r| r != &p);
    s.recent.insert(0, p.clone());
    s.recent.truncate(12);
    *state.settings.lock().unwrap() = s.clone();
    let _ = settings::save(&s);
    Ok(p)
}

#[tauri::command]
pub fn save_text(state: State<'_, AppState>, path: String, content: String) -> Result<(), String> {
    let p = PathBuf::from(&path);
    if !state.is_approved(&p) {
        return Err("保存先が許可されていません（保存ダイアログから選び直してください）".into());
    }
    doc::write_file(&p, &content).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn save_settings(state: State<'_, AppState>, settings: Settings) -> Result<Bootstrap, String> {
    let s = settings.validate();
    settings::save(&s).map_err(|e| e.to_string())?;
    *state.settings.lock().unwrap() = s;
    Ok(bootstrap(state))
}

#[tauri::command]
pub fn copy_text(text: String) -> Result<(), String> {
    let mut cb = arboard::Clipboard::new().map_err(|e| e.to_string())?;
    cb.set_text(text).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn open_external(url: String) -> Result<(), String> {
    let lower = url.to_ascii_lowercase();
    if !(lower.starts_with("http://") || lower.starts_with("https://") || lower.starts_with("mailto:")) {
        return Err("許可されていないURLスキームです".into());
    }
    open::that(url).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn reveal_path(state: State<'_, AppState>, path: String) -> Result<(), String> {
    let p = PathBuf::from(&path);
    if path.starts_with('-') || !p.exists() || !state.is_approved(&p) {
        return Err("表示できないパスです".into());
    }
    #[cfg(target_os = "macos")]
    {
        let status = std::process::Command::new("open")
            .args(["-R", &path])
            .status()
            .map_err(|e| e.to_string())?;
        if !status.success() {
            return Err("Finder で表示できませんでした".into());
        }
        Ok(())
    }
    #[cfg(not(target_os = "macos"))]
    {
        open::that(path).map_err(|e| e.to_string())
    }
}

#[tauri::command]
pub fn clips_get(state: State<'_, AppState>) -> Vec<String> {
    state.clips.lock().unwrap().clone()
}

#[tauri::command]
pub fn clip_add(state: State<'_, AppState>, text: String) -> Vec<String> {
    let normalized: String = text.chars().take(MAX_CLIP_LEN).collect();
    let trimmed = normalized.trim();
    if trimmed.is_empty() {
        return state.clips.lock().unwrap().clone();
    }
    let mut clips = state.clips.lock().unwrap();
    clips.retain(|c| c != trimmed);
    clips.insert(0, trimmed.to_string());
    clips.truncate(MAX_CLIPS);
    let _ = state::save_clips(&clips);
    clips.clone()
}

#[tauri::command]
pub fn clip_remove(state: State<'_, AppState>, index: usize) -> Vec<String> {
    let mut clips = state.clips.lock().unwrap();
    if index < clips.len() {
        clips.remove(index);
        let _ = state::save_clips(&clips);
    }
    clips.clone()
}

#[tauri::command]
pub fn fonts_list(state: State<'_, AppState>) -> Vec<String> {
    state.fonts.lock().unwrap().clone()
}

#[tauri::command]
pub fn font_add(state: State<'_, AppState>) -> Result<Vec<String>, String> {
    let Some(path) = rfd::FileDialog::new()
        .add_filter("Fonts", &["ttf", "otf", "ttc"])
        .pick_file()
    else {
        return Ok(state.fonts.lock().unwrap().clone());
    };
    std::fs::create_dir_all(state::fonts_dir()).map_err(|e| e.to_string())?;
    let name = path.file_name().ok_or("不正なファイル名")?.to_string_lossy().to_string();
    let dest = state::fonts_dir().join(&name);
    std::fs::copy(&path, &dest).map_err(|e| e.to_string())?;
    let mut fonts = state::load_fonts();
    fonts.push(
        Path::new(&name)
            .file_stem()
            .map(|s| s.to_string_lossy().replace('_', " "))
            .unwrap_or(name),
    );
    fonts.sort();
    fonts.dedup();
    *state.fonts.lock().unwrap() = fonts.clone();
    Ok(fonts)
}

#[tauri::command]
pub fn font_remove(state: State<'_, AppState>, family: String) -> Result<Vec<String>, String> {
    if let Ok(entries) = std::fs::read_dir(state::fonts_dir()) {
        for entry in entries.flatten() {
            let p = entry.path();
            let stem = p
                .file_stem()
                .map(|s| s.to_string_lossy().replace('_', " "))
                .unwrap_or_default();
            if stem == family {
                let _ = std::fs::remove_file(&p);
            }
        }
    }
    let fonts = state::load_fonts();
    *state.fonts.lock().unwrap() = fonts.clone();
    Ok(fonts)
}

fn read_themes() -> Vec<ThemeInfo> {
    let mut out = Vec::new();
    let Ok(entries) = std::fs::read_dir(state::themes_dir()) else {
        return out;
    };
    for entry in entries.flatten() {
        let p = entry.path();
        if p.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        let Ok(text) = std::fs::read_to_string(&p) else { continue };
        let Ok(v) = serde_json::from_str::<serde_json::Value>(&text) else { continue };
        let name = v
            .get("name")
            .and_then(|n| n.as_str())
            .map(|s| s.to_string())
            .or_else(|| p.file_stem().map(|s| s.to_string_lossy().to_string()))
            .unwrap_or_default();
        let accent = v
            .get("accent")
            .and_then(|a| a.as_str())
            .map(theme::normalize_accent)
            .unwrap_or_default();
        let dark = v.get("dark").and_then(|d| d.as_bool()).unwrap_or(true);
        out.push(ThemeInfo { name, accent, dark });
    }
    out.sort_by(|a, b| a.name.cmp(&b.name));
    out
}

#[tauri::command]
pub fn themes_list() -> Vec<ThemeInfo> {
    read_themes()
}

#[tauri::command]
pub fn open_themes_dir() -> Result<(), String> {
    let dir = state::themes_dir();
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    open::that(dir).map_err(|e| e.to_string())
}

fn merge_pdfs(parts: Vec<Vec<u8>>) -> Result<Vec<u8>, String> {
    let mut out = lopdf::Document::with_version("1.5");
    let mut page_ids: Vec<lopdf::ObjectId> = Vec::new();
    let mut next: u32 = 1;
    for bytes in parts {
        let mut d = lopdf::Document::load_mem(&bytes).map_err(|e| e.to_string())?;
        d.renumber_objects_with(next);
        next = d.max_id + 1;
        for (_, pid) in d.get_pages() {
            page_ids.push(pid);
        }
        for (id, obj) in d.objects {
            out.objects.insert(id, obj);
        }
    }
    let pages_id = (next, 0u16);
    let kids: Vec<lopdf::Object> = page_ids
        .iter()
        .map(|id| lopdf::Object::Reference(*id))
        .collect();
    let mut pages = lopdf::Dictionary::new();
    pages.set("Type", lopdf::Object::Name(b"Pages".to_vec()));
    pages.set("Kids", lopdf::Object::Array(kids));
    pages.set("Count", page_ids.len() as i64);
    out.objects.insert(pages_id, lopdf::Object::Dictionary(pages));
    for pid in &page_ids {
        if let Ok(dict) = out.get_dictionary_mut(*pid) {
            dict.set("Parent", lopdf::Object::Reference(pages_id));
        }
    }
    let catalog_id = (next + 1, 0u16);
    let mut cat = lopdf::Dictionary::new();
    cat.set("Type", lopdf::Object::Name(b"Catalog".to_vec()));
    cat.set("Pages", lopdf::Object::Reference(pages_id));
    out.objects.insert(catalog_id, lopdf::Object::Dictionary(cat));
    out.trailer.set("Root", lopdf::Object::Reference(catalog_id));
    out.max_id = next + 1;
    let mut buf = Vec::new();
    out.save_to(&mut buf).map_err(|e| e.to_string())?;
    Ok(buf)
}

/// 表示中のページを A4 相当の矩形で分割キャプチャし、1 つの PDF に結合する。
#[tauri::command]
pub async fn export_pdf(
    state: State<'_, AppState>,
    window: WebviewWindow,
    path: String,
    page_w: f64,
    page_h: f64,
    pages: u32,
) -> Result<u64, String> {
    let target = PathBuf::from(&path);
    let selftest = std::env::args().any(|a| a == "--selftest" || a == "--export-pdf");
    if !selftest && !state.is_approved(&target) {
        return Err("保存先が許可されていません".into());
    }
    if pages == 0 || pages > 2000 {
        return Err("ページ数が不正です".into());
    }

    #[cfg(target_os = "macos")]
    {
        use block2::RcBlock;
        use objc2_foundation::{NSData, NSError};
        use objc2_web_kit::{WKPDFConfiguration, WKWebView};

        let mut parts: Vec<Vec<u8>> = Vec::new();
        for i in 0..pages {
            let (tx, rx) = std::sync::mpsc::channel::<Result<Vec<u8>, String>>();
            let y = page_h * i as f64;
            window
                .with_webview(move |wv| {
                    let wk = wv.inner() as *mut WKWebView;
                    if wk.is_null() {
                        let _ = tx.send(Err("no webview".into()));
                        return;
                    }
                    unsafe {
                        let cfg = WKPDFConfiguration::new(objc2::MainThreadMarker::new_unchecked());
                        cfg.setRect(objc2_foundation::NSRect {
                            origin: objc2_foundation::NSPoint { x: 0.0, y },
                            size: objc2_foundation::NSSize { width: page_w, height: page_h },
                        });
                        let tx2 = tx.clone();
                        let handler = RcBlock::new(move |data: *mut NSData, _err: *mut NSError| {
                            let bytes = if data.is_null() { None } else { Some((*data).to_vec()) };
                            let _ = tx2.send(bytes.ok_or_else(|| "empty page".to_string()));
                        });
                        (*wk).createPDFWithConfiguration_completionHandler(Some(&cfg), &handler);
                    }
                })
                .map_err(|e| e.to_string())?;
            let bytes = rx
                .recv_timeout(std::time::Duration::from_secs(30))
                .map_err(|_| format!("ページ {} の生成がタイムアウトしました", i + 1))??;
            parts.push(bytes);
        }
        let merged = merge_pdfs(parts)?;
        std::fs::write(&target, &merged).map_err(|e| e.to_string())?;
        return Ok(merged.len() as u64);
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = (&state, &window, page_w, page_h);
        Err("このプラットフォームでは未対応です".into())
    }
}

#[tauri::command]
pub fn print_page(window: WebviewWindow) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        window.print().map_err(|e| e.to_string())
    }
    #[cfg(not(target_os = "macos"))]
    {
        window.eval("window.print()").map_err(|e| e.to_string())
    }
}

#[derive(Serialize)]
pub struct PaletteReply {
    pub palette: Palette,
    pub accent: String,
    pub heading: String,
    pub dark: bool,
}

/// 設定を保存せずにテーマ配色だけを返す（スクリーンショット検証用）。
#[tauri::command]
pub fn palette_for_theme(theme: String, accent: String) -> PaletteReply {
    let s = Settings { theme, accent_color: accent, ..Default::default() };
    let (palette, accent, heading, dark) = build_palette(&s);
    PaletteReply { palette, accent, heading, dark }
}

/// 実 WKWebView をオフスクリーンで描画し PNG に保存する（UI 検証用）。
#[tauri::command]
pub fn take_screenshot(app: AppHandle, output: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        use block2::RcBlock;
        use objc2_app_kit::{NSBitmapImageFileType, NSBitmapImageRep, NSImage};
        use objc2_foundation::{NSDictionary, NSError};
        use objc2_web_kit::{WKSnapshotConfiguration, WKWebView};

        let Some(window) = app.get_webview_window("main") else {
            return Err("window not found".into());
        };
        let (tx, rx) = std::sync::mpsc::channel::<Result<Vec<u8>, String>>();
        let out2 = output.clone();
        window
            .with_webview(move |wv| {
                let wk = wv.inner() as *mut WKWebView;
                if wk.is_null() {
                    let _ = tx.send(Err("no webview".into()));
                    return;
                }
                unsafe {
                    let cfg = WKSnapshotConfiguration::new(objc2::MainThreadMarker::new_unchecked());
                    let tx2 = tx.clone();
                    let handler = RcBlock::new(move |image: *mut NSImage, _err: *mut NSError| {
                        if image.is_null() {
                            let _ = tx2.send(Err("snapshot returned nil".into()));
                            return;
                        }
                        let bytes = (|| -> Option<Vec<u8>> {
                            let tiff = (*image).TIFFRepresentation()?;
                            let rep = NSBitmapImageRep::imageRepWithData(&tiff)?;
                            let props = NSDictionary::new();
                            let png = rep.representationUsingType_properties(
                                NSBitmapImageFileType::PNG,
                                &props,
                            )?;
                            Some(png.to_vec())
                        })();
                        let _ = tx2.send(bytes.ok_or_else(|| "png encode failed".to_string()));
                    });
                    (*wk).takeSnapshotWithConfiguration_completionHandler(Some(&cfg), &handler);
                }
                let _ = out2;
            })
            .map_err(|e| e.to_string())?;
        let bytes = rx
            .recv_timeout(std::time::Duration::from_secs(20))
            .map_err(|_| "snapshot timeout".to_string())??;
        std::fs::write(&output, bytes).map_err(|e| e.to_string())?;
        return Ok(());
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = (&app, &output);
        Err("unsupported platform".into())
    }
}

#[tauri::command]
pub fn system_theme_dark() -> bool {
    dark_now()
}

#[tauri::command]
pub fn app_paths() -> Paths {
    Paths {
        config: state::app_dir().to_string_lossy().to_string(),
        themes: state::themes_dir().to_string_lossy().to_string(),
        fonts: state::fonts_dir().to_string_lossy().to_string(),
        clips: state::clips_path().to_string_lossy().to_string(),
    }
}

static START: std::sync::OnceLock<std::time::Instant> = std::sync::OnceLock::new();

pub fn mark_start() {
    let _ = START.set(std::time::Instant::now());
}

#[tauri::command]
pub fn ui_ready() -> u128 {
    let ms = START.get().map(|t| t.elapsed().as_millis()).unwrap_or(0);
    let path = state::app_dir().join("startup.json");
    if let Some(dir) = path.parent() {
        let _ = std::fs::create_dir_all(dir);
    }
    let _ = std::fs::write(&path, format!("{{\"version\":\"{}\",\"ready_ms\":{}}}", env!("CARGO_PKG_VERSION"), ms));
    ms
}

#[tauri::command]
pub fn selftest_report(app: AppHandle, payload: serde_json::Value) -> Result<(), String> {
    let path = state::app_dir().join("selftest.json");
    if let Some(dir) = path.parent() {
        let _ = std::fs::create_dir_all(dir);
    }
    let text = serde_json::to_string_pretty(&payload).map_err(|e| e.to_string())?;
    std::fs::write(&path, text).map_err(|e| e.to_string())?;
    let handle = app.clone();
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_millis(300));
        handle.exit(0);
    });
    Ok(())
}

pub fn persist_window_state(app: &AppHandle) -> tauri::Result<()> {
    let Some(window) = app.get_webview_window("main") else {
        return Ok(());
    };
    let mut s = {
        let st = app.state::<AppState>();
        let guard = st.settings.lock().unwrap();
        guard.clone()
    };
    if let Ok(size) = window.inner_size() {
        s.window.width = size.width as f64;
        s.window.height = size.height as f64;
    }
    if let Ok(pos) = window.outer_position() {
        s.window.x = Some(pos.x as f64);
        s.window.y = Some(pos.y as f64);
    }
    s.window.maximized = window.is_maximized().unwrap_or(false);
    let _ = settings::save(&s);
    let st = app.state::<AppState>();
    *st.settings.lock().unwrap() = s;
    Ok(())
}
