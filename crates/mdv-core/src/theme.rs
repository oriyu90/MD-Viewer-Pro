//! テーマ（配色）とアクセント色の導出。
//!
//! 旧アプリ（main.py の DARK_PALETTE / LIGHT_PALETTE）と同じ値を持ち、
//! アクセント色から見出し色・ホバー色を導出する。GUI 非依存。

use serde::{Deserialize, Serialize};

/// 画面テーマ。
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum ThemeMode {
    #[default]
    Dark,
    Light,
    System,
}

/// 1 テーマ分の配色。CSS 変数へそのまま流し込む。
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Palette {
    pub bg: String,
    pub bg2: String,
    pub bg3: String,
    pub border: String,
    pub text: String,
    pub text_dim: String,
    pub accent: String,
    pub heading: String,
    pub toolbar: String,
    pub btn: String,
    pub btn_hover: String,
    pub btn_active_bg: String,
    pub btn_active_fg: String,
    pub select: String,
    pub code_fg: String,
    pub row_even: String,
    pub sep: String,
    pub copy_btn_bg: String,
    pub copy_btn_fg: String,
}

fn owned(v: [&str; 19]) -> Palette {
    Palette {
        bg: v[0].into(),
        bg2: v[1].into(),
        bg3: v[2].into(),
        border: v[3].into(),
        text: v[4].into(),
        text_dim: v[5].into(),
        accent: v[6].into(),
        heading: v[7].into(),
        toolbar: v[8].into(),
        btn: v[9].into(),
        btn_hover: v[10].into(),
        btn_active_bg: v[11].into(),
        btn_active_fg: v[12].into(),
        select: v[13].into(),
        code_fg: v[14].into(),
        row_even: v[15].into(),
        sep: v[16].into(),
        copy_btn_bg: v[17].into(),
        copy_btn_fg: v[18].into(),
    }
}

/// 旧アプリ v1.5.3 のダークパレット。
pub fn dark_palette() -> Palette {
    owned([
        "#000000", "#111111", "#1c1c1c", "#2a2a2a", "#c0c0c0", "#484848", "#4a9eff",
        "#7ab8f5", "#0c0c0c", "#1c1c1c", "#2e2e2e", "#4a4a4a", "#ffffff", "#1a3a5c",
        "#e06c75", "#0d0d0d", "#2a2a2a", "rgba(50,50,50,0.85)", "#aaaaaa",
    ])
}

/// 旧アプリ v1.5.3 のライトパレット。
pub fn light_palette() -> Palette {
    owned([
        "#f0f0f0", "#ffffff", "#e6e6e6", "#c4c4c4", "#000000", "#909090", "#1a6abf",
        "#1a5fa0", "#dcdcdc", "#cccccc", "#bababa", "#888888", "#ffffff", "#c0d8ff",
        "#c0392b", "#f4f4f4", "#b0b0b0", "rgba(180,180,180,0.85)", "#444444",
    ])
}

pub fn palette_for(mode: ThemeMode, system_dark: bool) -> Palette {
    match mode {
        ThemeMode::Dark => dark_palette(),
        ThemeMode::Light => light_palette(),
        ThemeMode::System => {
            if system_dark {
                dark_palette()
            } else {
                light_palette()
            }
        }
    }
}

fn parse_hex(c: &str) -> Option<(u8, u8, u8)> {
    let s = c.strip_prefix('#')?;
    if s.len() != 6 || !s.chars().all(|ch| ch.is_ascii_hexdigit()) {
        return None;
    }
    let r = u8::from_str_radix(&s[0..2], 16).ok()?;
    let g = u8::from_str_radix(&s[2..4], 16).ok()?;
    let b = u8::from_str_radix(&s[4..6], 16).ok()?;
    Some((r, g, b))
}

/// 2 色を線形に混ぜる（旧 _mix_hex と同じ）。
pub fn mix_hex(c1: &str, c2: &str, t: f64) -> String {
    let (Some(a), Some(b)) = (parse_hex(c1), parse_hex(c2)) else {
        return c1.to_string();
    };
    let t = t.clamp(0.0, 1.0);
    let mix = |x: u8, y: u8| -> u8 { (x as f64 + (y as f64 - x as f64) * t).round() as u8 };
    format!("#{:02x}{:02x}{:02x}", mix(a.0, b.0), mix(a.1, b.1), mix(a.2, b.2))
}

fn luminance(c: &str) -> f64 {
    let Some((r, g, b)) = parse_hex(c) else { return 0.0 };
    (0.2126 * r as f64 + 0.7152 * g as f64 + 0.0722 * b as f64) / 255.0
}

/// 背景が暗いか。
pub fn is_dark(hex_color: &str) -> bool {
    luminance(hex_color) < 0.5
}

/// アクセント色を背景に合わせて調整する（旧 _effective_accent）。
pub fn effective_accent(base_hex: &str, dark_bg: bool) -> String {
    if base_hex.is_empty() {
        return if dark_bg { "#4a9eff".into() } else { "#1a6abf".into() };
    }
    if parse_hex(base_hex).is_none() {
        return if dark_bg { "#4a9eff".into() } else { "#1a6abf".into() };
    }
    if dark_bg {
        base_hex.to_string()
    } else {
        // ライト背景では黒方向へ寄せてコントラストを確保する。
        mix_hex(base_hex, "#000000", 0.25)
    }
}

/// 見出し色（アクセントから導出。旧 _effective_heading）。
pub fn effective_heading(accent: &str, dark_bg: bool, text: &str) -> String {
    if dark_bg {
        mix_hex(accent, "#ffffff", 0.35)
    } else {
        mix_hex(accent, text, 0.25)
    }
}

/// 設定値（"#rrggbb" か空）を検証して正規化する。
pub fn normalize_accent(s: &str) -> String {
    let s = s.trim();
    if s.is_empty() {
        return String::new();
    }
    match parse_hex(s) {
        Some((r, g, b)) => format!("#{r:02x}{g:02x}{b:02x}"),
        None => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn palettes_match_legacy_values() {
        assert_eq!(dark_palette().bg, "#000000");
        assert_eq!(light_palette().accent, "#1a6abf");
        assert_eq!(dark_palette().code_fg, "#e06c75");
    }

    #[test]
    fn mix_is_linear() {
        assert_eq!(mix_hex("#000000", "#ffffff", 0.5), "#808080");
        assert_eq!(mix_hex("#000000", "#ffffff", 0.0), "#000000");
    }

    #[test]
    fn accent_normalization() {
        assert_eq!(normalize_accent("#AABBCC"), "#aabbcc");
        assert_eq!(normalize_accent("javascript:alert(1)"), "");
        assert_eq!(normalize_accent(""), "");
    }

    #[test]
    fn light_background_darkens_accent() {
        let a = effective_accent("#4a9eff", false);
        assert_ne!(a, "#4a9eff");
        assert_eq!(effective_accent("", false), "#1a6abf");
        assert_eq!(effective_accent("", true), "#4a9eff");
    }
}
