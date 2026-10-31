//! アプリ状態・設定・クリップボード・単一インスタンス。

use std::io::{Read, Write};
use std::path::PathBuf;
use std::sync::Mutex;

use mdv_core::settings::{self, Settings};

pub const MAX_CLIPS: usize = 200;
pub const MAX_CLIP_LEN: usize = 5000;

pub struct OpenDocument {
    pub path: Option<PathBuf>,
    pub source: String,
    pub dirty: bool,
}

pub struct AppState {
    pub approved: Mutex<std::collections::HashSet<PathBuf>>,
    pub settings: Mutex<Settings>,
    pub doc: Mutex<Option<OpenDocument>>,
    pub clips: Mutex<Vec<String>>,
    pub fonts: Mutex<Vec<String>>,
}

pub fn app_dir() -> PathBuf {
    settings::settings_dir()
}

pub fn clips_path() -> PathBuf {
    app_dir().join("clipboard.json")
}

pub fn fonts_dir() -> PathBuf {
    app_dir().join("fonts")
}

pub fn themes_dir() -> PathBuf {
    app_dir().join("themes")
}

impl AppState {
    /// ダイアログや起動引数でユーザーが明示的に選んだパスだけを許可する。
    pub fn approve(&self, path: &std::path::Path) {
        self.approved.lock().unwrap().insert(path.to_path_buf());
    }

    pub fn is_approved(&self, path: &std::path::Path) -> bool {
        self.approved.lock().unwrap().contains(path)
    }

    pub fn new() -> Self {
        let s = settings::load();
        let clips = load_clips();
        let fonts = load_fonts();
        AppState {
            approved: Mutex::new(std::collections::HashSet::new()),
            settings: Mutex::new(s),
            doc: Mutex::new(None),
            clips: Mutex::new(clips),
            fonts: Mutex::new(fonts),
        }
    }
}

pub fn load_clips() -> Vec<String> {
    let path = clips_path();
    let Ok(text) = std::fs::read_to_string(&path) else {
        return Vec::new();
    };
    if text.len() > 1024 * 1024 {
        return Vec::new();
    }
    let Ok(v) = serde_json::from_str::<Vec<String>>(&text) else {
        return Vec::new();
    };
    v.into_iter()
        .map(|s| s.chars().take(MAX_CLIP_LEN).collect())
        .filter(|s: &String| !s.trim().is_empty())
        .take(MAX_CLIPS)
        .collect()
}

pub fn save_clips(clips: &[String]) -> std::io::Result<()> {
    let path = clips_path();
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    let json = serde_json::to_string_pretty(clips)?;
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, json)?;
    std::fs::rename(tmp, path)?;
    Ok(())
}

pub fn load_fonts() -> Vec<String> {
    let mut out = Vec::new();
    let Ok(entries) = std::fs::read_dir(fonts_dir()) else {
        return out;
    };
    for entry in entries.flatten() {
        let p = entry.path();
        if let Some(stem) = p.file_stem().and_then(|s| s.to_str()) {
            out.push(stem.replace('_', " "));
        }
    }
    out.sort();
    out
}

// ── 単一インスタンス（macOS / Unix） ─────────────────────────────

#[cfg(target_os = "macos")]
fn sock_path() -> PathBuf {
    app_dir().join("instance.sock")
}

/// 既存インスタンスへパスを送る。成功したら true（呼び出し側は終了）。
#[cfg(target_os = "macos")]
pub fn forward_to_running_instance(path: &Option<PathBuf>) -> bool {
    use std::os::unix::net::UnixStream;
    let sock = sock_path();
    let Ok(mut stream) = UnixStream::connect(&sock) else {
        return false;
    };
    let msg = path
        .as_ref()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default();
    if stream.write_all(msg.as_bytes()).is_err() {
        return false;
    }
    let _ = stream.flush();
    true
}

/// 既存インスタンスからのファイルパスを受け取り、フロントへ転送する。
#[cfg(target_os = "macos")]
pub fn start_instance_listener(app: tauri::AppHandle) {
    use std::os::unix::net::UnixListener;
    let sock = sock_path();
    if let Some(dir) = sock.parent() {
        let _ = std::fs::create_dir_all(dir);
    }
    let _ = std::fs::remove_file(&sock);
    let Ok(listener) = UnixListener::bind(&sock) else {
        return;
    };
    std::thread::spawn(move || {
        use tauri::Emitter;
        for stream in listener.incoming().flatten() {
            let mut stream = stream;
            let mut buf = String::new();
            let _ = stream.read_to_string(&mut buf);
            let msg = buf.trim();
            if msg.is_empty() {
                let _ = app.emit("activate", ());
            } else {
                let _ = app.emit("open-path", msg.to_string());
            }
        }
    });
}

#[cfg(not(target_os = "macos"))]
pub fn forward_to_running_instance(_path: &Option<PathBuf>) -> bool {
    false
}

#[cfg(not(target_os = "macos"))]
pub fn start_instance_listener(_app: tauri::AppHandle) {}
