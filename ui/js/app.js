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
  dirtyBlocks: new Set(),
  page: "free",
  accent: "",
  renderToken: 0,
  renderTimer: 0,
  clips: [],
  fonts: [],
  searchIndex: -1,
  // β4.0: 書類種別（"md" / "txt" / "yaml"）と書式ツールバーの使用履歴。
  // .txt を開いて書式ツールバーを使っていない場合は、保存も .txt のまま行う。
  docKind: "md",
  formatUsed: false,
  tbScale: 1,
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
  $("#btn-toc").classList.toggle("toggled", !!s.show_toc);
  updateTocVisibility();
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

  setupTableBtns();
  buildToc();
}

// MD編集: 表の直後に列・行の追加ボタンを出す（v1.5.3 の _mdvSetupTableBtns）。
function setupTableBtns() {
  const root = $("#doc");
  for (const b of $$(".mdv-table-ctrl", root)) b.remove();
  if (state.mode !== "md") return;
  for (const tbl of $$("table", root)) {
    const ctrl = document.createElement("div");
    ctrl.className = "mdv-table-ctrl";
    ctrl.contentEditable = "false";
    const mk = (label, title, fn) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      b.title = title;
      b.onclick = (e) => { e.stopPropagation(); e.preventDefault(); fn(); };
      return b;
    };
    ctrl.appendChild(mk(t("table_add_col", "+ 列"), t("table_add_col_title", "列を追加"), () => {
      for (const row of tbl.querySelectorAll("tr")) {
        const isHead = tbl.querySelector("thead") && row.closest("thead") !== null;
        const cell = document.createElement(isHead ? "th" : "td");
        cell.textContent = isHead ? t("table_col", "列") : t("table_cell", "セル");
        row.appendChild(cell);
      }
      markBlockDirty(tbl);
      setupTableBtns();
    }));
    ctrl.appendChild(mk(t("table_add_row", "+ 行"), t("table_add_row_title", "行を追加"), () => {
      const tbody = tbl.querySelector("tbody") || tbl;
      const lastRow = tbody.querySelector("tr:last-child");
      if (!lastRow) return;
      const tr = document.createElement("tr");
      for (let j = 0; j < lastRow.cells.length; j++) {
        const td = document.createElement("td");
        td.textContent = t("table_cell", "セル");
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
      markBlockDirty(tbl);
      setupTableBtns();
    }));
    tbl.insertAdjacentElement("afterend", ctrl);
  }
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
  if (state.mode !== "txt" || !state.settings?.follow_scroll) return;
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
  // 1.5.3 と同じく、設定の show_toc だけで全モード共通に表示する。
  // （旧実装は閲覧モードで tocPinned が無いと隠れてしまっていた）
  const show = !!state.settings?.show_toc;
  $("#toc-panel").hidden = !show;
  $("#btn-toc").classList.toggle("toggled", show);
}

function isEditing() {
  return state.mode === "md" || state.mode === "txt";
}

async function setMode(mode) {
  const prev = state.mode;
  if (prev === "md" && mode !== "md") {
    await commitMdEdits();
  }
  state.mode = mode;
  document.body.dataset.mode = mode;
  const editing = mode !== "view";
  const md = mode === "md";
  const txt = mode === "txt";
  const doc = $("#doc");
  if (md) {
    doc.contentEditable = "true";
    doc.classList.add("md-edit");
  } else if (prev === "md") {
    doc.contentEditable = "false";
    doc.classList.remove("md-edit");
  }
  $("#editor-pane").hidden = !txt;
  $("#fmt-toolbar").hidden = !editing;
  $("#btn-back").disabled = !editing;
  for (const b of $$("#mode-seg button")) b.classList.toggle("active", b.dataset.mode === mode);
  updateTocVisibility();
  if (md) {
    await ensureTurndown().catch(() => {});
    clearTimeout(state.renderTimer);
    await renderNow();
    state.dirtyBlocks.clear();
    doc.focus({ preventScroll: true });
  }
  if (txt) {
    const ed = $("#editor");
    ed.value = state.source;
    ed.scrollTop = 0;
    ed.setSelectionRange(0, 0);
    updateGutter();
    updateActiveLine();
    setTimeout(() => ed.focus({ preventScroll: true }), 30);
  }
}

function blockIndex(el) {
  const children = Array.from($("#doc").children)
    .filter((x) => !x.classList.contains("front-matter") && !x.classList.contains("mdv-table-ctrl"));
  return children.indexOf(el);
}

function markBlockDirty(el) {
  const idx = blockIndex(el);
  if (idx >= 0) state.dirtyBlocks.add(idx);
  markDirty(true);
}

function currentBlock() {
  const sel = window.getSelection();
  if (!sel || !sel.rangeCount) return null;
  let n = sel.anchorNode;
  const el = n && n.nodeType === 3 ? n.parentElement : n;
  return el && el.closest ? el.closest("#doc > *") : null;
}

function replaceBlock(el, next) {
  const idx = blockIndex(el);
  el.replaceWith(next);
  if (idx >= 0) state.dirtyBlocks.add(idx);
  markDirty(true);
  placeCaretEnd(next);
}

function placeCaretEnd(el) {
  const range = document.createRange();
  range.selectNodeContents(el);
  range.collapse(false);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}

function wrapSelectionHtml(tag) {
  const sel = window.getSelection();
  if (!sel || !sel.rangeCount || sel.isCollapsed) return;
  const range = sel.getRangeAt(0);
  const el = document.createElement(tag);
  el.textContent = range.toString();
  range.deleteContents();
  range.insertNode(el);
  const block = el.closest("#doc > *");
  if (block) markBlockDirty(block);
}

function askText(title, initial) {
  return new Promise((resolve) => {
    const dlg = document.createElement("dialog");
    dlg.className = "modal";
    dlg.innerHTML = `<form method="dialog" class="modal-body">
      <h2>${escapeHtml(title)}</h2>
      <input id="ask-input" type="text">
      <div class="modal-actions">
        <button value="cancel" class="text-btn">${escapeHtml(t("cancel", "キャンセル"))}</button>
        <button value="ok">${escapeHtml(t("ok", "OK"))}</button>
      </div></form>`;
    document.body.appendChild(dlg);
    const input = dlg.querySelector("#ask-input");
    input.value = initial || "";
    dlg.addEventListener("close", () => {
      const v = dlg.returnValue === "ok" ? input.value.trim() : "";
      dlg.remove();
      resolve(v);
    });
    dlg.showModal();
    input.focus();
  });
}

async function applyFormatMd(kind) {
  const doc = $("#doc");
  doc.focus();
  if (kind === "bold" || kind === "italic") {
    document.execCommand(kind);
    const b = currentBlock();
    if (b) markBlockDirty(b);
    return;
  }
  if (kind === "strike") return wrapSelectionHtml("s");
  if (kind === "code") return wrapSelectionHtml("code");
  if (kind === "link") {
    const url = await askText(t("link_dialog_title", t("fmt_link", "リンク")), "https://");
    if (!url) return;
    document.execCommand("createLink", false, url);
    const b = currentBlock();
    if (b) markBlockDirty(b);
    return;
  }
  if (kind === "image") {
    const url = await askText(t("fmt_img", "画像"), "https://");
    if (!url) return;
    const p = document.createElement("p");
    const img = document.createElement("img");
    img.src = url;
    img.alt = "";
    p.appendChild(img);
    doc.appendChild(p);
    markDirty(true);
    return;
  }

  const block = currentBlock();
  switch (kind) {
    case "h1":
    case "h2":
    case "h3": {
      const h = document.createElement(kind);
      h.innerHTML = block ? block.innerHTML : "";
      if (block) replaceBlock(block, h);
      else doc.appendChild(h);
      return;
    }
    case "body": {
      const p = document.createElement("p");
      p.innerHTML = block ? block.innerHTML : "";
      if (block) replaceBlock(block, p);
      return;
    }
    case "quote": {
      if (!block) return;
      const bq = document.createElement("blockquote");
      bq.innerHTML = block.outerHTML;
      replaceBlock(block, bq);
      return;
    }
    case "list":
    case "num":
    case "check": {
      if (!block) return;
      const list = document.createElement(kind === "num" ? "ol" : "ul");
      const li = document.createElement("li");
      li.innerHTML = block.innerHTML;
      list.appendChild(li);
      replaceBlock(block, list);
      return;
    }
    case "hr": {
      const hr = document.createElement("hr");
      if (block) replaceBlock(block, hr);
      else doc.appendChild(hr);
      return;
    }
    case "table": {
      const table = document.createElement("table");
      const head = escapeHtml(t("fmt_table_head", "見出し"));
      const cell = escapeHtml(t("fmt_table_cell", "内容"));
      table.innerHTML = `<thead><tr><th>${head}</th><th>${head}</th></tr></thead><tbody><tr><td>${cell}</td><td>${cell}</td></tr></tbody>`;
      if (block) block.after(table);
      else doc.appendChild(table);
      markDirty(true);
      setupTableBtns();
      return;
    }
  }
}

let turndownPromise = null;
function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    s.onerror = reject;
    document.head.appendChild(s);
  });
}
function ensureTurndown() {
  if (window.TurndownService) return Promise.resolve();
  if (!turndownPromise) {
    turndownPromise = loadScript("assets/turndown/turndown.js").then(() =>
      loadScript("assets/turndown/turndown-plugin-gfm.js").catch(() => {}),
    );
  }
  return turndownPromise;
}

function htmlToMarkdown(el) {
  const clone = el.cloneNode(true);
  for (const n of clone.querySelectorAll(".copy-btn")) n.remove();
  for (const n of clone.querySelectorAll(".mdv-table-ctrl")) n.remove();
  for (const n of clone.querySelectorAll(".katex")) {
    const ann = n.querySelector('annotation[encoding="application/x-tex"]');
    const tex = ann ? ann.textContent : n.textContent;
    n.replaceWith(document.createTextNode(`$${tex}$`));
  }
  for (const n of clone.querySelectorAll(".mermaid")) {
    const pre = document.createElement("pre");
    pre.textContent = "```mermaid\n" + (n.textContent || "").trim() + "\n```";
    n.replaceWith(pre);
  }
  const T = window.TurndownService;
  if (!T) return clone.textContent || "";
  const td = new T({
    headingStyle: "atx",
    codeBlockStyle: "fenced",
    bulletListMarker: "-",
    emDelimiter: "*",
    strongDelimiter: "**",
  });
  if (window.turndownPluginGfm) td.use(window.turndownPluginGfm.gfm);
  return (td.turndown(clone.innerHTML) || "").trim();
}

async function commitMdEdits() {
  if (!state.dirtyBlocks.size || !state.rendered?.blocks) return false;
  const doc = $("#doc");
  const children = Array.from(doc.children)
    .filter((el) => !el.classList.contains("front-matter") && !el.classList.contains("mdv-table-ctrl"));
  if (children.length !== state.rendered.blocks.length) {
    toast(t("md_edit_mismatch", "この文書はMD編集で安全に反映できません。TXT編集を使ってください。"));
    return false;
  }
  const lines = state.source.split("\n");
  const idxs = [...state.dirtyBlocks].sort((a, b) => b - a);
  for (const i of idxs) {
    const b = state.rendered.blocks[i];
    if (!b) continue;
    const md = htmlToMarkdown(children[i]);
    lines.splice(b.start - 1, b.end - b.start + 1, ...md.split("\n"));
  }
  state.source = lines.join("\n");
  state.dirtyBlocks.clear();
  markDirty(true);
  const keep = state.mode;
  state.mode = "view";
  await renderNow();
  state.mode = keep;
  if (keep === "md") {
    setupTableBtns();
    doc.focus({ preventScroll: true });
  }
  return true;
}

function onMdInput(e) {
  if (state.mode !== "md") return;
  const t2 = e.target.nodeType === 3 ? e.target.parentElement : e.target;
  const block = t2 && t2.closest ? t2.closest("#doc > *") : null;
  if (!block) return;
  markBlockDirty(block);
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

function versionLabel(v) {
  if (!v) return "";
  const b = String(v).match(/-beta\.(.+)$/);
  if (b) return `β${b[1]}`;
  const a = String(v).match(/-alpha\.(.+)$/);
  if (a) return `α${a[1]}`;
  return "";
}

function updateTitle() {
  const name = state.docPath ? state.docPath.split("/").pop() : t("untitled", "無題");
  const label = versionLabel(state.boot?.version) ? ` ${versionLabel(state.boot.version)}` : "";
  document.title = `${state.dirty ? "● " : ""}${name} — MD Viewer Pro${label}`;
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
    state.docKind = normalizeDocKind(d.kind, d.path);
    state.formatUsed = false;
    $("#doc").innerHTML = d.rendered.html;
    $("#editor").value = d.source;
    updateGutter();
    ensureMermaidDeferred();
    enhance();
    $("#doc-scroll").scrollTop = 0;
    updateTitle();
    updateDocKindHint();
    setMode(state.boot?.screenshot?.mode === "md" ? "md" : state.boot?.screenshot?.mode === "txt" ? "txt" : "view");
    if (d.warning) toast(d.warning);
  } catch (e) {
    toast(String(e));
  }
}

/* Rust 側の kind（"md" / "txt" / "yaml"）を正とし、欠けていれば拡張子から補う。
   旧バージョンの open_path は .txt も "md" と返していたため、パスで上書きする。 */
const MD_EXTS = ["md", "markdown", "mdown", "mkd"];
const YAML_EXTS = ["yml", "yaml"];

function ensureMermaidDeferred() {
  mermaidReady = false;
}

async function openFile() {
  if (!(await confirmDiscard())) return;
  const p = await invoke("pick_file");
  if (p) await loadPath(p);
}

function kindFromPath(path) {
  if (!path) return null;
  const m = String(path).toLowerCase().match(/\.([^./\\]+)$/);
  if (!m) return null;
  if (YAML_EXTS.includes(m[1])) return "yaml";
  if (MD_EXTS.includes(m[1])) return "md";
  return "txt";
}

function normalizeDocKind(kind, path) {
  const fromPath = kindFromPath(path);
  if (fromPath) return fromPath;
  return kind === "txt" || kind === "yaml" ? kind : "md";
}

function isPlainTextDoc() {
  return state.docKind === "txt";
}

/* 保存ダイアログの推奨ファイル名。既存パスがあればその名前、無ければ種別に合わせる。 */
function suggestedSaveName() {
  if (state.docPath) return state.docPath.split("/").pop();
  return isPlainTextDoc() ? "untitled.txt" : "untitled.md";
}

/* 保存先の拡張子が変わったら書類種別を追従させる（.txt → .md など）。 */
function applySavedKind(savedPath) {
  const next = normalizeDocKind(null, savedPath);
  const prev = state.docKind;
  state.docKind = next;
  state.formatUsed = false;
  if (prev !== next) {
    // .txt になったら MD編集は使えないので TXT編集へ寄せる。
    if (next === "txt" && state.mode === "md") setMode("txt");
    if (next !== "txt" && state.mode === "txt") setMode("view");
  }
  updateTitle();
  updateDocKindHint();
}

/* .txt 文書を開いているときだけ、保存形式の案内を出す（要求 2 の可視化）。 */
function updateDocKindHint() {
  const el = $("#doc-kind-hint");
  if (!el) return;
  const show = isPlainTextDoc() && !!state.docPath;
  el.hidden = !show;
  if (show) el.textContent = t("txt_doc_notice", "このファイルはテキスト（.txt）です。");
}

/* .txt 文書で書式ツールバーを使ったときだけ、.md への変換を確認する。
   戻り値: "save"（.md として保存） / "keep"（.txt のまま保存） / "cancel"（中止）。
   ボタン名まで i18n で切り替えられるよう、アプリ内ダイアログで尋ねる。 */
function confirmTxtToMarkdown() {
  const msg = t("txt_to_md_msg",
    "書式ツールバーで Markdown 記法を追加しました。.md ファイルとして保存しますか？");
  const hint = t("txt_to_md_hint",
    "「.txt のまま保存」を選ぶと、拡張子は .txt のまま保存されます。");
  const saveAsMd = t("txt_to_md_save", ".md で保存");
  const keepTxt = t("txt_to_md_keep", ".txt のまま保存");
  const cancel = t("cancel", "キャンセル");
  return new Promise((resolve) => {
    const dlg = document.createElement("dialog");
    dlg.className = "modal confirm-modal";
    dlg.innerHTML = `<form method="dialog" class="modal-body">
      <h2>${escapeHtml(t("txt_to_md_title", "保存形式の確認"))}</h2>
      <p class="confirm-msg">${escapeHtml(msg)}</p>
      <p class="hint">${escapeHtml(hint)}</p>
      <div class="modal-actions">
        <button value="cancel" class="text-btn">${escapeHtml(cancel)}</button>
        <button value="keep" class="text-btn">${escapeHtml(keepTxt)}</button>
        <button value="save">${escapeHtml(saveAsMd)}</button>
      </div></form>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("close", () => {
      const v = dlg.returnValue;
      dlg.remove();
      resolve(v === "save" || v === "keep" ? v : "cancel");
    });
    dlg.showModal();
  });
}

async function saveFile(forceAs = false) {
  if (state.mode === "md") await commitMdEdits();
  let path = state.docPath;

  // .txt 文書で書式ツールバーを使った場合のみ、.md への変換を提案する。
  // （書式ツールバーを使っていなければ、拡張子も保存先も一切変えない）
  if (!forceAs && path && isPlainTextDoc() && state.formatUsed) {
    const choice = await confirmTxtToMarkdown();
    if (choice === "cancel") return false;
    if (choice === "save") {
      const base = path.replace(/\.[^.]+$/, "");
      const target = await invoke("pick_save", { suggested: `${base}.md`, kind: "md" });
      if (!target) return false;
      path = target;
    }
  }

  if (!path || forceAs) {
    path = await invoke("pick_save", { suggested: suggestedSaveName(), kind: state.docKind });
    if (!path) return false;
  }
  try {
    const saved = await invoke("save_document", { path, source: state.source });
    state.docPath = saved;
    applySavedKind(saved);
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
  const path = await invoke("pick_save", { suggested: `${base}.html`, kind: "html" });
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
  if (state.mode === "md") await commitMdEdits();
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
  const path = await invoke("pick_save", { suggested: `${base}.pdf`, kind: "pdf" });
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

function applyFormatText(kind) {
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
      const sel = ed.value.slice(ed.selectionStart, ed.selectionEnd) || t("fmt_link_default", "リンク");
      return replaceSelection(`[${sel}](https://)`, sel.length + 3, 8);
    }
    case "image": return insertBlock(`![${t("img_alt_default", "alt")}](${t("fmt_img_placeholder", "path/to/image.png")})`);
    case "table": {
      const head = t("fmt_table_head", "見出し");
      const cell = t("fmt_table_cell", "内容");
      return insertBlock(`| ${head} | ${head} |\n| --- | --- |\n| ${cell} | ${cell} |`);
    }
  }
}

function applyFormat(kind) {
  // 書式ツールバー（Markdown 記法）を使ったことを記録する。
  // .txt 文書でこれが立つと、保存時に .md への変換を案内する。
  state.formatUsed = true;
  if (state.mode === "md") return applyFormatMd(kind);
  return applyFormatText(kind);
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
      <textarea id="clip-text" rows="6"></textarea>
      <p class="hint">${escapeHtml(t("clip_add_hint", "貼り付けたテキストをそのまま保存します。"))}</p>
      <div class="modal-actions">
        <button value="cancel" class="text-btn">${escapeHtml(t("cancel", "キャンセル"))}</button>
        <button value="ok">${escapeHtml(t("ok", "OK"))}</button>
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

function openMarginDialog() {
  const [mt, mr, mb, ml] = state.settings.margins;
  $("#m-top").value = mt; $("#m-right").value = mr; $("#m-bottom").value = mb; $("#m-left").value = ml;
  $("#margin-dialog").showModal();
}

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
      if (state.mode === "txt") setMode("txt");
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
    const show = !state.settings.show_toc;
    await refreshBootstrap({ ...state.settings, show_toc: show });
    updateTocVisibility();
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
  $("#btn-margin").addEventListener("click", openMarginDialog);
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
      <select id="font-del-select">
        ${state.fonts.map((f) => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join("")}
      </select>
      <div class="modal-actions">
        <button value="cancel" class="text-btn">${escapeHtml(t("cancel", "キャンセル"))}</button>
        <button value="ok">${escapeHtml(t("ok", "OK"))}</button>
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
  $("#doc").addEventListener("input", onMdInput);

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
    else if (k === "b" && isEditing()) { e.preventDefault(); applyFormat("bold"); }
    else if (k === "i" && isEditing()) { e.preventDefault(); applyFormat("italic"); }
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

// 説明文面は v1.5.3 の _set_sample()（main_v1.5.3.py:7681）の ja 版そのもの。
// （同版は 資料箱/sample_*.md を読むが、本リポジトリに同ファイルは無いため埋め込み文面で代替）
const GUIDE_JA = [
  "# MD Viewer Pro へようこそ",
  "",
  "上部バーでモード・レイアウト・スケールを切り替えられます。",
  "",
  "## 機能一覧",
  "",
  "| 機能 | 説明 |",
  "| :--- | :--- |",
  "| 閲覧モード | Markdown をきれいにレンダリング |",
  "| MD編集 | レンダリングフォーマットのままテキストを直接編集 |",
  "| TXT編集 | 左エディタ + 右リアルタイムプレビュー |",
  "| A4文書 | 印刷向けA4レイアウト・余白設定 |",
  "| 詳細設定 | フォント・言語・テーマ・テーマ色・太字変更 |",
  "| テーマ色 | 詳細設定で強調色を変更（プリセット＋カスタム） |",
  "| クリップボード | 右側パネルに定型文を保存（押すとコピー・左下の削除で整理） |",
  "| プラグインテーマ | ~/.mdviewer/themes/ にJSONを置いて配色追加 |",
  "",
  "## チェックリスト",
  "",
  "- [x] Markdown 表示",
  "- [x] リアルタイムプレビュー",
  "- [x] コードブロックのコピーボタン",
  "- [x] PDF/HTML書き出し",
  "- [x] プラグインテーマ",
  "- [ ] クラウド同期（予定）",
  "",
  "## コードブロック",
  "",
  "```python",
  "def hello():",
  "    print('Hello, MD Viewer Pro!')",
  "```",
  "",
  "> TXT編集またはMD編集モードに切り替えると書式ツールバーが表示されます。",
].join("\n");

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
  // ダイアログを閉じて何も選ばなかったら説明を開く（1.5.3 のガイド導線）。
  dlg.addEventListener("cancel", (e) => { e.preventDefault(); close(); guide(); });
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
  // 新規文書は Markdown として扱う（保存時に .txt を選べば .txt 文書になる）。
  state.docKind = "md";
  state.formatUsed = false;
  $("#doc").innerHTML = "";
  $("#editor").value = "";
  updateGutter();
  updateTitle();
  updateDocKindHint();
  setMode("txt");
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
    if (q.get("mode") === "md") setMode("md"); else if (q.get("mode") === "txt" || q.get("mode") === "edit") setMode("txt");
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
      if (shot.mode === "md") setMode("md");
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
  const vl = versionLabel(state.boot?.version);
  if (vl) {
    const h = $("#startup-dialog h2");
    if (h) h.textContent = `MD Viewer Pro ${vl}`;
  }

  if (state.boot?.initial && !state.docPath) {
    try { await loadPath(state.boot.initial); } catch (e) { /* noop */ }
  }

  if (state.boot?.dialog) {
    const d = state.boot.dialog;
    setTimeout(() => {
      if (d === "settings") { fillSettingsDialog(); $("#settings-dialog").showModal(); }
      else if (d === "margin") { openMarginDialog(); }
      else if (d === "pdf") { try { fillPdfDialog(); $("#pdf-dialog").showModal(); } catch (err) { toast("PDF dialog: " + err); } }
      else if (d === "clip") { $("#btn-clip").click(); }
      else if (d === "search") { openFind(); $("#find-input").value = "見出し 1"; runFind("見出し 1"); }
      else if (d === "txt2md") { confirmTxtToMarkdown(); }
    }, 300);
  } else if (!state.docPath) {
    showStartup();
  }

  syncWrapWidth();
  syncToolbarScale();
  addEventListener("resize", onViewportResize);
  // `resize` はプログラム的リサイズ（ウィンドウマネージャや set_size）で
  // 発火しないことがあるため、レイアウト変化も監視して取りこぼさない。
  if (typeof ResizeObserver !== "undefined") {
    try {
      const ro = new ResizeObserver(() => onViewportResize());
      ro.observe(document.documentElement);
      ro.observe(document.body);
      ro.observe($("#app"));
    } catch (e) { /* 監視できなくても resize で動作する */ }
  }
  // 最後の保険: ウィンドウ寸法の変化を 500ms 間隔で見張る（変化時だけ処理）。
  let lastW = innerWidth, lastH = innerHeight;
  setInterval(() => {
    if (innerWidth !== lastW || innerHeight !== lastH) {
      lastW = innerWidth; lastH = innerHeight;
      onViewportResize();
    }
  }, 250);
}

/* フリー表示の左右余白。ウィンドウ縦横比 1→3 で 0→20% へ線形に広げる
   (Python 版 _side_blank_fraction と同じ式)。 */
function syncWrapWidth() {
  const ratio = innerWidth / Math.max(1, innerHeight);
  const blank = ratio <= 1 ? 0 : Math.min(0.2, 0.2 * (ratio - 1) / 2);
  document.documentElement.style.setProperty("--wrap-w", `${((1 - 2 * blank) * 100).toFixed(1)}%`);
}

/* ツールバーの縦幅係数（β4.0）。
   ウィンドウ縦幅 h に対して（単調増加・連続）:
     h <= 360px        -> 0.80
     360 < h < 900px   -> 0.80 + 0.20 * (h - 360) / 540
     h >= 900px        -> 1.00
   常に [0.80, 1.00] にクランプする（数値の異常値でもレイアウトを壊さない）。
   幅による段階の切り替えは CSS 側（--tb-base / --fmt-base）が担当し、
   その高さ変化は CSS transition で滑らかに補間される。 */
const TB_SCALE_MIN = 0.8;
const TB_SCALE_MAX = 1.0;
const TB_SCALE_FULL_HEIGHT = 900;
const TB_SCALE_MIN_HEIGHT = 360;

function toolbarScaleForHeight(h) {
  const height = Number.isFinite(h) ? h : TB_SCALE_FULL_HEIGHT;
  const span = TB_SCALE_FULL_HEIGHT - TB_SCALE_MIN_HEIGHT;
  const s = TB_SCALE_MIN + (TB_SCALE_MAX - TB_SCALE_MIN) * (height - TB_SCALE_MIN_HEIGHT) / span;
  return Math.min(TB_SCALE_MAX, Math.max(TB_SCALE_MIN, s));
}

/* ツールバーの縦幅係数を滑らかに補間する。
   `--tb-h` は CSS 側の `calc(var(--tb-base) * var(--tb-scale))` のまま残し、
   JS は `--tb-scale` だけを動かす。こうすることで、幅の段階（--tb-base）が
   メディアクエリで変わっても常に反映される（インライン上書きを残さない）。
   CSS の height transition はプログラム的リサイズで止まることがあるため使わない。 */
let tbAnim = 0;
let tbScaleShown = 1;

function syncToolbarScale() {
  const target = toolbarScaleForHeight(innerHeight);
  state.tbScale = target;
  const root = document.documentElement;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  const apply = (v) => {
    tbScaleShown = v;
    root.style.setProperty("--tb-scale", v.toFixed(4));
  };
  if (tbAnim) { clearTimeout(tbAnim); tbAnim = 0; }
  if (reduce || Math.abs(tbScaleShown - target) < 0.0005) {
    apply(target);
    return;
  }
  // 180ms かけて ease-out で近づける（CSS transition はプログラム的リサイズで
  // 止まるため使わない）。rAF が発火しない環境でも動くよう setTimeout で回す。
  const from = tbScaleShown;
  const start = performance.now();
  const DURATION = 180;
  const step = () => {
    const p = Math.min(1, (performance.now() - start) / DURATION);
    const e = 1 - Math.pow(1 - p, 3);
    apply(from + (target - from) * e);
    if (p < 1) tbAnim = setTimeout(step, 16);
    else { tbAnim = 0; apply(target); }
  };
  step();
}

/* resize は 1 フレーム 1 回にまとめる（リサイズ中の再計算を抑える）。
   注意: この WebView では requestAnimationFrame が発火しない状況があるため、
   rAF に頼らず setTimeout で間引く（16ms 程度で実用上は十分滑らか）。 */
let resizeTimer = 0;
function onViewportResize() {
  if (resizeTimer) return;
  resizeTimer = setTimeout(() => {
    resizeTimer = 0;
    try {
      syncWrapWidth();
      syncToolbarScale();
    } catch (e) {
      // レイアウト計算の失敗で UI を止めない（原因はセルフテストで記録する）
      state.resizeError = String(e && e.stack || e);
    }
  }, 16);
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
    res.bootVersion = state.boot?.version;
    res.bootLabel = state.boot?.version_label;
    res.parsedLabel = versionLabel(state.boot?.version);
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
      res.docTitle = document.title;
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

      // MD編集モードの逆変換（ブロック単位）
      const beforeSrc = state.source;
      await setMode("md");
      const p1 = document.querySelector("#doc > p");
      if (p1) {
        p1.textContent = "MD編集テストの段落";
        p1.dispatchEvent(new Event("input", { bubbles: true }));
      }
      res.mdBlocks = state.rendered.blocks.length;
      await commitMdEdits();
      res.mdEditChanged = state.source !== beforeSrc && state.source.includes("MD編集テストの段落");
      res.mdEditKeptHeading = state.source.includes("自動作成ドキュメント");
      await setMode("view");
    }
    res.i18nKeys = Object.keys(state.t).length;
    res.lang = state.lang;
    res.htmlBytes = r.html.length;

    // ── β4.0 回帰: 要求 2（TXT 保存の維持）と要求 3（ツールバー縦幅） ──
    Object.assign(res, await selftestBeta4());
  } catch (e) {
    res.error = String(e);
  }
  await invoke("selftest_report", { payload: res });
}

/* ウィンドウを複数の大きさにして、ツールバーの実測高さを記録する。
   期待値 = 基準値（幅の段階） × 係数（縦幅）。transition が終わるのを待ってから測る。 */
/* ウィンドウの実サイズが目標に近づくまで待つ（最大 1.5 秒）。
   set_size はイベントループ経由で反映されるため、直後に測ると古い値になる。
   innerWidth/innerHeight はウィンドウ外枠より少し小さい（タイトルバー等）ので、
   許容差は 48px とする。 */
async function waitViewport(w, h, maxMs = 1500) {
  const start = performance.now();
  while (performance.now() - start < maxMs) {
    if (Math.abs(innerWidth - w) <= 48 && Math.abs(innerHeight - h) <= 48) return true;
    await sleep(30);
  }
  return false;
}

/* ツールバーの高さが安定するまで待つ（最大 1 秒）。
   180ms の transition 中に測ると、遷移途中の値で誤判定するため。 */
/* 高さが目標値に到達するまで待つ（補間の完了を確実に待つ）。 */
async function waitHeightNear(el, target, maxMs = 2000) {
  const start = performance.now();
  let h = el.getBoundingClientRect().height;
  while (performance.now() - start < maxMs) {
    h = el.getBoundingClientRect().height;
    if (Math.abs(h - target) <= 1.0) return h;
    await sleep(40);
  }
  return h;
}

async function measureToolbarMatrix() {
  const rows = [];
  const errors = [];
  const tb = $("#main-toolbar");
  // 幅の段階（1100 / 780 / 620）と縦幅係数の両方を踏む組み合わせ。
  const sizes = [
    [1280, 900], [1280, 700], [1280, 500],
    [1000, 900], [800, 900], [600, 900],
  ];
  for (const [w, h] of sizes) {
    try {
      // ACL を広げないよう、リサイズは Rust 側のセルフテスト専用コマンドで行う。
      await invoke("selftest_resize", { width: w, height: h });
    } catch (e) {
      errors.push(`${w}x${h}: resize failed: ${e}`);
      continue;
    }
    // リサイズの反映（最大 1.5 秒）を待つ。
    await waitViewport(w, h);
    // 幅の段階（--tb-base）と縦幅係数（--tb-scale）が新しい値になるまで待つ。
    // ここで待たないと、補間前の古い高さを「安定」と誤判定する。
    const cs = getComputedStyle(document.documentElement);
    let base = parseFloat(cs.getPropertyValue("--tb-base"));
    let scale = parseFloat(cs.getPropertyValue("--tb-scale"));
    const expectedScale = toolbarScaleForHeight(innerHeight);
    const deadline = performance.now() + 2000;
    while (performance.now() < deadline) {
      base = parseFloat(cs.getPropertyValue("--tb-base"));
      scale = parseFloat(cs.getPropertyValue("--tb-scale"));
      if (Math.abs(scale - expectedScale) < 0.002) break;
      await sleep(40);
    }
    // 補間（180ms）が終わるまで高さを追う。
    const expected = base * scale;
    const measured = await waitHeightNear(tb, expected, 2000);
    const ok = Math.abs(measured - expected) <= 1.0;
    if (!ok) errors.push(`${w}x${h}: measured ${measured} != expected ${expected.toFixed(1)}`);
    rows.push({
      requested: `${w}x${h}`,
      w: innerWidth, h: innerHeight,
      base: Math.round(base * 10) / 10,
      scale: Math.round(scale * 1000) / 1000,
      expected: Math.round(expected * 10) / 10,
      measured: Math.round(measured * 10) / 10,
      ok,
    });
  }
  try { await invoke("selftest_resize", { width: 1280, height: 900 }); } catch (e) { /* noop */ }
  await sleep(340);
  return { rows, errors, allOk: errors.length === 0 && rows.every((r) => r.ok) };
}

/* 要求 2: .txt を開いて書式ツールバーを使わずに保存しても .txt のまま。
   要求 3: ツールバー高さ = 基準値(幅の段階) × 係数(ウィンドウ縦幅)。
   i18n: ja/en のキー集合が一致し、en に日本語が残らない。 */
async function selftestBeta4() {
  const out = {};
  const tmp = (name) => {
    const fx = state.boot?.selftest_fixture || "";
    const dir = fx.slice(0, fx.lastIndexOf("/"));
    return dir ? `${dir}/${name}` : name;
  };

  // 要求 2-a: .txt を開いて保存 → 拡張子は .txt のまま、内容一致
  // （保存できるのは open_path で許可済みのパスだけなので、見本を open_path で開く）
  const txtPath = tmp("mdvp-selftest.txt");
  try {
    await loadPath(txtPath);
    out.txtKind = state.docKind;
    out.txtKindFromRust = state.rendered ? "ok" : "missing";
    out.txtFormatUsed = state.formatUsed;
    out.txtHintVisible = !$("#doc-kind-hint").hidden;
    state.source += "追記した行\n";
    state.dirty = true;
    const ok = await saveFile(false);
    out.txtSaved = !!ok;
    out.savedPath = state.docPath;
    out.savedExt = (state.docPath || "").split(".").pop();
    out.savedKind = state.docKind;
    out.savedHasAppend = (await invoke("read_file_text", { path: txtPath })).includes("追記した行");
  } catch (e) {
    out.txtError = String(e);
  }

  // 要求 2-b: 書式ツールバーを使うと formatUsed が立ち、.txt 文書のままである
  try {
    state.formatUsed = false;
    applyFormat("bold");
    out.formatUsedAfterToolbar = state.formatUsed;
    out.txtStillPlainAfterToolbar = state.docKind === "txt";
    state.formatUsed = false;
  } catch (e) {
    out.formatError = String(e);
  }

  // 要求 3: ツールバー高さの基準値（幅の段階）と係数（ウィンドウ縦幅）
  try {
    const tb = $("#main-toolbar");
    const fmt = $("#fmt-toolbar");
    const cssVar = (n) => parseFloat(getComputedStyle(document.documentElement).getPropertyValue(n));
    out.tbWidth = innerWidth;
    out.tbHeight = Math.round(tb.getBoundingClientRect().height * 10) / 10;
    out.tbBase = cssVar("--tb-base");
    out.fmtBase = cssVar("--fmt-base");
    out.tbScale = Math.round(cssVar("--tb-scale") * 1000) / 1000;
    out.tbExpected = Math.round(out.tbBase * out.tbScale * 10) / 10;
    out.tbRatioToLegacy = Math.round((out.tbHeight / (out.tbBase / 0.9)) * 1000) / 1000;
    // 書式ツールバーは編集モードでだけ表示されるので、高さ計算は CSS 変数で検査する
    out.fmtComputed = cssVar("--fmt-base") * cssVar("--tb-scale");
    void fmt;
    // 係数の境界（純関数）
    out.scaleAt900 = toolbarScaleForHeight(900);
    out.scaleAt720 = toolbarScaleForHeight(720);
    out.scaleAt360 = toolbarScaleForHeight(360);
    out.scaleClampLow = toolbarScaleForHeight(0);
    out.scaleClampHigh = toolbarScaleForHeight(5000);
    out.scaleNaN = toolbarScaleForHeight(NaN);

    // 実際にウィンドウをリサイズして、幅の段階と縦幅係数の両方を実測する。
    out.tbMatrix = await measureToolbarMatrix();
  } catch (e) {
    out.tbError = String(e);
  }

  // i18n: 5 言語のキー集合一致・en に日本語が残らない
  try {
    const all = state.allI18n || {};
    const base = Object.keys(all.ja || {}).sort().join(",");
    out.i18nSameKeys = Object.keys(all).every((l) => Object.keys(all[l]).sort().join(",") === base);
    const jp = /[\u3040-\u30ff\u4e00-\u9fff]/;
    const enBad = Object.entries(all.en || {}).filter(([, v]) => typeof v === "string" && jp.test(v)).map(([k]) => k);
    out.i18nEnJapaneseKeys = enBad;
    out.i18nLangCount = Object.keys(all).length;
    // 画面に残る未翻訳の日本語（en 時）。data-i18n 由来ではない直書きを検査する。
    const prevLang = state.lang;
    await loadI18n("en");
    applyI18n();
    const uiText = Array.from(document.querySelectorAll(
      "#main-toolbar [data-i18n], #fmt-toolbar [data-i18n], .modal [data-i18n]",
    )).map((el) => el.textContent).join(" ");
    out.i18nUiJapaneseInEn = jp.test(uiText);
    await loadI18n(prevLang);
    applyI18n();
  } catch (e) {
    out.i18nError = String(e);
  }
  return out;
}
