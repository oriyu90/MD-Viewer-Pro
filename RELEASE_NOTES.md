# Release notes

## v26.0.1 — Rust rewrite (pre-release)

First release of the Rust/Tauri 2 line. The v1.5.x Python application remains the
previous stable line.

### Highlights

- Full rewrite of the document engine in Rust (`mdv-core`): parsing, sanitization,
  settings, themes and file I/O no longer depend on Python or Qt.
- Native macOS window, menu bar, file associations, Finder "Open With", single
  instance and window-state restoration.
- Offline KaTeX math and Mermaid diagrams, bundled with the app.
- In-page search (Cmd+F) with highlight and next/previous navigation.
- Source-of-truth editing: the Markdown source is never reconstructed from HTML, so
  saving can no longer rewrite or damage the document.
- Ad-hoc signed, not notarized (same policy as v1.5.x).
- Security hardening: HTML is sanitized in Rust (ammonia) and file writes are restricted to
  paths the user explicitly chose in a save/open dialog.

### Measured (Apple Silicon, macOS 26.4)

| Metric | v1.5.3 (Python/Qt) | v26.0.1 (Rust/Tauri) |
|---|---|---|
| App binary | — (PyInstaller bundle) | 7.7 MB |
| DMG | ~175 MB | see asset |
| Cold start | ~8.5 s (Windows), several seconds on macOS | ~1 s |
| Peak RSS (main process) | ~300 MB total | ~44 MB (main) + WebView |

### Known limitations

- PDF export uses the macOS print dialog ("Save as PDF").
- WYSIWYG Markdown editing is replaced by source + preview.
- Windows/Linux builds are not shipped in this release.
- Google Drive / OneDrive upload is not implemented.

### Upgrade notes

Settings are read from the existing `~/.mdviewer/settings.json` (unknown keys are
ignored, missing keys use defaults). Clipboard phrases are read from
`~/.mdviewer/clipboard.json`. The Python app can still be used side by side.
