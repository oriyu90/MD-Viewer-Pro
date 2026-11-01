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
  tocPinned: false,
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
  $("#scale-range").value = String(s.scale_idx);
  $("#scale-val").textContent = ["50%", "75%", "100%", "125%", "150%"][s.scale_idx] || "100%";
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

let lastSync = 0;
function syncPreviewToEditor() {
  if (state.mode !== "edit" || !state.settings?.follow_scroll) return;
  const now = performance.now();
  if (now - lastSync < 60) return;
  lastSync = now;
  const ed = $("#editor");
  const sc = $("#doc-scroll");
  const edMax = Math.max(1, ed.scrollHeight - ed.clientHeight);
  const ratio = Math.min(1, Math.max(0, ed.scrollTop / edMax));
  sc.scrollTop = ratio * Math.max(0, sc.scrollHeight - sc.clientHeight);
}

function updateActiveLine() {
  const ed = $("#editor");
  const line = ed.value.slice(0, ed.selectionStart).split("\n").length;
  for (const el of $$("#gutter .ln")) {
    el.classList.toggle("cur", Number(el.dataset.line) === line);
  }
  syncPreviewToEditor();
}

function updateGutter() {
  const ed = $("#editor");
  const lines = ed.value.split("\n").length;
  const gutter = $("#gutter");
  if (gutter.dataset.lines !== String(lines)) {
    gutter.dataset.lines = String(lines);
    if (lines <= 4000) {
      gutter.innerHTML = Array.from({ length: lines }, (_, i) => `<span class="ln" data-line="${i + 1}">${i + 1}</span>`).join("");
    } else {
      gutter.textContent = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
    }
  }
  gutter.scrollTop = ed.scrollTop;
}

function updateTocVisibility() {
  const show = !!state.settings?.show_toc && (state.mode === "edit" || state.tocPinned);
  $("#toc-panel").hidden = !show;
  $("#btn-toc").classList.toggle("toggled", show);
}

function setMode(mode) {
  state.mode = mode;
  document.body.dataset.mode = mode;
  const editing = mode === "edit";
  $("#editor-pane").hidden = !editing;
  $("#fmt-toolbar").hidden = !editing;
  $("#btn-back").disabled = !editing;
  for (const b of $$("#mode-seg button")) b.classList.toggle("active", b.dataset.mode === mode);
  updateTocVisibility();
  if (editing) {
    const ed = $("#editor");
    ed.value = state.source;
    ed.scrollTop = 0;
    ed.setSelectionRange(0, 0);
    updateGutter();
    updateActiveLine();
    setTimeout(() => ed.focus({ preventScroll: true }), 30);
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
    setMode(state.boot?.screenshot?.mode === "edit" ? "edit" : "view");
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

function paginateForPdf(pageH) {
  const doc = $("#doc");
  for (const el of $$(".pdf-spacer", doc)) el.remove();
  let page = 0;
  for (const el of Array.from(doc.children)) {
    if (el.classList.contains("pdf-spacer")) continue;
    const h = el.offsetHeight;
    let guard = 0;
    while (guard++ < 6) {
      const top = el.offsetTop;
      const bottom = top + h;
      const limit = (page + 1) * pageH;
      if (bottom <= limit || top >= limit) break;
      if (h > pageH - 30) break;
      const spacer = document.createElement("div");
      spacer.className = "pdf-spacer";
      spacer.style.height = `${limit - top}px`;
      el.before(spacer);
      page++;
    }
  }
  const total = doc.scrollHeight;
  const pages = Math.max(1, Math.ceil(total / pageH));
  const pad = pages * pageH - total;
  if (pad > 0) {
    const spacer = document.createElement("div");
    spacer.className = "pdf-spacer";
    spacer.style.height = `${pad}px`;
    doc.appendChild(spacer);
  }
}

function fillPdfDialog() {
  const s = state.settings;
  $("#pdf-orientation").value = s.pdf_orientation || "portrait";
  const [t0, r0, b0, l0] = s.pdf_margins || [20, 20, 20, 20];
  $("#pdf-m-top").value = t0;
  $("#pdf-m-right").value = r0;
  $("#pdf-m-bottom").value = b0;
  $("#pdf-m-left").value = l0;
  $("#pdf-images").checked = s.pdf_embed_images !== false;
  const sel = $("#pdf-style");
  sel.innerHTML = "";
  const mk = (v, label) => {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = label;
    sel.appendChild(o);
  };
  mk("", t("pdf_theme_follow", "アプリと同じ"));
  mk("dark", t("dark", "ダークモード"));
  mk("light", t("light", "ライトモード"));
  for (const th of state.boot?.themes ?? []) mk(th.name, th.name);
  sel.value = s.pdf_theme || "";
}

const raf2 = () => new Promise((r) => setTimeout(r, 80));

async function runPdfExport(path) {
  const s = state.settings;
  const styleName = s.pdf_theme || s.theme;
  const pal = await invoke("palette_for_theme", { theme: styleName, accent: s.accent_color || "" });
  applyPalette({ palette: pal.palette, dark: pal.dark });
  if (!s.pdf_embed_images) document.body.classList.add("no-images");
  document.body.classList.add("pdf-export");

  const portrait = (s.pdf_orientation || "portrait") !== "landscape";
  const pageW = portrait ? 794 : 1123;
  const pageH = portrait ? 1123 : 794;
  const mm = s.pdf_margins || [20, 20, 20, 20];
  const pad = mm.map((v) => Math.round(v * 96 / 25.4));
  const doc = $("#doc");
  try {
    await raf2();
    doc.style.padding = `${pad[0]}px ${pad[1]}px ${pad[2]}px ${pad[3]}px`;
    doc.style.width = `${pageW}px`;
    paginateForPdf(pageH);
    await raf2();
    const pages = Math.max(1, Math.round(doc.scrollHeight / pageH));
    const bytes = await invoke("export_pdf", { path, pageW, pageH, pages });
    toast(`${t("saved", "保存しました")} (${Math.round(bytes / 1024)} KB / ${pages}p)`);
    return bytes;
  } finally {
    doc.style.padding = "";
    doc.style.width = "";
    document.body.classList.remove("pdf-export", "no-images");
    for (const el of $$(".pdf-spacer")) el.remove();
    if (!TAURI) { /* mock */ }
    renderNow();
  }
}

async function exportPdf() {
  fillPdfDialog();
  const dlg = $("#pdf-dialog");
  const ok = await new Promise((resolve) => {
    dlg.onclose = () => resolve(dlg.returnValue === "ok");
    dlg.showModal();
  });
  if (!ok) return;
  const next = {
    ...state.settings,
    pdf_orientation: $("#pdf-orientation").value,
    pdf_margins: [
      Number($("#pdf-m-top").value) || 0,
      Number($("#pdf-m-right").value) || 0,
      Number($("#pdf-m-bottom").value) || 0,
      Number($("#pdf-m-left").value) || 0,
    ],
    pdf_embed_images: $("#pdf-images").checked,
    pdf_theme: $("#pdf-style").value,
  };
  const boot = await refreshBootstrap(next);
  applyPalette(boot);
  const base = state.docPath ? state.docPath.replace(/\.[^.]+$/, "") : "untitled";
  const path = await invoke("pick_save", { suggested: `${base}.pdf` });
  if (!path) return;
  await runPdfExport(path);
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
  invoke("themes_list").then((list) => { if (Array.isArray(list)) state.boot.themes = list; }).catch(() => {});
  const themeSel = $("#set-theme");
  themeSel.innerHTML = "";
  for (const [val, label] of [["dark", t("dark", "ダークモード")], ["light", t("light", "ライトモード")], ["system", t("system_theme", "システム")]]) {
    const o = document.createElement("option");
    o.value = val; o.textContent = label; themeSel.appendChild(o);
  }
  for (const th of state.boot?.themes ?? []) {
    const o = document.createElement("option");
    o.value = th.name; o.textContent = th.name; themeSel.appendChild(o);
  }
  if (![...themeSel.options].some((o) => o.value === s.theme)) {
    const o = document.createElement("option");
    o.value = s.theme; o.textContent = s.theme; themeSel.appendChild(o);
  }
  themeSel.value = s.theme;
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
  $("#scale-range").addEventListener("input", (e) => {
    const idx = Number(e.target.value);
    $("#scale-val").textContent = ["50%", "75%", "100%", "125%", "150%"][idx] || "100%";
  });
  $("#scale-range").addEventListener("change", async (e) => {
    await refreshBootstrap({ ...state.settings, scale_idx: Number(e.target.value) });
  });
  $("#btn-toc").addEventListener("click", async () => {
    state.tocPinned = !state.tocPinned;
    const show = !state.settings.show_toc;
    state.tocPinned = show;
    updateTocVisibility();
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
  $("#btn-font-remove").addEventListener("click", () => {
    if (!state.fonts?.length) { toast(t("font_none", "追加したフォントはありません")); return; }
    const dlg = document.createElement("dialog");
    dlg.className = "modal";
    dlg.innerHTML = `<form method="dialog" class="modal-body">
      <h2>${escapeHtml(t("font_remove", "フォント削除"))}</h2>
      <select id="font-del-select" style="width:100%;padding:6px;background:var(--btn);border:1px solid var(--border);border-radius:8px">
        ${state.fonts.map((f) => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join("")}
      </select>
      <div class="modal-actions">
        <button value="cancel" class="text-btn">${escapeHtml(t("cancel", "キャンセル"))}</button>
        <button value="ok" class="primary">${escapeHtml(t("ok", "OK"))}</button>
      </div></form>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("close", async () => {
      if (dlg.returnValue === "ok") {
        const fam = dlg.querySelector("#font-del-select").value;
        state.fonts = await invoke("font_remove", { family: fam });
        fillSettingsDialog();
      }
      dlg.remove();
    });
    dlg.showModal();
  });
  $("#btn-pdf").addEventListener("click", exportPdf);

  $("#editor").addEventListener("input", onEditorInput);
  $("#editor").addEventListener("scroll", () => {
    $("#gutter").scrollTop = $("#editor").scrollTop;
    syncPreviewToEditor();
  });
  $("#editor").addEventListener("click", updateActiveLine);
  $("#editor").addEventListener("keyup", updateActiveLine);
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
    if (e.key === "Escape" && findState.open) { closeFind(); return; }
    const mod = e.metaKey || e.ctrlKey;
    if (!mod) return;
    const k = e.key.toLowerCase();
    if (TAURI) return; // ネイティブメニューの accelerator に一本化（二重発火防止）
    if (k === "s") { e.preventDefault(); await saveFile(e.shiftKey); }
    else if (k === "o") { e.preventDefault(); await openFile(); }
    else if (k === "n") { e.preventDefault(); newDocument(); }
    else if (k === "b" && state.mode === "edit") { e.preventDefault(); applyFormat("bold"); }
    else if (k === "i" && state.mode === "edit") { e.preventDefault(); applyFormat("italic"); }
    else if (k === "f") { e.preventDefault(); openFind(); }
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

  wireFind();
  const menuActions = {
    "find": () => openFind(),
    "new": () => newDocument(),
    "new-window": () => invoke("new_window"),
    "open": () => openFile(),
    "save": () => saveFile(false),
    "save-as": () => saveFile(true),
    "export-html": () => exportHtml(),
    "export-pdf": () => exportPdf(),
    "reveal": () => state.docPath && invoke("reveal_path", { path: state.docPath }),
    "close": () => wv && wv.close(),
    "toggle-toc": () => $("#btn-toc").click(),
    "toggle-clip": () => $("#btn-clip").click(),
    "settings": () => $("#btn-settings").click(),
    "guide": () => guide(),
    "gdrive": () => {
      const name = state.docPath ? state.docPath.split("/").pop() : t("unsaved_file", "（未保存）");
      toast(t("gdrive_msg", "ファイル: {fname}\n\nGoogle Drive を開きます。").replace("{fname}", name));
      invoke("open_external", { url: "https://drive.google.com/drive/my-drive" });
    },
    "onedrive": () => {
      const name = state.docPath ? state.docPath.split("/").pop() : t("unsaved_file", "（未保存）");
      toast(t("onedrive_msg", "ファイル: {fname}\n\nOneDrive を開きます。").replace("{fname}", name));
      invoke("open_external", { url: "https://onedrive.live.com" });
    },
    "print": () => printDoc(),
    "page-free": () => $$("#page-seg button").find((b) => b.dataset.page === "free")?.click(),
    "page-a4": () => $$("#page-seg button").find((b) => b.dataset.page === "a4")?.click(),
    "zoom-in": () => changeScale(1),
    "zoom-out": () => changeScale(-1),
    "zoom-reset": () => changeScale(0, true),
    
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

const GUIDE_JA = `# MD Viewer Pro の使い方

## 閲覧
- ツールバーの「閲覧 / 編集」でモードを切り替えます。
- 左の目次から見出しへジャンプできます。
- \`Cmd+F\` でページ内検索、\`Esc\` で閉じます。

## 編集
- 「編集」に切り替えると、左に Markdown ソース、右にプレビューが出ます。
- 書式ツールバーの B / I / H1〜H3 / リストなどが使えます。
- \`Cmd+S\` で保存、\`Cmd+Shift+S\` で名前を付けて保存します。

## 表示
- 「フリー / A4文書」でレイアウトを切り替えます。
- 詳細設定でテーマ・アクセント色・フォント・文字サイズ・改行の扱いを変更できます。

## 書き出し
- ファイルメニューから HTML / PDF を書き出せます（PDF は印刷ダイアログ経由）。
`;

function showStartup() {
  if (!TAURI || state.boot?.selftest_fixture || state.docPath) return;
  setTimeout(() => {
    if (state.docPath || state.source) return;
    const dlg = $("#startup-dialog");
    if (!dlg) return;
    $("#startup-lang").value = state.settings.lang;
    dlg.showModal();
  }, 450);
}

function wireStartup() {
  const dlg = $("#startup-dialog");
  if (!dlg) return;
  const close = () => { if (dlg.open) dlg.close(); };
  $("#startup-lang").addEventListener("change", async (e) => {
    await loadI18n(e.target.value);
    applyI18n();
  });
  $("#startup-open").addEventListener("click", async () => { close(); await openFile(); });
  $("#startup-new").addEventListener("click", () => { close(); newDocument(); });
  $("#startup-guide").addEventListener("click", () => {
    close();
    state.source = GUIDE_JA;
    state.docPath = null;
    state.rendered = null;
    renderNow().then(() => setMode("view"));
    updateTitle();
  });
  dlg.addEventListener("cancel", (e) => { e.preventDefault(); close(); newDocument(); });
}

function guide() {
  state.source = GUIDE_JA;
  state.docPath = null;
  state.rendered = null;
  renderNow().then(() => setMode("view"));
  updateTitle();
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
  state.tocPinned = false;
  updateTocVisibility();
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
    if (q.get("find")) { openFind(); $("#find-input").value = q.get("find"); runFind(q.get("find")); }
    setTimeout(() => {
      const target = q.get("scroll");
      if (target) document.getElementById(target)?.scrollIntoView();
    }, 60);
  }

  // 起動時は空でも案内を出す（旧アプリの起動体験に合わせる）
  if (state.boot?.screenshot) {
    const shot = state.boot.screenshot;
    try {
      const p = await invoke("palette_for_theme", {
        theme: shot.theme,
        accent: state.settings.accent_color || "",
      });
      applyPalette({ palette: p.palette, dark: p.dark });
      state.settings.page_mode = shot.page;
      document.body.dataset.page = shot.page;
      if (shot.mode === "edit") setMode("edit");
    } catch (e) { /* noop */ }
  }

  try { await invoke("ui_ready"); } catch (e) { /* mock */ }

  if (TAURI && state.boot?.pdf_export) {
    const [input, output] = state.boot.pdf_export;
    try {
      await loadPath(input);
      await new Promise((r) => setTimeout(r, 300));
      const bytes = await runPdfExport(output);
      await invoke("selftest_report", { payload: { ok: true, mode: "pdf-export", pdfBytes: bytes } });
    } catch (err) {
      await invoke("selftest_report", { payload: { ok: false, error: String(err) } });
    }
  }

  wireStartup();

  if (state.boot?.initial && !state.docPath) {
    try { await loadPath(state.boot.initial); } catch (e) { /* noop */ }
  }

  if (state.boot?.dialog) {
    const d = state.boot.dialog;
    setTimeout(() => {
      if (d === "settings") { fillSettingsDialog(); $("#settings-dialog").showModal(); }
      else if (d === "margin") { $("#margin-dialog").showModal(); }
      else if (d === "pdf") { try { fillPdfDialog(); $("#pdf-dialog").showModal(); } catch (err) { toast("PDF dialog: " + err); } }
      else if (d === "clip") { $("#btn-clip").click(); }
      else if (d === "search") { openFind(); $("#find-input").value = "見出し 1"; runFind("見出し 1"); }
    }, 300);
  } else if (!state.docPath) {
    showStartup();
  }

  if (!state.source) {
    $("#doc").innerHTML = `<div class="welcome"><h1>MD Viewer Pro</h1><p>${escapeHtml(t("startup_hint", "Markdown ファイルを開くか、ドラッグ＆ドロップしてください。"))}</p></div>`;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  boot().catch((e) => {
    document.body.innerHTML = `<pre style="color:#f66;padding:20px">${escapeHtml(String(e))}</pre>`;
  });
});

// ── ページ内検索 ─────────────────────────────────────────────

const findState = { hits: [], idx: -1, open: false };

function clearFindMarks() {
  for (const m of $$("#doc mark.find-hit")) {
    const parent = m.parentNode;
    if (!parent) continue;
    parent.replaceChild(document.createTextNode(m.textContent || ""), m);
    parent.normalize();
  }
  findState.hits = [];
  findState.idx = -1;
  $("#find-count").textContent = "";
}

function runFind(query) {
  clearFindMarks();
  if (!query) return;
  const root = $("#doc");
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      const p = node.parentElement;
      if (!p || p.closest("script,style,mark.find-hit")) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  const needle = query.toLowerCase();
  const targets = [];
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.nodeValue.toLowerCase().includes(needle)) targets.push(node);
  }
  for (const node of targets) {
    const text = node.nodeValue;
    const lower = text.toLowerCase();
    const frag = document.createDocumentFragment();
    let from = 0;
    let at = lower.indexOf(needle, from);
    while (at !== -1) {
      if (at > from) frag.appendChild(document.createTextNode(text.slice(from, at)));
      const mark = document.createElement("mark");
      mark.className = "find-hit";
      mark.textContent = text.slice(at, at + needle.length);
      frag.appendChild(mark);
      findState.hits.push(mark);
      from = at + needle.length;
      at = lower.indexOf(needle, from);
    }
    if (from < text.length) frag.appendChild(document.createTextNode(text.slice(from)));
    node.parentNode?.replaceChild(frag, node);
  }
  if (findState.hits.length) {
    findState.idx = 0;
    focusHit();
  } else {
    $("#find-count").textContent = "0";
  }
}

function focusHit() {
  const hits = findState.hits;
  if (!hits.length) return;
  hits.forEach((h) => h.classList.remove("active"));
  const hit = hits[findState.idx];
  if (!hit) return;
  hit.classList.add("active");
  hit.scrollIntoView({ block: "center" });
  $("#find-count").textContent = `${findState.idx + 1}/${hits.length}`;
}

function openFind() {
  findState.open = true;
  $("#find-bar").hidden = false;
  const input = $("#find-input");
  input.focus();
  input.select();
  if (input.value) runFind(input.value);
}

function closeFind() {
  findState.open = false;
  $("#find-bar").hidden = true;
  $("#find-input").value = "";
  clearFindMarks();
}

function wireFind() {
  $("#find-input").addEventListener("input", (e) => runFind(e.target.value));
  $("#find-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (!findState.hits.length) return;
      findState.idx = (findState.idx + (e.shiftKey ? -1 : 1) + findState.hits.length) % findState.hits.length;
      focusHit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeFind();
    }
  });
  $("#find-next").addEventListener("click", () => {
    if (!findState.hits.length) return;
    findState.idx = (findState.idx + 1) % findState.hits.length;
    focusHit();
  });
  $("#find-close").addEventListener("click", closeFind);
}

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
      const out = fx; // open_path で許可済みのパスのみ保存できる
      await invoke("save_document", { path: out, source: state.source + "\n\n追記\n" });
      const back = await invoke("read_file_text", { path: out });
      res.savedBytes = back.length;
      res.savedHasAppend = back.includes("追記");
      const pdf = fx.replace(/\.md$/, ".pdf");
      res.pdfBytes = await invoke("export_pdf", { path: pdf, pageW: 794, pageH: 1123, pages: 1 });
    }
    res.i18nKeys = Object.keys(state.t).length;
    res.lang = state.lang;
    res.htmlBytes = r.html.length;
  } catch (e) {
    res.error = String(e);
  }
  await invoke("selftest_report", { payload: res });
}
