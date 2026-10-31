//! 設定の永続化。
//!
//! - 旧アプリ `~/.mdviewer/settings.json` のキーを読める（未知キーは無視）。
//! - 保存は同一ディレクトリの一時ファイル + rename（原子的）。
//! - 破損時は既定値で起動し、壊れたファイルは `.bak` として退避する。

use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

use crate::theme::{normalize_accent, ThemeMode};

pub const SETTINGS_VERSION: u32 = 2;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(default)]
pub struct WindowState {
    pub width: f64,
    pub height: f64,
    pub x: Option<f64>,
    pub y: Option<f64>,
    pub maximized: bool,
}

impl Default for WindowState {
    fn default() -> Self {
        WindowState { width: 1280.0, height: 900.0, x: None, y: None, maximized: false }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    pub version: u32,
    pub lang: String,
    pub theme: ThemeMode,
    pub accent_color: String,
    pub font_family: String,
    pub font_size: u32,
    pub scale_idx: usize,
    pub page_mode: String,
    pub margins: [u32; 4],
    pub hard_breaks: bool,
    pub show_toc: bool,
    pub show_clip: bool,
    pub bold_mode: bool,
    pub recent: Vec<String>,
    pub last_dir: String,
    pub last_pdf_dir: String,
    pub pdf_embed_images: bool,
    pub window: WindowState,
    /// 旧アプリの `window_geometry`（"wxh+x+y"）を保持しておく（移行用）。
    pub window_geometry: String,
}

impl Default for Settings {
    fn default() -> Self {
        Settings {
            version: SETTINGS_VERSION,
            lang: "ja".into(),
            theme: ThemeMode::Dark,
            accent_color: String::new(),
            font_family: "Helvetica Neue".into(),
            font_size: 16,
            scale_idx: 2,
            page_mode: "free".into(),
            margins: [20, 20, 20, 20],
            hard_breaks: true,
            show_toc: true,
            show_clip: false,
            bold_mode: false,
            recent: Vec::new(),
            last_dir: String::new(),
            last_pdf_dir: String::new(),
            pdf_embed_images: true,
            window: WindowState::default(),
            window_geometry: String::new(),
        }
    }
}

impl Settings {
    pub fn validate(mut self) -> Self {
        if !matches!(self.lang.as_str(), "ja" | "en" | "de" | "fr" | "zh") {
            self.lang = "ja".into();
        }
        if self.scale_idx > 4 {
            self.scale_idx = 2;
        }
        if !matches!(self.page_mode.as_str(), "free" | "a4") {
            self.page_mode = "free".into();
        }
        self.accent_color = normalize_accent(&self.accent_color);
        self.font_size = self.font_size.clamp(10, 40);
        for m in &mut self.margins {
            *m = (*m).min(80);
        }
        if self.recent.len() > 12 {
            self.recent.truncate(12);
        }
        self.version = SETTINGS_VERSION;
        self
    }

    pub fn scale(&self) -> f64 {
        const STEPS: [f64; 5] = [0.5, 0.75, 1.0, 1.25, 1.5];
        STEPS[self.scale_idx.min(4)]
    }
}

/// 設定ディレクトリ。旧アプリと同じ `~/.mdviewer` を使う（移行のため）。
pub fn settings_dir() -> PathBuf {
    dirs::home_dir().unwrap_or_else(|| PathBuf::from(".")).join(".mdviewer")
}

pub fn settings_path() -> PathBuf {
    settings_dir().join("settings.json")
}

/// 読み込み。壊れていれば既定値 + 退避。
pub fn load_from(path: &Path) -> Settings {
    match fs::read_to_string(path) {
        Ok(text) => match serde_json::from_str::<Settings>(&text) {
            Ok(s) => s.validate(),
            Err(_) => {
                let _ = fs::rename(path, path.with_extension("json.bak"));
                Settings::default()
            }
        },
        Err(_) => Settings::default(),
    }
}

pub fn load() -> Settings {
    load_from(&settings_path())
}

/// 原子的保存（tmp → fsync → rename）。
pub fn save_to(path: &Path, s: &Settings) -> std::io::Result<()> {
    if let Some(dir) = path.parent() {
        fs::create_dir_all(dir)?;
    }
    let tmp = path.with_extension("json.tmp");
    let json = serde_json::to_string_pretty(s)?;
    {
        let mut f = fs::File::create(&tmp)?;
        f.write_all(json.as_bytes())?;
        f.sync_all()?;
    }
    fs::rename(&tmp, path)?;
    Ok(())
}

pub fn save(s: &Settings) -> std::io::Result<()> {
    save_to(&settings_path(), s)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Read;

    #[test]
    fn defaults_validate() {
        let s = Settings::default().validate();
        assert_eq!(s.lang, "ja");
        assert_eq!(s.scale(), 1.0);
        assert!(s.hard_breaks);
    }

    #[test]
    fn invalid_values_are_repaired() {
        let s = Settings { lang: "xx".into(), page_mode: "letter".into(), scale_idx: 9, ..Default::default() }
            .validate();
        assert_eq!(s.lang, "ja");
        assert_eq!(s.page_mode, "free");
        assert_eq!(s.scale_idx, 2);
    }

    #[test]
    fn legacy_json_is_accepted_and_unknown_keys_ignored() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path().join("settings.json");
        fs::write(
            &p,
            r##"{"lang":"en","theme":"light","font_family":"Hiragino Sans","accent_color":"#AABBCC",
                "show_toc":false,"hard_breaks":false,"window_geometry":"1280x900+10+20","unknown_key":1}"##,
        )
        .unwrap();
        let s = load_from(&p);
        assert_eq!(s.lang, "en");
        assert_eq!(s.theme, ThemeMode::Light);
        assert_eq!(s.accent_color, "#aabbcc");
        assert!(!s.show_toc);
        assert_eq!(s.window_geometry, "1280x900+10+20");
    }

    #[test]
    fn corrupted_file_falls_back_and_is_backed_up() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path().join("settings.json");
        fs::write(&p, "{not json").unwrap();
        let s = load_from(&p);
        assert_eq!(s.lang, "ja");
        assert!(p.with_extension("json.bak").exists());
    }

    #[test]
    fn atomic_save_roundtrip() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path().join("settings.json");
        let mut s = Settings::default();
        s.lang = "fr".into();
        s.recent = vec!["/a.md".into()];
        save_to(&p, &s).unwrap();
        let mut got = String::new();
        fs::File::open(&p).unwrap().read_to_string(&mut got).unwrap();
        let back: Settings = serde_json::from_str(&got).unwrap();
        assert_eq!(back.lang, "fr");
        assert_eq!(back.recent, vec!["/a.md".to_string()]);
        assert!(!p.with_extension("json.tmp").exists());
    }
}
