//! mdv-core — GUI 非依存の文書コア。
//!
//! 設計原則:
//! - 原文（Markdown ソース）が常に正本。HTML からの逆変換は行わない。
//! - ここには Tauri も WebView も登場しない（CLI / テストから同じ経路で使える）。
//! - サニタイズは Rust 側（ammonia）で行い、WebView には安全な HTML だけを渡す。

pub mod doc;
pub mod render;
pub mod settings;
pub mod theme;

pub use doc::Document;
pub use render::{render_markdown, Heading, RenderOptions, Rendered};
pub use settings::Settings;
pub use theme::{palette_for, Palette, ThemeMode};
