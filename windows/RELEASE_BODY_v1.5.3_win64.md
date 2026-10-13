# MD Viewer Pro v1.5.3 — Windows版 (x64)

## 日本語

- `MDViewerPro-1.5.3-win64-Setup.exe`（GUIインストーラー・推奨）と
  `MDViewerPro-1.5.3-win64-portable.zip`（ポータブル）を追加しました。
  このバージョンから完全GUIの独自インストーラー（NSIS・日本語/English選択・
  現在のユーザーのみ・管理者権限不要・アンインストーラー付き）で導入できます。
- アプリ本体はmacOS版 v1.5.3 と同じソース（テーマ色・クリップボードパネル・
  B5廃止・狭幅短称表示を含む）＋ Windows調整
  （%APPDATA%/MDViewerPro 保存・Yu Gothic UI既定・LF統一・シングルインスタンス）。
- インストーラーでは .md 関連付けを任意で選べます（既定では変更しない）。
  `windows\register_assoc.ps1` でも登録可能です。
- 署名なし配布のためSmartScreenが出ることがあります。
  「詳細情報」→「実行」で起動してください。
- 回帰テスト計998件すべて成功（Windows実機）。

## English

- Added `MDViewerPro-1.5.3-win64-Setup.exe` (GUI installer, recommended) and
  `MDViewerPro-1.5.3-win64-portable.zip` (portable) for Windows 10/11 64-bit.
  From this version, Windows ships its own full-GUI installer (NSIS,
  Japanese/English, per-user, no admin, with uninstaller).
- Same v1.5.3 source as macOS (accent color, clipboard panel, B5 removal,
  narrow-width short labels) plus Windows adjustments
  (%APPDATA%/MDViewerPro, Yu Gothic UI, LF, single-instance).
- File association is an optional installer step (off by default);
  `windows\register_assoc.ps1` also works.
- Unsigned, so SmartScreen may appear ("More info" → "Run anyway").
- All 998 regression tests pass on Windows.

**Download / ダウンロード**:
- [MDViewerPro-1.5.3-win64-Setup.exe](https://github.com/oriyu90/MD-Viewer-Pro/releases/download/1.5.3/MDViewerPro-1.5.3-win64-Setup.exe)
- [MDViewerPro-1.5.3-win64-portable.zip](https://github.com/oriyu90/MD-Viewer-Pro/releases/download/1.5.3/MDViewerPro-1.5.3-win64-portable.zip)

32-bit Windows is not supported. / 32-bit版Windowsには対応していません。
