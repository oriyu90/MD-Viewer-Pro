# MD Viewer Pro v1.5.1

## 日本語

- クリップボードの長文切り詰め案内、スケール変更時の行高更新、起動直後の幅0、初期サンプル文の4点を修正しました。
- 回帰テスト（計998件）ですべて成功しました。

## English

- Fixed 4 issues: clipboard truncation notice, row heights on scaling, zero-width panel at launch, and sample text rows.
- All 998 regression tests pass.

**Download / ダウンロード**: [MDViewerPro-1.5.1-Installer.dmg](https://github.com/oriyu90/MD-Viewer-Pro/releases/download/1.5.1/MDViewerPro-1.5.1-Installer.dmg)

Apple Silicon macOS build; ad-hoc signed, not Apple-notarized. First launch may require approval under System Settings → Privacy & Security.

**初回起動で「壊れている」と出る場合 / If macOS says the app is damaged**: アプリ自体は壊れていません (The app itself is not damaged). 先にMDViewerPro.app を Applications フォルダへ入れ（DMGの中のまま開かない）、ターミナルで `xattr -cr /Applications/MDViewerPro.app` を実行してから開いてください。DMG 内の `FIRST_LAUNCH.txt` もご覧ください。
