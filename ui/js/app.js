// MD Viewer Pro — UI controller (v26.0.1)
// 役割: 表示と入力の仲介。文書の解析・整形・保存は Rust 側 (mdv-core / Tauri commands)。

const TAURI = window.__TAURI__ ?? null;
const invoke = TAURI ? TAURI.core.invoke : mockInvoke;
const listen = TAURI ? TAURI.event.listen : () => {};

// ブラウザで UI を確認するためのモック（Tauri 外でのみ使用）
const MOCK_HTML = `
<div class="front-matter"><table><tbody>
<tr><th>title</th><td>MD Viewer Pro</td></tr>
<tr><th>tags</th><td>markdown, rust</td></tr>
</tbody></table></div>
<h1 id="md-viewer-pro">MD Viewer Pro</h1>
<p>Rust と Tauri で作り直した Markdown ビューアです。<strong>強調</strong>、<em>斜体</em>、<code>inline code</code>、<a href="https://example.com">リンク</a>が表示できます。</p>
<h2 id="features">主な機能</h2>
<ul><li>閲覧と編集（ソース + プレビュー）</li><li>目次・テーマ・フォント</li><li>数式 <span class="katex">$E = mc^2$</span> と Mermaid</li></ul>
<h2 id="table">表とコード</h2>
<table><thead><tr><th>機能</th><th>状態</th></tr></thead><tbody>
<tr><td>Markdown</td><td>対応</td></tr><tr><td>数式</td><td>対応</td></tr><tr><td>PDF</td><td>印刷経由</td></tr></tbody></table>
<pre><code class="language-rust">fn main() {
    let app = "MD Viewer Pro";
    println!("{app}");
}</code></pre>
<pre><code class="language-mermaid">graph TD; A[Markdown]--&gt;B[HTML]; B--&gt;C[WebView];</code></pre>
<h2 id="math">数式</h2>
<p>インライン $a^2 + b^2 = c^2$ とディスプレイ $$\\int_0^1 x^2\\,dx = \\frac{1}{3}$$</p>
<blockquote><p>引用ブロックはアクセント色の左罫線で表示されます。</p></blockquote>
<h2 id="tasks">タスク</h2>
<ul><li><input type="checkbox" checked disabled> 実装</li><li><input type="checkbox" disabled> レビュー</li></ul>
`;

function mockPalette() {
  return { bg:"#000", bg2:"#111", bg3:"#1c1c1c", border:"#2a2a2a", text:"#c0c0c0", text_dim:"#484848",
    accent:"#4a9eff", heading:"#7ab8f5", toolbar:"#0c0c0c", btn:"#1c1c1c", btn_hover:"#2e2e2e",
    btn_active_bg:"#4a4a4a", btn_active_fg:"#fff", select:"#1a3a5c", code_fg:"#e06c75",
    row_even:"#0d0d0d", sep:"#2a2a2a", copy_btn_bg:"rgba(50,50,50,.85)", copy_btn_fg:"#aaa" };
}

async function mockInvoke(cmd) {
  const settings = {
    version: 2, lang: "ja", theme: "dark", accent_color: "", font_family: "Helvetica Neue",
    font_size: 16, scale_idx: 2, page_mode: "free", margins: [20,20,20,20], hard_breaks: true,
    show_toc: true, show_clip: false, bold_mode: false, recent: [], last_dir: "",
    last_pdf_dir: "", pdf_embed_images: true, window: { width: 1280, height: 900, x: null, y: null, maximized: false },
    window_geometry: "",
  };
  if (cmd === "bootstrap" || cmd === "save_settings") {
    return { version: "26.0.1", settings, palette: mockPalette(), accent: "#4a9eff", heading: "#7ab8f5",
      dark: true, fonts: [], themes: [], recent: [], default_fonts: ["Helvetica Neue","Hiragino Sans"],
      paths: { config: "~/.mdviewer", themes: "~/.mdviewer/themes", fonts: "~/.mdviewer/fonts", clips: "~/.mdviewer/clipboard.json" },
      platform: "macos", selftest_fixture: null };
  }
  if (cmd === "render") {
    return { html: MOCK_HTML, headings: [
        { level:1, text:"MD Viewer Pro", id:"md-viewer-pro" },
        { level:2, text:"主な機能", id:"features" },
        { level:2, text:"表とコード", id:"table" },
        { level:2, text:"数式", id:"math" },
        { level:2, text:"タスク", id:"tasks" } ],
      title: "MD Viewer Pro", front_matter: [["title","MD Viewer Pro"],["tags","markdown, rust"]],
      has_math: true, has_mermaid: true, plain: "" };
  }
  if (cmd === "clips_get") return ["ありがとうございます。", "確認しました。", "よろしくお願いいたします。"];
  if (cmd === "copy_text") return null;
  return null;
}

const state = {
  boot: null,
  settings: null,
  lang: "ja",
  t: {},
  docPath: null,
  source: "",
  rendered: null,
  dirty: false,
  mode: "view",
  page: "free",
  accent: "",
  renderToken: 0,
  renderTimer: 0,
  clips: [],
  fonts: [],
  searchIndex: -1,
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// ── i18n ────────────────────────────────────────────────────────

function t(key, fallback = "") {
  return state.t[key] ?? fallback ?? key;
}

function applyI18n() {
  for (const el of $$("[data-i18n]")) {
    const v = state.t[el.dataset.i18n];
    if (v != null && v !== "") el.textContent = v;
  }
  for (const el of $$("[data-i18n-title]")) {
    const v = state.t[el.dataset.i18nTitle];
    if (v != null && v !== "") el.title = v;
  }
  for (const el of $$("[data-i18n-placeholder]")) {
    const v = state.t[el.dataset.i18nPlaceholder];
    if (v != null && v !== "") el.placeholder = v;
  }
}

// ── テーマ・設定の反映 ──────────────────────────────────────────

const SCALES = [0.5, 0.75, 1.0, 1.25, 1.5];

function applyPalette(boot) {
  const p = boot.palette;
  const root = document.documentElement.style;
  for (const [k, v] of Object.entries(p)) {
    root.setProperty(`--${k.replace(/_/g, "-")}`, v);
  }
  document.body.dataset.theme = boot.dark ? "dark" : "light";
}

function applySettings(s) {
  state.settings = s;
  state.page = s.page_mode;
  state.accent = s.accent_color || "";
  document.body.dataset.page = s.page_mode;
  const scale = SCALES[s.scale_idx] ?? 1;
  document.documentElement.style.setProperty("--doc-size", `${s.font_size * scale}px`);
  document.documentElement.style.setProperty("--doc-font", `"${s.font_family}", "Hiragino Sans", "Yu Gothic UI", sans-serif`);
  const [mt, mr, mb, ml] = s.margins;
  document.documentElement.style.setProperty("--mt", `${mt}mm`);
  document.documentElement.style.setProperty("--mr", `${mr}mm`);
  document.documentElement.style.setProperty("--mb", `${mb}mm`);
  document.documentElement.style.setProperty("--ml", `${ml}mm`);
  $("#scale").value = String(s.scale_idx);
  for (const b of $$("#mode-seg button")) b.classList.toggle("active", b.dataset.mode === state.mode);
  for (const b of $$("#page-seg button")) b.classList.toggle("active", b.dataset.page === s.page_mode);
  document.body.classList.toggle("bold-mode", !!s.bold_mode);
  $("#btn-toc").classList.toggle("toggled", !!s.show_toc);
}

async function refreshBootstrap(settings) {
  const boot = await invoke("save_settings", { settings });
  state.boot = boot;
  applyPalette(boot);
  applySettings(boot.settings);
  state.fonts = boot.fonts;
  return boot;
}

// ── 文書の描画 ──────────────────────────────────────────────────

let mermaidReady = false;

function ensureMermaid() {
  if (mermaidReady || typeof window.mermaid === "undefined") return;
  window.mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: state.boot?.dark ? "dark" : "default",
    fontFamily: "inherit",
  });
  mermaidReady = true;
}

function enhance() {
  const root = $("#doc");

  // Mermaid: ```mermaid フェンスを図へ置換
  for (const code of $$("pre > code.language-mermaid", root)) {
    const pre = code.parentElement;
    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = code.textContent;
    pre.replaceWith(div);
  }
  ensureMermaid();
  if (mermaidReady) {
    window.mermaid.run({ nodes: $$(".mermaid", root) }).catch((e) => console.warn("mermaid", e));
  }

  // コードハイライト
  if (window.hljs) {
    for (const el of $$("pre code", root)) {
      try { window.hljs.highlightElement(el); } catch (e) { /* noop */ }
    }
  }

  // 数式
  if (window.renderMathInElement) {
    try {
      window.renderMathInElement(root, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\[", right: "\\]", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\(", right: "\\)", display: false },
        ],
        throwOnError: false,
        ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "option"],
      });
    } catch (e) { console.warn("katex", e); }
  }

  // コピーボタン
  for (const pre of $$("pre", root)) {
    if (pre.querySelector(".copy-btn") || pre.closest(".mermaid")) continue;
    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.textContent = t("copy", "コピー");
    btn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const code = pre.querySelector("code");
      try {
        await invoke("copy_text", { text: code ? code.innerText : pre.innerText });
        toast(t("copied", "コピーしました"));
      } catch (e) { toast(String(e)); }
    });
    pre.appendChild(btn);
  }

  buildToc();
}

function buildToc() {
  const list = $("#toc-list");
  list.innerHTML = "";
  const hs = state.rendered?.headings ?? [];
  if (!hs.length) {
    const d = document.createElement("div");
    d.className = "clip-empty";
    d.textContent = t("toc_empty", "見出しがありません");
    list.appendChild(d);
    return;
  }
  hs.forEach((h, i) => {
    const b = document.createElement("button");
    b.className = "toc-item";
    b.dataset.level = String(h.level);
    b.dataset.idx = String(i);
    b.textContent = h.text;
    b.addEventListener("click", () => {
      const el = document.getElementById(h.id);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    list.appendChild(b);
  });
}

function updateActiveToc() {
  const scroll = $("#doc-scroll");
  if (!scroll || !state.rendered?.headings?.length) return;
  const top = scroll.getBoundingClientRect().top + 24;
  let active = -1;
  state.rendered.headings.forEach((h, i) => {
    const el = document.getElementById(h.id);
    if (el && el.getBoundingClientRect().top <= top) active = i;
  });
  for (const b of $$("#toc-list .toc-item")) {
    b.classList.toggle("active", Number(b.dataset.idx) === active);
  }
}

async function renderNow({ keepScroll = true } = {}) {
  const token = ++state.renderToken;
  const hardBreaks = !!state.settings?.hard_breaks;
  let r;
  try {
    r = await invoke("render", { source: state.source, hardBreaks });
  } catch (e) {
    toast(String(e));
    return;
  }
  if (token !== state.renderToken) return;
  state.rendered = r;
  const scrollTop = $("#doc-scroll").scrollTop;
  $("#doc").innerHTML = r.html;
  enhance();
  if (keepScroll) $("#doc-scroll").scrollTop = scrollTop;
  else $("#doc-scroll").scrollTop = 0;
  updateActiveToc();
}

function scheduleRender() {
  clearTimeout(state.renderTimer);
  state.renderTimer = setTimeout(() => renderNow(), 120);
}

// ── エディタ ────────────────────────────────────────────────────

function updateGutter() {
  const ed = $("#editor");
  const lines = ed.value.split("\n").length;
  const gutter = $("#gutter");
  if (gutter.dataset.lines !== String(lines)) {
    gutter.dataset.lines = String(lines);
    gutter.textContent = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
  }
  gutter.scrollTop = ed.scrollTop;
}

function setMode(mode) {
  state.mode = mode;
  document.body.dataset.mode = mode;
  const editing = mode === "edit";
  $("#editor-pane").hidden = !editing;
  $("#fmt-toolbar").hidden = !editing;
  $("#btn-back").disabled = !editing;
  for (const b of $$("#mode-seg button")) b.classList.toggle("active", b.dataset.mode === mode);
  if (editing) {
    $("#editor").value = state.source;
    updateGutter();
    setTimeout(() => $("#editor").focus(), 30);
  }
}

function onEditorInput() {
  state.source = $("#editor").value;
  markDirty(true);
  updateGutter();
  scheduleRender();
}

function markDirty(v) {
  if (state.dirty === v) return;
  state.dirty = v;
  updateTitle();
}

function updateTitle() {
  const name = state.docPath ? state.docPath.split("/").pop() : t("untitled", "無題");
  document.title = `${state.dirty ? "● " : ""}${name} — MD Viewer Pro`;
  try {
    if (!TAURI) return;
    const w = TAURI.webviewWindow.getCurrentWebviewWindow();
    w.setTitle(document.title);
  } catch (e) { /* noop */ }
}

// ── ファイル操作 ────────────────────────────────────────────────

async function loadPath(path) {
  try {
    const d = await invoke("open_path", { path });
    state.docPath = d.path;
    state.source = d.source;
    state.rendered = d.rendered;
    state.dirty = false;
    $("#doc").innerHTML = d.rendered.html;
    $("#editor").value = d.source;
    updateGutter();
    ensureMermaidDeferred();
    enhance();
    $("#doc-scroll").scrollTop = 0;
    updateTitle();
    setMode("view");
    if (d.warning) toast(d.warning);
  } catch (e) {
    toast(String(e));
  }
}

function ensureMermaidDeferred() {
  mermaidReady = false;
}

async function openFile() {
  if (!(await confirmDiscard())) return;
  const p = await invoke("pick_file");
  if (p) await loadPath(p);
}

async function saveFile(forceAs = false) {
  let path = state.docPath;
  if (!path || forceAs) {
    const suggested = path ? path.split("/").pop() : "untitled.md";
    path = await invoke("pick_save", { suggested });
    if (!path) return false;
  }
  try {
    const saved = await invoke("save_document", { path, source: state.source });
    state.docPath = saved;
    markDirty(false);
    toast(t("saved", "保存しました"));
    return true;
  } catch (e) {
    toast(String(e));
    return false;
  }
}

async function exportHtml() {
  const base = state.docPath ? state.docPath.replace(/\.[^.]+$/, "") : "untitled";
  const path = await invoke("pick_save", { suggested: `${base}.html` });
  if (!path) return;
  const content = buildStandaloneHtml();
  try {
    await invoke("save_text", { path, content });
    toast(t("saved", "保存しました"));
  } catch (e) { toast(String(e)); }
}

function buildStandaloneHtml() {
  const css = Array.from(document.styleSheets)
    .map((sheet) => {
      try {
        return Array.from(sheet.cssRules).map((r) => r.cssText).join("\n");
      } catch (e) { return ""; }
    })
    .join("\n");
  const title = state.rendered?.title || (state.docPath ? state.docPath.split("/").pop() : "MD Viewer Pro");
  const body = $("#doc").innerHTML;
  return `<!doctype html>
<html lang="${state.lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)}</title>
<style>${css}
html,body{background:#fff;color:#111;}
body{margin:0;padding:40px 16px;}
#doc{max-width:820px;margin:0 auto;}
</style></head>
<body class="export"><article id="doc" class="markdown-body">${body}</article></body></html>`;
}

async function printDoc() {
  try {
    await invoke("print_page");
  } catch (e) { toast(String(e)); }
}

async function confirmDiscard() {
  if (!state.dirty) return true;
  const ok = window.confirm(t("unsaved_msg", "変更が保存されていません。続行しますか？"));
  return ok;
}

// ── 書式操作 ────────────────────────────────────────────────────

function replaceSelection(text, selectOffset = 0, selectLen = 0) {
  const ed = $("#editor");
  const start = ed.selectionStart;
  const end = ed.selectionEnd;
  ed.setRangeText(text, start, end, "end");
  ed.selectionStart = start + selectOffset;
  ed.selectionEnd = start + selectOffset + selectLen;
  ed.focus();
  onEditorInput();
}

function wrapSelection(before, after = before) {
  const ed = $("#editor");
  const sel = ed.value.slice(ed.selectionStart, ed.selectionEnd) || t("fmt_text_placeholder", "テキスト");
  replaceSelection(before + sel + after, before.length, sel.length);
}

function prefixLines(prefix) {
  const ed = $("#editor");
  const value = ed.value;
  const start = value.lastIndexOf("\n", ed.selectionStart - 1) + 1;
  let end = value.indexOf("\n", ed.selectionEnd);
  if (end === -1) end = value.length;
  const block = value.slice(start, end) || "";
  const lines = block.split("\n").map((l) => prefix + l.replace(/^(\s*)(#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s+)?/, "$1"));
  const out = lines.join("\n");
  ed.setSelectionRange(start, end);
  ed.setRangeText(out, start, end, "end");
  ed.focus();
  onEditorInput();
}

function stripLinePrefix() {
  const ed = $("#editor");
  const value = ed.value;
  const start = value.lastIndexOf("\n", ed.selectionStart - 1) + 1;
  let end = value.indexOf("\n", ed.selectionEnd);
  if (end === -1) end = value.length;
  const block = value.slice(start, end);
  const out = block
    .split("\n")
    .map((l) => l.replace(/^(\s*)(#{1,6}\s+|[-*+]\s+\[[ xX]\]\s+|[-*+]\s+|\d+\.\s+|>\s+)/, "$1"))
    .join("\n");
  ed.setSelectionRange(start, end);
  ed.setRangeText(out, start, end, "end");
  ed.focus();
  onEditorInput();
}

function insertBlock(text) {
  const ed = $("#editor");
  const pos = ed.selectionStart;
  const before = ed.value.slice(0, pos);
  const prefix = before.length === 0 || before.endsWith("\n\n") ? "" : before.endsWith("\n") ? "\n" : "\n\n";
  const insert = prefix + text + (text.endsWith("\n") ? "" : "\n");
  ed.setRangeText(insert, pos, ed.selectionEnd, "end");
  ed.focus();
  onEditorInput();
}

function applyFormat(kind) {
  switch (kind) {
    case "bold": return wrapSelection("**");
    case "italic": return wrapSelection("*");
    case "strike": return wrapSelection("~~");
    case "code": return wrapSelection("`");
    case "h1": return prefixLines("# ");
    case "h2": return prefixLines("## ");
    case "h3": return prefixLines("### ");
    case "body": return stripLinePrefix();
    case "list": return prefixLines("- ");
    case "num": return prefixLines("1. ");
    case "check": return prefixLines("- [ ] ");
    case "quote": return prefixLines("> ");
    case "hr": return insertBlock("\n---\n");
    case "link": {
      const ed = $("#editor");
      const sel = ed.value.slice(ed.selectionStart, ed.selectionEnd) || "リンク";
      return replaceSelection(`[${sel}](https://)`, sel.length + 3, 8);
    }
    case "image": return insertBlock("![alt](path/to/image.png)");
    case "table": return insertBlock("| 見出し | 見出し |\n| --- | --- |\n| 内容 | 内容 |");
  }
}

// ── クリップボードパネル ────────────────────────────────────────

function renderClips() {
  const list = $("#clip-list");
  list.innerHTML = "";
  if (!state.clips.length) {
    const d = document.createElement("div");
    d.className = "clip-empty";
    d.textContent = t("clip_empty", "保存されたフレーズはありません");
    list.appendChild(d);
    return;
  }
  state.clips.forEach((text, idx) => {
    const card = document.createElement("div");
    card.className = "clip-card";
    card.textContent = text;
    card.title = t("clip_copy_hint", "クリックでコピー");
    card.addEventListener("click", async () => {
      await invoke("copy_text", { text });
      toast(t("clip_copied", "コピーしました"));
    });
    const del = document.createElement("button");
    del.className = "del";
    del.textContent = "×";
    del.title = t("clip_delete", "削除");
    del.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      if (!window.confirm(t("clip_delete_msg", "このフレーズを削除しますか？").replace("{phrase}", text.slice(0, 80)))) return;
      state.clips = await invoke("clip_remove", { index: idx });
      renderClips();
    });
    card.appendChild(del);
    list.appendChild(card);
  });
}

function openClipDialog() {
  const dlg = document.createElement("dialog");
  dlg.className = "modal";
  dlg.innerHTML = `
    <form method="dialog" class="modal-body">
      <h2>${escapeHtml(t("clip_add_title", "フレーズを追加"))}</h2>
      <textarea id="clip-text" rows="6" style="width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:10px;color:var(--text)"></textarea>
      <p class="hint">${escapeHtml(t("clip_add_hint", "貼り付けたテキストをそのまま保存します。"))}</p>
      <div class="modal-actions">
        <button value="cancel" class="text-btn">${escapeHtml(t("cancel", "キャンセル"))}</button>
        <button value="ok" class="primary">${escapeHtml(t("ok", "OK"))}</button>
      </div>
    </form>`;
  document.body.appendChild(dlg);
  dlg.addEventListener("close", async () => {
    if (dlg.returnValue === "ok") {
      const text = dlg.querySelector("#clip-text").value;
      if (text.trim()) {
        state.clips = await invoke("clip_add", { text });
        renderClips();
      }
    }
    dlg.remove();
  });
  dlg.showModal();
  dlg.querySelector("#clip-text").focus();
}

// ── 設定ダイアログ ──────────────────────────────────────────────

const ACCENTS = [
  ["", "default"],
  ["#4a9eff", "blue"],
  ["#3ecf8e", "green"],
  ["#ff9f43", "orange"],
  ["#ff6b6b", "red"],
  ["#a78bfa", "purple"],
  ["#2dd4bf", "teal"],
];

function fillSettingsDialog() {
  const s = state.settings;
  $("#set-lang").value = s.lang;
  $("#set-theme").value = s.theme;
  $("#set-font").innerHTML = "";
  const fonts = [...new Set([...(state.boot?.default_fonts ?? []), ...(state.fonts ?? [])])];
  for (const f of fonts) {
    const o = document.createElement("option");
    o.value = f;
    o.textContent = f;
    $("#set-font").appendChild(o);
  }
  if (!fonts.includes(s.font_family)) {
    const o = document.createElement("option");
    o.value = s.font_family;
    o.textContent = s.font_family;
    $("#set-font").appendChild(o);
  }
  $("#set-font").value = s.font_family;
  $("#set-fontsize").value = String(s.font_size);
  $("#set-fontsize-val").textContent = `${s.font_size}px`;
  $("#set-bold").checked = !!s.bold_mode;
  $("#set-hardbreaks").checked = !!s.hard_breaks;

  const wrap = $("#accent-swatches");
  wrap.innerHTML = "";
  for (const [hex, name] of ACCENTS) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `swatch${hex ? "" : " default"}`;
    b.dataset.hex = hex;
    b.title = name;
    if (hex) b.style.background = hex;
    b.setAttribute("aria-pressed", String((s.accent_color || "") === hex));
    b.addEventListener("click", () => {
      for (const x of $$(".swatch", wrap)) x.setAttribute("aria-pressed", "false");
      b.setAttribute("aria-pressed", "true");
    });
    wrap.appendChild(b);
  }
}

async function commitSettings() {
  const swatch = $(".swatch[aria-pressed='true']");
  const accent = swatch ? swatch.dataset.hex : "";
  const next = {
    ...state.settings,
    lang: $("#set-lang").value,
    theme: $("#set-theme").value,
    accent_color: accent,
    font_family: $("#set-font").value,
    font_size: Number($("#set-fontsize").value),
    bold_mode: $("#set-bold").checked,
    hard_breaks: $("#set-hardbreaks").checked,
  };
  await refreshBootstrap(next);
  state.lang = next.lang;
  await loadI18n(next.lang);
  applyI18n();
  await renderNow();
}

async function loadI18n(lang) {
  const all = state.allI18n ?? (await (await fetch("i18n.json")).json());
  state.allI18n = all;
  state.lang = lang;
  state.t = all[lang] ?? all.ja;
  document.documentElement.lang = lang;
}

// ── 補助 ────────────────────────────────────────────────────────

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

let toastTimer = 0;
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 2200);
}

// ── イベント配線 ────────────────────────────────────────────────

function wire() {
  $("#btn-back").addEventListener("click", () => setMode("view"));
  for (const b of $$("#mode-seg button")) {
    b.addEventListener("click", () => setMode(b.dataset.mode));
  }
  for (const b of $$("#page-seg button")) {
    b.addEventListener("click", async () => {
      const page = b.dataset.page;
      await refreshBootstrap({ ...state.settings, page_mode: page });
      if (state.mode === "edit") setMode("edit");
    });
  }
  $("#scale").addEventListener("change", async (e) => {
    await refreshBootstrap({ ...state.settings, scale_idx: Number(e.target.value) });
  });
  $("#btn-toc").addEventListener("click", async () => {
    const show = !state.settings.show_toc;
    $("#toc-panel").hidden = !show;
    await refreshBootstrap({ ...state.settings, show_toc: show });
  });
  $("#btn-clip").addEventListener("click", async () => {
    const show = $("#clip-panel").hidden;
    $("#clip-panel").hidden = !show;
    $("#btn-clip").classList.toggle("toggled", show);
    await refreshBootstrap({ ...state.settings, show_clip: show });
  });
  $("#clip-add").addEventListener("click", openClipDialog);
  $("#btn-settings").addEventListener("click", () => {
    fillSettingsDialog();
    $("#settings-dialog").showModal();
  });
  $("#settings-dialog").addEventListener("close", async (e) => {
    if (e.target.returnValue === "ok") await commitSettings();
  });
  $("#btn-margin").addEventListener("click", () => {
    const [mt, mr, mb, ml] = state.settings.margins;
    $("#m-top").value = mt; $("#m-right").value = mr; $("#m-bottom").value = mb; $("#m-left").value = ml;
    $("#margin-dialog").showModal();
  });
  $("#margin-dialog").addEventListener("close", async (e) => {
    if (e.target.returnValue !== "ok") return;
    const margins = [
      Number($("#m-top").value) || 0,
      Number($("#m-right").value) || 0,
      Number($("#m-bottom").value) || 0,
      Number($("#m-left").value) || 0,
    ];
    await refreshBootstrap({ ...state.settings, margins });
  });
  $("#btn-theme-dir").addEventListener("click", () => invoke("open_themes_dir"));
  $("#btn-font-add").addEventListener("click", async () => {
    state.fonts = await invoke("font_add");
    fillSettingsDialog();
  });
  $("#btn-pdf").addEventListener("click", printDoc);

  $("#editor").addEventListener("input", onEditorInput);
  $("#editor").addEventListener("scroll", () => { $("#gutter").scrollTop = $("#editor").scrollTop; });
  $("#editor").addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      replaceSelection("  ");
    }
  });
  $("#doc-scroll").addEventListener("scroll", updateActiveToc);

  for (const b of $$("#fmt-toolbar button")) {
    b.addEventListener("mousedown", (e) => e.preventDefault());
    b.addEventListener("click", () => applyFormat(b.dataset.fmt));
  }

  document.addEventListener("keydown", async (e) => {
    const mod = e.metaKey || e.ctrlKey;
    if (!mod) return;
    const k = e.key.toLowerCase();
    if (k === "s") { e.preventDefault(); await saveFile(e.shiftKey); }
    else if (k === "o") { e.preventDefault(); await openFile(); }
    else if (k === "n") { e.preventDefault(); newDocument(); }
    else if (k === "b" && state.mode === "edit") { e.preventDefault(); applyFormat("bold"); }
    else if (k === "i" && state.mode === "edit") { e.preventDefault(); applyFormat("italic"); }
  });

  window.addEventListener("dragover", (e) => { e.preventDefault(); });
  window.addEventListener("drop", async (e) => {
    e.preventDefault();
    $("#drop-overlay").hidden = true;
  });

  const wv = TAURI ? TAURI.webviewWindow.getCurrentWebviewWindow() : null;
  if (wv && wv.onDragDropEvent) {
    wv.onDragDropEvent(async (event) => {
      const p = event.payload;
      if (p.type === "over") {
        $("#drop-overlay").hidden = false;
      } else if (p.type === "drop") {
        $("#drop-overlay").hidden = true;
        if (p.paths?.length) loadPath(p.paths[0]);
      } else if (p.type === "leave") {
        $("#drop-overlay").hidden = true;
      }
    });
  }

  if (TAURI) listen("selftest", () => runSelfTest());
  listen("open-path", (e) => loadPath(e.payload));
  listen("activate", () => {
    try { wv.setFocus(); } catch (err) { /* noop */ }
  });

  const menuActions = {
    "new": () => newDocument(),
    "new-window": () => newDocument(),
    "open": () => openFile(),
    "save": () => saveFile(false),
    "save-as": () => saveFile(true),
    "export-html": () => exportHtml(),
    "export-pdf": () => printDoc(),
    "reveal": () => state.docPath && invoke("reveal_path", { path: state.docPath }),
    "close": () => wv && wv.close(),
    "toggle-toc": () => $("#btn-toc").click(),
    "toggle-clip": () => $("#btn-clip").click(),
    "settings": () => $("#btn-settings").click(),
    "page-free": () => $$("#page-seg button").find((b) => b.dataset.page === "free")?.click(),
    "page-a4": () => $$("#page-seg button").find((b) => b.dataset.page === "a4")?.click(),
    "zoom-in": () => changeScale(1),
    "zoom-out": () => changeScale(-1),
    "zoom-reset": () => changeScale(0, true),
    "find": () => toast(t("find_unavailable", "検索は次のアップデートで対応します")),
  };
  listen("menu", (e) => {
    const fn = menuActions[e.payload];
    if (fn) fn();
  });
}

async function changeScale(delta, reset = false) {
  const cur = state.settings.scale_idx;
  const next = reset ? 2 : Math.min(4, Math.max(0, cur + delta));
  if (next === cur) return;
  await refreshBootstrap({ ...state.settings, scale_idx: next });
}

function newDocument() {
  if (state.dirty && !window.confirm(t("unsaved_msg", "変更が保存されていません。続行しますか？"))) return;
  state.docPath = null;
  state.source = "";
  state.rendered = null;
  state.dirty = false;
  $("#doc").innerHTML = "";
  $("#editor").value = "";
  updateGutter();
  updateTitle();
  setMode("edit");
}

// ── 起動 ────────────────────────────────────────────────────────

async function boot() {
  await loadI18n("ja");
  const b = await invoke("bootstrap");
  state.boot = b;
  state.settings = b.settings;
  state.fonts = b.fonts;
  state.clips = await invoke("clips_get");
  applyPalette(b);
  applySettings(b.settings);
  await loadI18n(b.settings.lang);
  applyI18n();
  $("#toc-panel").hidden = !b.settings.show_toc;
  $("#clip-panel").hidden = !b.settings.show_clip;
  $("#btn-clip").classList.toggle("toggled", !!b.settings.show_clip);
  renderClips();
  setMode("view");
  wire();
  updateTitle();

  if (!TAURI) {
    const q = new URLSearchParams(location.search);
    state.source = "# demo";
    if (q.get("page") === "a4") {
      state.settings.page_mode = "a4";
      document.body.dataset.page = "a4";
    }
    await renderNow();
    if (q.get("mode") === "edit") setMode("edit");
    setTimeout(() => {
      const target = q.get("scroll");
      if (target) document.getElementById(target)?.scrollIntoView();
    }, 60);
  }

  // 起動時は空でも案内を出す（旧アプリの起動体験に合わせる）
  if (!state.source) {
    $("#doc").innerHTML = `<div class="welcome"><h1>MD Viewer Pro</h1><p>${escapeHtml(t("startup_hint", "Markdown ファイルを開くか、ドラッグ＆ドロップしてください。"))}</p></div>`;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  boot().catch((e) => {
    document.body.innerHTML = `<pre style="color:#f66;padding:20px">${escapeHtml(String(e))}</pre>`;
  });
});

// ── セルフテスト（--selftest 起動時のみ） ───────────────────────

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function runSelfTest() {
  const sample = [
    "---", "title: Self Test", "tags: [a, b]", "---", "",
    "# 見出し1", "", "本文です。**強調** と *斜体* と `code`。", "",
    "| a | b |", "|---|---|", "| 1 | 2 |", "",
    "- [x] done", "- [ ] todo", "",
    "```rust", "fn main() { let x = 1; }", "```", "",
    "```mermaid", "graph TD; A-->B;", "```", "",
    "$$E = mc^2$$", "",
    "> 引用", "",
  ].join("\n");
  const res = { ok: false, version: state.boot?.version };
  try {
    const r = await invoke("render", { source: sample, hardBreaks: true });
    $("#doc").innerHTML = r.html;
    enhance();
    await sleep(900);
    res.ok = true;
    res.title = r.title;
    res.headings = r.headings.length;
    res.frontMatter = r.front_matter.length;
    res.tables = $$("#doc table").length;
    res.taskItems = $$("#doc input[type=checkbox]").length;
    res.codeBlocks = $$("#doc pre code").length;
    res.highlighted = $$("#doc .hljs-keyword").length;
    res.katex = $$("#doc .katex").length;
    res.mermaidSvg = $$("#doc .mermaid svg").length;
    state.rendered = r;
    buildToc();
    res.tocItems = $$("#toc-list .toc-item").length;
    const fx = state.boot?.selftest_fixture;
    if (fx) {
      await loadPath(fx);
      res.openedHeadings = state.rendered.headings.length;
      res.openedToc = $$("#toc-list .toc-item").length;
      res.openedSourceBytes = state.source.length;
      const out = fx.replace(/\.md$/, "-saved.md");
      await invoke("save_document", { path: out, source: state.source + "\n\n追記\n" });
      const back = await invoke("read_file_text", { path: out });
      res.savedBytes = back.length;
      res.savedHasAppend = back.includes("追記");
    }
    res.i18nKeys = Object.keys(state.t).length;
    res.lang = state.lang;
    res.htmlBytes = r.html.length;
  } catch (e) {
    res.error = String(e);
  }
  await invoke("selftest_report", { payload: res });
}
