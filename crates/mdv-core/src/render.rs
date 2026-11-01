//! Markdown → 安全な HTML。
//!
//! - CommonMark + GFM（表・打ち消し・自動リンク・タスクリスト・脚注）
//! - フロントマター（YAML サブセット）をメタ情報として抽出
//! - 見出し ID を自前で付与し、TOC を生成
//! - ammonia による allowlist サニタイズ（script/iframe/on* は落とす）
//!
//! 数式（KaTeX）と Mermaid は「プレースホルダを残す」ところまで担当し、
//! 実際の描画は WebView 側の同梱アセットが行う（CSP で自前スクリプトのみ許可）。

use comrak::nodes::{AstNode, NodeValue};
use comrak::{parse_document, Arena, Options};
use serde::Serialize;
use std::collections::HashSet;

#[derive(Debug, Clone, Copy)]
pub struct RenderOptions {
    /// Enter 改行をそのまま `<br>` にする（旧アプリ既定 ON）。
    pub hard_breaks: bool,
    /// raw HTML を許可するか（許可しても ammonia で無害化する）。
    pub allow_raw_html: bool,
}

impl Default for RenderOptions {
    fn default() -> Self {
        RenderOptions { hard_breaks: true, allow_raw_html: true }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Heading {
    pub level: u32,
    pub text: String,
    pub id: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct BlockRange {
    /// 1-based, 元ファイル全体での行番号
    pub start: u32,
    pub end: u32,
}

#[derive(Debug, Clone, Serialize)]
pub struct Rendered {
    pub html: String,
    pub headings: Vec<Heading>,
    pub title: Option<String>,
    pub front_matter: Vec<(String, String)>,
    pub has_math: bool,
    pub has_mermaid: bool,
    pub plain: String,
    /// トップレベルブロックの元ソース行範囲（MD編集の逆変換用）
    pub blocks: Vec<BlockRange>,
}

/// 先頭の `---` フェンスを分離する。閉じフェンスが無ければ本文扱い。
fn split_front_matter(src: &str) -> (Option<&str>, &str) {
    let s = src.strip_prefix('\u{feff}').unwrap_or(src);
    let trimmed = s.trim_start_matches(['\r', '\n']);
    if !(trimmed.starts_with("---\n") || trimmed.starts_with("---\r\n")) {
        return (None, src);
    }
    let after = &trimmed[3..];
    let after = after.strip_prefix('\r').unwrap_or(after);
    let after = after.strip_prefix('\n').unwrap_or(after);
    // 閉じフェンスを探す（最大 200 行）
    let mut offset = 0usize;
    for _ in 0..200 {
        let line_end = match after[offset..].find('\n') {
            Some(i) => offset + i,
            None => break,
        };
        let line = after[offset..line_end].trim_end_matches('\r');
        if line == "---" || line == "..." {
            let body_start = line_end + 1;
            return (Some(&after[..offset]), &after[body_start..]);
        }
        offset = line_end + 1;
    }
    (None, src)
}

/// YAML のごく小さなサブセット（key: scalar / key: [a, b] / key:\n  - a）。
fn parse_front_matter(text: &str) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    let mut current: Option<(String, Vec<String>)> = None;

    let flush = |out: &mut Vec<(String, String)>, cur: Option<(String, Vec<String>)>| {
        if let Some((k, v)) = cur {
            let joined = if v.is_empty() { String::new() } else { v.join(", ") };
            out.push((k, joined));
        }
    };

    for raw in text.lines() {
        let line = raw.trim_end();
        if line.trim().is_empty() || line.trim_start().starts_with('#') {
            continue;
        }
        let indent = line.len() - line.trim_start().len();
        let body = line.trim_start();
        if indent == 0 {
            if let Some((k, v)) = body.split_once(':') {
                flush(&mut out, current.take());
                let key = k.trim().to_string();
                let val = v.trim();
                if val.is_empty() {
                    current = Some((key, Vec::new()));
                } else {
                    out.push((key, unquote(val)));
                }
                continue;
            }
        } else if let Some((_, items)) = current.as_mut() {
            if let Some(item) = body.strip_prefix("- ") {
                items.push(unquote(item.trim()));
                continue;
            }
        }
    }
    if let Some(cur) = current {
        flush(&mut out, Some(cur));
    }
    out
}

fn unquote(s: &str) -> String {
    let s = s.trim();
    if s.len() >= 2 {
        let b = s.as_bytes();
        if (b[0] == b'"' && b[s.len() - 1] == b'"') || (b[0] == b'\'' && b[s.len() - 1] == b'\'') {
            let inner = &s[1..s.len() - 1];
            if b[0] == b'"' {
                return inner
                    .replace("\\n", "\n")
                    .replace("\\\"", "\"")
                    .replace("\\t", "\t");
            }
            return inner.replace("''", "'");
        }
        if s.starts_with('[') && s.ends_with(']') {
            return s[1..s.len() - 1]
                .split(',')
                .map(|x| unquote(x.trim()))
                .collect::<Vec<_>>()
                .join(", ");
        }
    }
    s.to_string()
}

fn slugify(text: &str) -> String {
    let mut out = String::new();
    let mut last_dash = false;
    for ch in text.chars() {
        if ch.is_alphanumeric() {
            for lower in ch.to_lowercase() {
                out.push(lower);
            }
            last_dash = false;
        } else if matches!(ch, ' ' | '-' | '_' | '.') && !out.is_empty() && !last_dash {
            out.push('-');
            last_dash = true;
        }
    }
    out.trim_matches('-').to_string()
}

fn collect_heading_text<'a>(node: &'a AstNode<'a>) -> String {
    let mut s = String::new();
    for d in node.descendants() {
        match &d.data.borrow().value {
            NodeValue::Text(t) => s.push_str(t),
            NodeValue::Code(c) => s.push_str(&c.literal),
            NodeValue::SoftBreak | NodeValue::LineBreak => s.push(' '),
            _ => {}
        }
        if std::ptr::eq(d, node) {
            continue;
        }
    }
    s.trim().to_string()
}

fn strip_tags(html: &str) -> String {
    let mut out = String::with_capacity(html.len());
    let mut in_tag = false;
    for ch in html.chars() {
        match ch {
            '<' => in_tag = true,
            '>' => {
                in_tag = false;
                out.push(' ');
            }
            _ if !in_tag => out.push(ch),
            _ => {}
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn sanitizer() -> ammonia::Builder<'static> {
    let mut b = ammonia::Builder::default();
    b.add_tags(["input", "del", "s", "sup", "sub", "kbd", "mark", "details", "summary"])
        .add_tag_attributes("input", ["type", "checked", "disabled"])
        .add_tag_attributes("a", ["href", "title", "target"])
        .add_tag_attributes("img", ["src", "alt", "title", "width", "height"])
        .add_tag_attributes("th", ["align", "colspan", "rowspan"])
        .add_tag_attributes("td", ["align", "colspan", "rowspan"])
        .add_tag_attributes("ol", ["start"])
        .add_generic_attributes(["class"])
        .link_rel(Some("noopener noreferrer"));

    for tag in ["h1", "h2", "h3", "h4", "h5", "h6", "li", "pre", "code", "span", "div"] {
        b.add_tag_attributes(tag, ["id", "class"]);
    }
    b
}

pub fn render_markdown(source: &str, opts: RenderOptions) -> Rendered {
    let (fm, body) = split_front_matter(source);
    let front_matter = fm.map(parse_front_matter).unwrap_or_default();

    let mut options = Options::default();
    options.extension.table = true;
    options.extension.strikethrough = true;
    options.extension.autolink = true;
    options.extension.tasklist = true;
    options.extension.footnotes = true;
    options.extension.description_lists = true;
    options.render.hardbreaks = opts.hard_breaks;
    options.render.r#unsafe = opts.allow_raw_html;

    // 見出しを AST から収集（ID は自前で振る）。
    let arena = Arena::new();
    let root = parse_document(&arena, body, &options);
    let mut headings: Vec<Heading> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    for node in root.descendants() {
        if let NodeValue::Heading(h) = &node.data.borrow().value {
            let text = collect_heading_text(node);
            if text.is_empty() {
                continue;
            }
            let mut id = slugify(&text);
            if id.is_empty() {
                id = format!("h{}", headings.len() + 1);
            }
            let base = id.clone();
            let mut n = 1;
            while seen.contains(&id) {
                id = format!("{base}-{n}");
                n += 1;
            }
            seen.insert(id.clone());
            headings.push(Heading { level: h.level as u32, text, id });
        }
    }

    let mut html = comrak::markdown_to_html(body, &options);

    // 見出しへ id を注入する。生 HTML の <hN> と取り違えないよう、
    // AST から取った見出しテキストと一致するものだけに付与する。
    html = inject_heading_ids(&html, &headings);

    let mut prefix = String::new();
    if !front_matter.is_empty() {
        prefix.push_str("<div class=\"front-matter\"><table><tbody>");
        for (k, v) in &front_matter {
            prefix.push_str("<tr><th>");
            prefix.push_str(&ammonia::clean_text(k));
            prefix.push_str("</th><td>");
            prefix.push_str(&ammonia::clean_text(v));
            prefix.push_str("</td></tr>");
        }
        prefix.push_str("</tbody></table></div>\n");
    }
    html = format!("{prefix}{html}");
    html = sanitizer().clean(&html).to_string();

    let title = front_matter
        .iter()
        .find(|(k, _)| k.eq_ignore_ascii_case("title"))
        .map(|(_, v)| v.clone())
        .or_else(|| headings.iter().find(|h| h.level == 1).map(|h| h.text.clone()));

    // トップレベルブロックの行範囲（フロントマター除去分をオフセット）
    let removed = &source[..source.len() - body.len()];
    let offset = removed.matches('\n').count() as u32;
    let mut blocks: Vec<BlockRange> = Vec::new();
    for child in root.children() {
        let data = child.data.borrow();
        if matches!(data.value, NodeValue::FrontMatter(_)) {
            continue;
        }
        let sp = data.sourcepos;
        if sp.start.line == 0 || sp.end.line == 0 {
            continue;
        }
        blocks.push(BlockRange {
            start: sp.start.line as u32 + offset,
            end: sp.end.line as u32 + offset,
        });
    }

    let has_mermaid = source.contains("```mermaid") || source.contains("~~~mermaid");
    let has_math = detect_math(body);
    let plain = strip_tags(&html);

    Rendered { html, headings, title, front_matter, has_math, has_mermaid, plain, blocks }
}


/// AST 由来の見出しとテキストが一致する `<hN>` にだけ id を付与する。
/// 生 HTML の見出し（例: `<h2>raw</h2>`）はテキストが一致しないため素通りする。
fn inject_heading_ids(html: &str, headings: &[Heading]) -> String {
    let mut out = String::with_capacity(html.len() + headings.len() * 24);
    let mut rest = html;
    let mut idx = 0usize;
    while let Some(pos) = rest.find("<h") {
        let (before, after) = rest.split_at(pos);
        out.push_str(before);
        if idx >= headings.len() {
            out.push_str(after);
            rest = "";
            break;
        }
        let b = after.as_bytes();
        let is_heading = b.len() >= 4 && (b'1'..=b'6').contains(&b[2]) && b[3] == b'>';
        if is_heading {
            let level = b[2] as char;
            let close = format!("</h{level}>");
            if let Some(end) = after.find(&close) {
                let inner = &after[4..end];
                let plain = strip_tags(inner);
                if plain.trim() == headings[idx].text.trim() {
                    out.push_str(&format!("<h{level} id=\"{}\">", headings[idx].id));
                    out.push_str(inner);
                    out.push_str(&close);
                    rest = &after[end + close.len()..];
                    idx += 1;
                    continue;
                }
            }
        }
        out.push_str("<h");
        rest = &after[2..];
    }
    out.push_str(rest);
    out
}

/// `$...$` / `$$...$$` / `\(...\)` の簡易検出。
fn detect_math(src: &str) -> bool {
    if src.contains("\\(") || src.contains("\\[") {
        return true;
    }
    let bytes: Vec<char> = src.chars().collect();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == '$' && (i == 0 || bytes[i - 1] != '\\') {
            if let Some(j) = (i + 1..bytes.len()).find(|&j| bytes[j] == '$') {
                if j > i + 1 && !bytes[i + 1..j].contains(&'\n') {
                    return true;
                }
            }
        }
        i += 1;
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    fn render(src: &str) -> Rendered {
        render_markdown(src, RenderOptions::default())
    }

    #[test]
    fn headings_get_stable_ids_and_toc() {
        let r = render("# はじめに\n\n## 使い方\n\n### 使い方\n");
        assert_eq!(r.headings.len(), 3);
        assert_eq!(r.headings[0].id, "はじめに");
        assert_eq!(r.headings[1].id, "使い方");
        assert_eq!(r.headings[2].id, "使い方-1");
        assert!(r.html.contains("id=\"はじめに\""));
        assert_eq!(r.title.as_deref(), Some("はじめに"));
    }

    #[test]
    fn raw_html_heading_does_not_steal_ids() {
        let r = render("<h2>raw</h2>\n\n# Real\n\n## Second\n");
        assert_eq!(r.headings.len(), 2);
        assert!(r.html.contains("id=\"real\""));
        assert!(r.html.contains("id=\"second\""));
        // raw heading must not receive an AST id
        let raw_pos = r.html.find("raw").unwrap();
        let before = &r.html[..raw_pos];
        let last_h2 = before.rfind("<h2").unwrap();
        assert!(!before[last_h2..].contains("id="));
    }

    #[test]
    fn duplicate_heading_ids_are_unique() {
        let r = render("# a\n\n# a-1\n\n# a\n");
        let ids: Vec<_> = r.headings.iter().map(|h| h.id.as_str()).collect();
        assert_eq!(ids, vec!["a", "a-1", "a-2"]);
    }

    #[test]
    fn gfm_table_and_tasklist() {
        let r = render("| a | b |\n|---|---|\n| 1 | 2 |\n\n- [x] done\n- [ ] todo\n");
        assert!(r.html.contains("<table>"));
        assert!(r.html.contains("type=\"checkbox\""));
    }

    #[test]
    fn script_is_removed() {
        let r = render("<script>alert(1)</script>\n\nhello");
        assert!(!r.html.contains("<script"));
        assert!(r.html.contains("hello"));
    }

    #[test]
    fn onclick_is_removed() {
        let r = render("<a href=\"#\" onclick=\"alert(1)\">x</a>");
        assert!(!r.html.contains("onclick"));
    }

    #[test]
    fn front_matter_is_extracted_and_hidden() {
        let src = "---\ntitle: テスト\ntags: [a, b]\nauthor: Yuki\n---\n\n# 本文\n";
        let r = render(src);
        assert_eq!(r.front_matter.len(), 3);
        assert_eq!(r.title.as_deref(), Some("テスト"));
        assert!(!r.html.contains("tags:"));
        assert!(r.html.contains("front-matter"));
    }

    #[test]
    fn hard_breaks_option() {
        let on = render("a\nb");
        assert!(on.html.contains("<br"));
        let off = render_markdown("a\nb", RenderOptions { hard_breaks: false, ..Default::default() });
        assert!(!off.html.contains("<br"));
    }

    #[test]
    fn mermaid_and_math_detection() {
        let r = render("```mermaid\ngraph TD; A-->B;\n```\n\n$E=mc^2$\n");
        assert!(r.has_mermaid);
        assert!(r.has_math);
        assert!(r.html.contains("language-mermaid"));
    }

    #[test]
    fn inline_code_class_survives_sanitizer() {
        let r = render("```rust\nfn main() {}\n```");
        assert!(r.html.contains("language-rust"));
    }

    #[test]
    fn unclosed_front_matter_is_body() {
        let r = render("---\ntitle: x\n\n# h\n");
        assert!(r.front_matter.is_empty());
        assert!(r.html.contains("<hr"));
    }

    #[test]
    fn plain_text_has_no_tags() {
        let r = render("# 見出し\n\n本文です。");
        assert!(!r.plain.contains('<'));
        assert!(r.plain.contains("本文です"));
    }
}
