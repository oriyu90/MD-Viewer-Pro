# MD Viewer Pro v1.4.7

## 日本語

- MD編集でリンク・画像が挿入できるようになりました。ツールバーの「リンク」「画像」ボタンがURL入力ダイアログを開き、選択中の文字列をリンク文言にして挿入します。
- PDF書き出しの形式崩れを改善しました。書き出し中に画面のスクロールやカーソル位置が失われなくなり、表・コード・図・数式のページ切断や配色の再現性が向上しました。
- 閲覧・MD編集・TXT編集のプレビューで、右側の広い空白と意図しない横スクロールが出ないようになりました。
- 編集直後の保存やコード内空行を含む既存機能も回帰テスト（計989件）で確認しました。

実際にMD編集で変更した複雑なMarkdownはHTMLからの逆変換で表記が変わることがあります。厳密な原文編集にはTXT編集を使用してください。

## English

- Links and images can now be inserted in MD Edit via URL dialogs on the toolbar; pasting a URL or `[label](URL)` also pastes as a link.
- PDF export layout is improved: a dedicated off-screen page keeps the on-screen state intact, reduces page-break splits, and preserves on-screen colors.
- View, MD Edit, and TXT Edit previews now fit within the document display range with no wide right-side blank area or accidental horizontal scrolling.
- Regression tests (989 total) cover existing behavior including immediate saves and code blank lines.

Complex Markdown can still change formatting after an actual visual edit. Use TXT Edit for exact source editing.

**Download / ダウンロード**: [MDViewerPro-1.4.7-Installer.dmg](https://github.com/oriyu90/MD-Viewer-Pro/releases/download/1.4.7/MDViewerPro-1.4.7-Installer.dmg)

Apple Silicon macOS build; ad-hoc signed, not Apple-notarized. First launch may require approval under System Settings → Privacy & Security.

**初回起動で「壊れている」と出る場合 / If macOS says the app is damaged**: アプリ自体は壊れていません (The app itself is not damaged). 先にMDViewerPro.app を Applications フォルダへ入れ（DMGの中のまま開かない）、ターミナルで `xattr -cr /Applications/MDViewerPro.app` を実行してから開いてください。DMG 内の `FIRST_LAUNCH.txt` もご覧ください。

（2026-09-22 追記 / Update）同梱ガイドのファイル名をASCIIのみに修正したDMGに差し替えました。旧DMGで起動できない場合は新しいDMGをダウンロードし直してください (Re-download if the old DMG won't open: bundled guide filenames are now ASCII-only to survive Unicode normalization during copying)。
