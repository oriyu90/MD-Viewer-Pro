# MD Viewer Pro v1.5.2

## 日本語

- クリップボードのカード全面をコピー範囲にしました（右半分の空き領域もコピーできます）。
- フリー表示に入力欄・表示欄の余白を追加（縦長は全幅、3:1で両端2割）。A4はページ表示のままです。
- B5文書モードを廃止しました。
- 回帰テスト（計998件）ですべて成功しました。

## English

- Whole clipboard cards now copy (right-side empty areas included).
- Free mode gains aspect-based margins (full width when portrait, 20% blanks per side at 3:1). A4 keeps its page look.
- Removed B5 mode.
- All 998 regression tests pass.

**Download / ダウンロード**: [MDViewerPro-1.5.2-Installer.dmg](https://github.com/oriyu90/MD-Viewer-Pro/releases/download/1.5.2/MDViewerPro-1.5.2-Installer.dmg)

Apple Silicon macOS build; ad-hoc signed, not Apple-notarized. First launch may require approval under System Settings → Privacy & Security.

**初回起動で「壊れている」と出る場合 / If macOS says the app is damaged**: アプリ自体は壊れていません (The app itself is not damaged). 先にMDViewerPro.app を Applications フォルダへ入れ（DMGの中のまま開かない）、ターミナルで `xattr -cr /Applications/MDViewerPro.app` を実行してから開いてください。DMG 内の `FIRST_LAUNCH.txt` もご覧ください。
