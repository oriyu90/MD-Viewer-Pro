//! 文書の読み書き。原文を正本として扱い、HTML からの逆変換はしない。

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

/// 1 文書の状態。`generation` は非同期処理の競合検出に使う。
#[derive(Debug, Clone, PartialEq)]
pub struct Document {
    pub path: Option<PathBuf>,
    pub source: String,
    pub generation: u64,
    pub kind: DocKind,
    pub readonly: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DocKind {
    Markdown,
    Text,
    Yaml,
}

impl DocKind {
    pub fn from_path(path: &Path) -> Self {
        match path
            .extension()
            .and_then(|e| e.to_str())
            .map(|e| e.to_ascii_lowercase())
            .as_deref()
        {
            Some("yml") | Some("yaml") => DocKind::Yaml,
            Some("md") | Some("markdown") | Some("mdown") | Some("mkd") => DocKind::Markdown,
            _ => DocKind::Text,
        }
    }

    /// UI へ渡す識別子（`"md"` / `"txt"` / `"yaml"`）。
    ///
    /// `.txt` を開いたときに UI が Markdown 文書として扱わないよう、
    /// 拡張子から確定した種別をそのまま返す。
    pub fn id(self) -> &'static str {
        match self {
            DocKind::Markdown => "md",
            DocKind::Text => "txt",
            DocKind::Yaml => "yaml",
        }
    }

    /// `.txt` など、書式ツールバーで Markdown 記法を入れたくない書類か。
    pub fn prefers_plain_text(self) -> bool {
        matches!(self, DocKind::Text)
    }

    pub fn is_yaml(self) -> bool {
        matches!(self, DocKind::Yaml)
    }
}

/// 保存先パスから書類種別を決める。拡張子が無ければ `fallback`。
pub fn kind_for_save(path: &Path, fallback: DocKind) -> DocKind {
    if path.extension().and_then(|e| e.to_str()).is_some() {
        DocKind::from_path(path)
    } else {
        fallback
    }
}

#[derive(Debug, thiserror::Error)]
pub enum DocError {
    #[error("ファイルが大きすぎます（{size} bytes > 上限 {limit} bytes）")]
    TooLarge { size: u64, limit: u64 },
    #[error("バイナリファイルの可能性があります: {0}")]
    Binary(String),
    #[error("読み込みに失敗しました: {0}")]
    Io(#[from] std::io::Error),
    #[error("保存先が指定されていません")]
    NoPath,
}

/// 既定の上限（32MiB）。UI を固まらせないための安全弁。
pub const MAX_FILE_BYTES: u64 = 32 * 1024 * 1024;

/// 先頭 8KiB に NUL があればバイナリとみなす。
fn looks_binary(bytes: &[u8]) -> bool {
    let head = &bytes[..bytes.len().min(8192)];
    head.contains(&0)
}

/// バイト列をテキストへ。BOM → UTF-8 → 文字コード推定 → 置換、の順。
pub fn decode_text(bytes: &[u8]) -> (String, Option<String>) {
    if let Some(rest) = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]) {
        return (String::from_utf8_lossy(rest).into_owned(), None);
    }
    if let Some(rest) = bytes.strip_prefix(&[0xFF, 0xFE]) {
        let (s, _, _) = encoding_rs::UTF_16LE.decode(rest);
        return (s.into_owned(), None);
    }
    if let Some(rest) = bytes.strip_prefix(&[0xFE, 0xFF]) {
        let (s, _, _) = encoding_rs::UTF_16BE.decode(rest);
        return (s.into_owned(), None);
    }
    match std::str::from_utf8(bytes) {
        Ok(s) => (s.to_string(), None),
        Err(_) => {
            let mut det = chardetng::EncodingDetector::new(chardetng::Iso2022JpDetection::Deny);
            det.feed(bytes, true);
            let enc = det.guess(None, chardetng::Utf8Detection::Allow);
            let (s, had_errors) = enc.decode_without_bom_handling(bytes);
            let warning = if had_errors {
                Some(format!("文字コード {} として読み込みました（一部置換）", enc.name()))
            } else {
                Some(format!("文字コード {} として読み込みました", enc.name()))
            };
            (s.into_owned(), warning)
        }
    }
}

/// ファイルを読む。改行はそのまま保持（表示側で吸収）。
pub fn read_file(path: &Path) -> Result<(String, Option<String>), DocError> {
    let meta = fs::metadata(path)?;
    if meta.len() > MAX_FILE_BYTES {
        return Err(DocError::TooLarge { size: meta.len(), limit: MAX_FILE_BYTES });
    }
    let bytes = fs::read(path)?;
    if looks_binary(&bytes) {
        return Err(DocError::Binary(path.display().to_string()));
    }
    Ok(decode_text(&bytes))
}

/// 原子的保存。改行は LF に統一（旧アプリと同じ）。
pub fn write_file(path: &Path, text: &str) -> Result<(), DocError> {
    if let Some(dir) = path.parent() {
        fs::create_dir_all(dir)?;
    }
    let normalized = text.replace("\r\n", "\n").replace('\r', "\n");
    let tmp = path.with_file_name(format!(
        ".{}.{}.tmp",
        path.file_name().and_then(|s| s.to_str()).unwrap_or("file"),
        std::process::id()
    ));
    {
        let mut f = fs::File::create(&tmp)?;
        f.write_all(normalized.as_bytes())?;
        f.sync_all()?;
    }
    fs::rename(&tmp, path)?;
    Ok(())
}

impl Document {
    pub fn empty() -> Self {
        Document {
            path: None,
            source: String::new(),
            generation: 1,
            kind: DocKind::Markdown,
            readonly: false,
        }
    }

    pub fn from_path(path: &Path) -> Result<(Self, Option<String>), DocError> {
        let (source, warning) = read_file(path)?;
        let doc = Document {
            path: Some(path.to_path_buf()),
            source,
            generation: 1,
            kind: DocKind::from_path(path),
            readonly: false,
        };
        Ok((doc, warning))
    }

    pub fn display_name(&self) -> String {
        self.path
            .as_ref()
            .and_then(|p| p.file_name())
            .map(|s| s.to_string_lossy().into_owned())
            .unwrap_or_else(|| "Untitled".into())
    }

    pub fn bump(&mut self) {
        self.generation = self.generation.wrapping_add(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Read;

    #[test]
    fn utf8_bom_is_stripped() {
        let (s, w) = decode_text(&[0xEF, 0xBB, 0xBF, b'h', b'i']);
        assert_eq!(s, "hi");
        assert!(w.is_none());
    }

    #[test]
    fn utf16le_is_decoded() {
        let mut bytes = vec![0xFF, 0xFE];
        for b in "あ".encode_utf16().flat_map(|u| u.to_le_bytes()) {
            bytes.push(b);
        }
        let (s, _) = decode_text(&bytes);
        assert_eq!(s, "あ");
    }

    #[test]
    fn invalid_utf8_falls_back_with_warning() {
        let (s, w) = decode_text(&[0x82, 0xA0, 0x82, 0xA2]);
        assert!(!s.is_empty());
        assert!(w.is_some());
    }

    #[test]
    fn binary_is_rejected() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path().join("a.md");
        fs::write(&p, [0u8, 1, 2, 3]).unwrap();
        assert!(matches!(read_file(&p), Err(DocError::Binary(_))));
    }

    #[test]
    fn save_is_atomic_and_normalizes_crlf() {
        let tmp = tempfile::tempdir().unwrap();
        let p = tmp.path().join("x.md");
        write_file(&p, "a\r\nb\r\n").unwrap();
        let mut got = String::new();
        fs::File::open(&p).unwrap().read_to_string(&mut got).unwrap();
        assert_eq!(got, "a\nb\n");
        assert!(!tmp.path().join("x.md.tmp").exists());
    }

    #[test]
    fn kind_detection() {
        assert_eq!(DocKind::from_path(Path::new("a.MD")), DocKind::Markdown);
        assert_eq!(DocKind::from_path(Path::new("a.yml")), DocKind::Yaml);
        assert_eq!(DocKind::from_path(Path::new("a.rs")), DocKind::Text);
    }

    #[test]
    fn kind_identifiers_are_stable() {
        assert_eq!(DocKind::Markdown.id(), "md");
        assert_eq!(DocKind::Text.id(), "txt");
        assert_eq!(DocKind::Yaml.id(), "yaml");
        assert!(DocKind::Text.prefers_plain_text());
        assert!(!DocKind::Markdown.prefers_plain_text());
        assert!(!DocKind::Yaml.prefers_plain_text());
    }

    #[test]
    fn txt_extension_is_plain_text() {
        assert_eq!(DocKind::from_path(Path::new("notes.txt")), DocKind::Text);
        assert_eq!(DocKind::from_path(Path::new("notes.TXT")), DocKind::Text);
        assert_eq!(DocKind::from_path(Path::new("README")), DocKind::Text);
    }

    #[test]
    fn kind_for_save_keeps_extension_and_uses_fallback_without_one() {
        // 既存の .txt へ保存しても Markdown へ化けない（要求 2 の核心）。
        assert_eq!(kind_for_save(Path::new("/tmp/a.txt"), DocKind::Markdown), DocKind::Text);
        assert_eq!(kind_for_save(Path::new("/tmp/a.md"), DocKind::Text), DocKind::Markdown);
        assert_eq!(kind_for_save(Path::new("/tmp/a.yaml"), DocKind::Markdown), DocKind::Yaml);
        // 拡張子が無い保存先は、開いていた書類種別を引き継ぐ。
        assert_eq!(kind_for_save(Path::new("/tmp/notes"), DocKind::Text), DocKind::Text);
        assert_eq!(kind_for_save(Path::new("/tmp/notes"), DocKind::Markdown), DocKind::Markdown);
    }
}
