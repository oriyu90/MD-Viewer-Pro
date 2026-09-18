# MD Viewer Pro v1.4.6

## 日本語

- MD編集を開いただけで保存しても、見出しの記法、エスケープ、末尾空行などのMarkdown原文を保持します。
- 編集内容をWebEngineから取得できない場合、古い内容で保存・書き出し・終了を続けず、警告して再試行を待ちます。
- 編集直後の保存やコード内空行を含む既存機能も回帰テストで確認しました。

実際にMD編集で変更した複雑なMarkdownはHTMLからの逆変換で表記が変わることがあります。厳密な原文編集にはTXT編集を使用してください。

## English

- Entering and leaving MD Edit without changes preserves source Markdown, including heading syntax, escapes, and trailing blank lines.
- Failed WebEngine capture now stops save, export, and close instead of writing stale contents.
- Regression tests cover immediate saves, code blank lines, and both capture outcomes.

Complex Markdown can still change formatting after an actual visual edit. Use TXT Edit for exact source editing.

**Download / ダウンロード**: [MDViewerPro-1.4.6-Installer.dmg](https://github.com/oriyu90/MD-Viewer-Pro/releases/download/1.4.6/MDViewerPro-1.4.6-Installer.dmg)

Apple Silicon macOS build; ad-hoc signed, not Apple-notarized. First launch may require approval under System Settings → Privacy & Security.
