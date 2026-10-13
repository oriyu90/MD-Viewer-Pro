# MD Viewer Pro v1.5.3

## 日本語

- 狭幅ウィンドウでのツールバー溢れを修正しました（最狭幅の戻る・余白設定、狭幅の詳細設定・PDF書き出しに短称表示）。
- 回帰テスト（計998件）ですべて成功しました。

## English

- Fixed toolbar overflow on narrow windows (short labels where needed).
- All 998 regression tests pass.

**Download / ダウンロード**: [MDViewerPro-1.5.3-Installer.dmg](https://github.com/oriyu90/MD-Viewer-Pro/releases/download/1.5.3/MDViewerPro-1.5.3-Installer.dmg)

Apple Silicon macOS build; ad-hoc signed, not Apple-notarized. First launch may require approval under System Settings → Privacy & Security.

**初回起動で「壊れている」と出る場合 / If macOS says the app is damaged**: アプリ自体は壊れていません (The app itself is not damaged). 先にMDViewerPro.app を Applications フォルダへ入れ（DMGの中のまま開かない）、ターミナルで `xattr -cr /Applications/MDViewerPro.app` を実行してから開いてください。DMG 内の `FIRST_LAUNCH.txt` もご覧ください。
