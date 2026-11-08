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
    pub doc: Mutex<std::collections::HashMap<String, OpenDocument>>,
    pub clips: Mutex<Vec<String>>,
    pub fonts: Mutex<Vec<String>>,
    /// フロントエンドが `open-path` を購読する前に届いたパスを保持する。
    /// macOS の `application:openURLs:` は起動直後（WebView の準備前）に来るため、
    /// そのまま emit すると取りこぼす。UI 準備完了時にここから流す。
    pub pending_paths: Mutex<Vec<String>>,
    /// フロントエンドが購読済みか（`ui_ready` で true）。
    pub ui_ready: std::sync::atomic::AtomicBool,
}

/// 起動直後に届いたパスを覚えておく上限（暴走した引数でもメモリを食い尽くさない）。
pub const MAX_PENDING_PATHS: usize = 64;

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
            doc: Mutex::new(std::collections::HashMap::new()),
            clips: Mutex::new(clips),
            fonts: Mutex::new(fonts),
            pending_paths: Mutex::new(Vec::new()),
            ui_ready: std::sync::atomic::AtomicBool::new(false),
        }
    }

    /// フロントエンドが未購読なら溜めておき、購読済みならそのまま返す。
    /// 戻り値が `true` なら呼び出し側が `open-path` を emit する。
    pub fn offer_path(&self, path: String) -> bool {
        use std::sync::atomic::Ordering;
        if self.ui_ready.load(Ordering::SeqCst) {
            return true;
        }
        let mut q = self.pending_paths.lock().unwrap_or_else(|e| e.into_inner());
        if q.len() < MAX_PENDING_PATHS && !q.contains(&path) {
            q.push(path);
        }
        false
    }

    /// `ui_ready` 後に溜まっていたパスを取り出す（取り出したら空になる）。
    pub fn take_pending_paths(&self) -> Vec<String> {
        let mut q = self.pending_paths.lock().unwrap_or_else(|e| e.into_inner());
        std::mem::take(&mut *q)
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

/// 転送メッセージの上限。壊れたクライアントで無制限にメモリを確保しない。
const MAX_MSG_BYTES: u64 = 64 * 1024;

#[cfg(target_os = "macos")]
fn sock_path() -> PathBuf {
    app_dir().join("instance.sock")
}

/// 既存インスタンスへ送る内容。`path` が無ければ「起動要求（前面化）」。
#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, PartialEq)]
struct InstanceMessage {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    path: Option<String>,
}

/// 受信テキストを解釈する。
///
/// 新形式は JSON（`{"path": "..."}` / `{}`）。旧形式（生のパス文字列）も
/// そのまま受け付ける（β3.0 以前のプロセスと混在しても壊れない）。
fn parse_instance_message(text: &str) -> InstanceMessage {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return InstanceMessage { path: None };
    }
    if trimmed.starts_with('{') {
        if let Ok(m) = serde_json::from_str::<InstanceMessage>(trimmed) {
            return m;
        }
    }
    InstanceMessage { path: Some(trimmed.to_string()) }
}

/// 既存インスタンスへパスを送る。成功したら true（呼び出し側は終了）。
#[cfg(target_os = "macos")]
pub fn forward_to_running_instance(path: &Option<PathBuf>) -> bool {
    use std::os::unix::net::UnixStream;
    let sock = sock_path();
    let Ok(mut stream) = UnixStream::connect(&sock) else {
        return false;
    };
    let msg = InstanceMessage {
        path: path.as_ref().map(|p| p.to_string_lossy().to_string()),
    };
    let Ok(json) = serde_json::to_vec(&msg) else {
        return false;
    };
    if stream.write_all(&json).is_err() {
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
    // 既存のソケットに接続できなかった場合だけ、古い残骸を消して作り直す。
    let _ = std::fs::remove_file(&sock);
    let Ok(listener) = UnixListener::bind(&sock) else {
        return;
    };
    std::thread::spawn(move || {
        use tauri::{Emitter, Manager};
        for stream in listener.incoming().flatten() {
            // 上限付きで読む（`read_to_string` は無制限）。
            let mut buf = Vec::new();
            let _ = stream.take(MAX_MSG_BYTES).read_to_end(&mut buf);
            let text = String::from_utf8_lossy(&buf);
            let msg = parse_instance_message(&text);
            if let Some(p) = msg.path.filter(|p| !p.is_empty()) {
                // 起動直後（UI 未購読）の転送も取りこぼさない。
                let st = app.state::<AppState>();
                if st.offer_path(p.clone()) {
                    let _ = app.emit("open-path", p);
                }
            }
            // ファイル指定の有無にかかわらず、既存ウィンドウを前面へ出す。
            activate_main_window(&app);
        }
    });
}

/// メインウィンドウを表示・前面化する（Dock 再オープンと転送の共通経路）。
pub fn activate_main_window(app: &tauri::AppHandle) {
    use tauri::Manager;
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.unminimize();
        let _ = w.set_focus();
    }
    focus_app();
}

/// アプリ自体を前面へ。macOS 14+ は `activate`、それ以前は
/// `activateIgnoringOtherApps(true)`。メインスレッド以外では何もしない。
#[cfg(target_os = "macos")]
pub fn focus_app() {
    use objc2_app_kit::NSApplication;
    use objc2_foundation::MainThreadMarker;
    let Some(mtm) = MainThreadMarker::new() else {
        // メインスレッドでなければ Tauri のイベントループへ委譲する。
        return;
    };
    let ns_app = NSApplication::sharedApplication(mtm);
    #[allow(deprecated)]
    ns_app.activateIgnoringOtherApps(true);
}

#[cfg(not(target_os = "macos"))]
pub fn focus_app() {}

#[cfg(not(target_os = "macos"))]
pub fn forward_to_running_instance(_path: &Option<PathBuf>) -> bool {
    false
}

#[cfg(not(target_os = "macos"))]
pub fn start_instance_listener(_app: tauri::AppHandle) {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn instance_message_roundtrip_with_path() {
        let text = r#"{"path":"/tmp/a.md"}"#;
        assert_eq!(
            parse_instance_message(text),
            InstanceMessage { path: Some("/tmp/a.md".into()) }
        );
    }

    #[test]
    fn instance_message_activate_only() {
        assert_eq!(parse_instance_message("{}"), InstanceMessage { path: None });
        assert_eq!(parse_instance_message("   "), InstanceMessage { path: None });
        assert_eq!(parse_instance_message(""), InstanceMessage { path: None });
    }

    #[test]
    fn legacy_raw_path_is_accepted() {
        assert_eq!(
            parse_instance_message("/tmp/legacy.txt\n"),
            InstanceMessage { path: Some("/tmp/legacy.txt".into()) }
        );
    }

    #[test]
    fn broken_json_does_not_panic() {
        // 壊れた JSON は旧形式（生パス）として解釈され、パニックしない。
        let m = parse_instance_message("{not json");
        assert!(m.path.is_some());
    }
}
