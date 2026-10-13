# MD Viewer Pro v1.5.0

## 日本語

- 詳細設定に「テーマ色」を追加しました。青・緑・オレンジ・赤・紫・ティールのプリセットとカスタム色から、リンク・見出し・ボタン等の強調色を変更できます。PDF書き出しにも反映されます。
- 右側にクリップボードパネルを追加しました。+ ボタンから開くポップアップに貼り付けるとプレーンテキストで保存され、フレーズを押すとコピー、左下の小さな削除ボタンから確認付きで削除できます。
- 狭幅ウィンドウでのツールバー溢れを改善しました。
- 回帰テスト（計998件）ですべて成功しました。

実際にMD編集で変更した複雑なMarkdownはHTMLからの逆変換で表記が変わることがあります。厳密な原文編集にはTXT編集を使用してください。

## English

- Added accent color to Settings: presets (blue, green, orange, red, purple, teal) plus custom colors for links, headings, and buttons, including PDF export.
- Added a right-side Clipboard panel. Paste into the + popup as plain text to save a phrase, click to copy, and delete via the small bottom-left button with confirmation.
- Improved toolbar overflow on narrow windows.
- All 998 regression tests pass.

Complex Markdown can still change formatting after an actual visual edit. Use TXT Edit for exact source editing.

**Download / ダウンロード**: [MDViewerPro-1.5.0-Installer.dmg](https://github.com/oriyu90/MD-Viewer-Pro/releases/download/1.5.0/MDViewerPro-1.5.0-Installer.dmg)

Apple Silicon macOS build; ad-hoc signed, not Apple-notarized. First launch may require approval under System Settings → Privacy & Security.

**初回起動で「壊れている」と出る場合 / If macOS says the app is damaged**: アプリ自体は壊れていません (The app itself is not damaged). 先にMDViewerPro.app を Applications フォルダへ入れ（DMGの中のまま開かない）、ターミナルで `xattr -cr /Applications/MDViewerPro.app` を実行してから開いてください。DMG 内の `FIRST_LAUNCH.txt` もご覧ください。
