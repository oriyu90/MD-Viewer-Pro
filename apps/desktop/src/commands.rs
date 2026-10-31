//! Tauri コマンド層。UI から呼べる操作はここに集約し、権限は capability で絞る。

use std::path::{Path, PathBuf};

use mdv_core::doc::{self, Document};
use mdv_core::render::{render_markdown, RenderOptions, Rendered};
use mdv_core::settings::{self, Settings};
use mdv_core::theme::{self, effective_accent, effective_heading, palette_for, Palette, ThemeMode};
use serde::Serialize;
use tauri::{AppHandle, Manager, State, WebviewWindow};

use crate::state::{self, AppState, OpenDocument, MAX_CLIPS, MAX_CLIP_LEN};

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

fn build_palette(s: &Settings) -> (Palette, String, String, bool) {
    let dark = match s.theme {
        ThemeMode::Dark => true,
        ThemeMode::Light => false,
        ThemeMode::System => dark_now(),
    };
    let accent = effective_accent(&s.accent_color, dark);
    let heading = effective_heading(&accent, dark, if dark { "#c0c0c0" } else { "#000000" });
    let mut p = palette_for(s.theme, dark);
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

fn selftest_fixture() -> Option<String> {
    if !std::env::args().any(|a| a == "--selftest") {
        return None;
    }
    let path = std::env::temp_dir().join("mdvp-selftest.md");
    let body = "# 自動作成ドキュメント\n\nこれはセルフテスト用の本文です。\n\n## 節\n\n- 箇条書き\n- 二つ目\n\n| 列A | 列B |\n|---|---|\n| 1 | 2 |\n";
    std::fs::write(&path, body).ok()?;
    Some(path.to_string_lossy().to_string())
}

fn open_document(state: &AppState, path: &Path) -> Result<OpenedDoc, String> {
    let (mut d, warning) = Document::from_path(path).map_err(|e| e.to_string())?;
    d.bump();
    let s = state.settings.lock().unwrap().clone();
    let rendered = render_markdown(&d.source, RenderOptions {
        hard_breaks: s.hard_breaks,
        allow_raw_html: true,
    });
    let out = OpenedDoc {
        path: Some(path.to_string_lossy().to_string()),
        source: d.source.clone(),
        kind: if d.kind.is_yaml() { "yaml".into() } else { "md".into() },
        readonly: d.readonly,
        warning,
        rendered,
    };
    *state.doc.lock().unwrap() = Some(OpenDocument {
        path: Some(path.to_path_buf()),
        source: d.source.clone(),
        dirty: false,
    });
    Ok(out)
}

#[tauri::command]
pub fn open_path(state: State<'_, AppState>, path: String) -> Result<OpenedDoc, String> {
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
    open_document(&state, &p)
}

#[tauri::command]
pub fn pick_file() -> Option<String> {
    rfd::FileDialog::new()
        .add_filter("Markdown / Text / YAML", &["md", "markdown", "txt", "yml", "yaml"])
        .add_filter("All Files", &["*"])
        .pick_file()
        .map(|p| p.to_string_lossy().to_string())
}

#[tauri::command]
pub fn pick_save(suggested: String) -> Option<String> {
    rfd::FileDialog::new()
        .set_file_name(&suggested)
        .add_filter("Markdown", &["md"])
        .add_filter("Text", &["txt"])
        .add_filter("HTML", &["html"])
        .save_file()
        .map(|p| p.to_string_lossy().to_string())
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
    path: Option<String>,
    source: String,
) -> Result<String, String> {
    let target = match path {
        Some(p) if !p.is_empty() => PathBuf::from(p),
        _ => return Err("保存先が指定されていません".into()),
    };
    doc::write_file(&target, &source).map_err(|e| e.to_string())?;
    {
        let mut d = state.doc.lock().unwrap();
        if let Some(doc) = d.as_mut() {
            doc.source = source.clone();
            doc.path = Some(target.clone());
            doc.dirty = false;
        }
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
pub fn save_text(path: String, content: String) -> Result<(), String> {
    doc::write_file(Path::new(&path), &content).map_err(|e| e.to_string())
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
pub fn reveal_path(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .args(["-R", &path])
            .status()
            .map_err(|e| e.to_string())?;
        return Ok(());
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

#[tauri::command]
pub fn print_page(window: WebviewWindow) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        return window.print().map_err(|e| e.to_string());
    }
    #[cfg(not(target_os = "macos"))]
    {
        window.eval("window.print()").map_err(|e| e.to_string())
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
