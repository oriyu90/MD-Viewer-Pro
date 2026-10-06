# MD Viewer Pro v1.4.7 — Windows版 (x64 portable)

## 日本語

- Windows 10/11 64-bit用ポータブル版を追加しました。ZIPを展開して
  `MDViewerPro.exe` を開くだけで使えます（インストール不要）。
- アプリ本体はmacOS版 v1.4.7 と同じソースです
  （閲覧・MD編集・TXT編集・LaTeX・Mermaid・YAML・PDF/HTML書き出し）。
- 標準のアプリに設定できます。関連付けから開いた文書は起動中のアプリで
  開かれます（二重起動防止）。`windows\register_assoc.ps1` で現在の
  ユーザーの関連付けを登録できます（管理者権限不要）。
- 配布物を軽量化しました（デバッグ用リソース・未使用Qtモジュール・
  未使用言語の翻訳を除外）。
- Windowsでは設定・テーマ・追加フォントを `%APPDATA%\MDViewerPro` に保存します
  （旧 `~/.mdviewer` があれば初回に引き継ぎ）。既定フォントは Yu Gothic UI、
  保存時の改行はLFに統一しています。
- Windowsでのみ必要な調整として、macOS固有設定の無効化と
  最小ウィンドウ幅でのツールバーボタンのはみ出し修正を含みます。
- 32-bit版Windowsには対応していません
  （Qt6/PySide6に32-bit用配布物がないため）。
  Windows 11に32-bit版は存在しません。

**Download / ダウンロード**:
- Windows (x64 portable): `MDViewerPro-1.4.7-win64-portable.zip`
- Mac (Apple Silicon): `MDViewerPro-1.4.7-Installer.dmg`

署名なしポータブルのため、初回起動時にSmartScreen
（「WindowsによってPCが保護されました」）が出ることがあります。
アプリ自体は壊れていません。「詳細情報」→「実行」で起動してください。
ZIP内の `FIRST_LAUNCH_WINDOWS.txt` もご覧ください。

## English

- Added a portable build for Windows 10/11 64-bit. Extract the ZIP and
  open `MDViewerPro.exe` (no installation required).
- The app is the same v1.4.7 source as the macOS build
  (View / MD Edit / TXT Edit / LaTeX / Mermaid / YAML / PDF & HTML export).
- It can be set as the default app for .md files. Documents opened from an
  association reuse the running app (single-instance). `windows\register_assoc.ps1`
  registers the association for the current user (no admin rights needed).
- The package is slimmed down (debug resources, unused Qt modules and unused
  language translations excluded).
- On Windows, settings, themes and extra fonts live under `%APPDATA%\MDViewerPro`
  (migrated from `~/.mdviewer` on first run). The default font is Yu Gothic UI
  and saved files use LF line endings.
- 32-bit Windows is not supported (Qt6/PySide6 ships no 32-bit binaries).
  There is no 32-bit edition of Windows 11.

The Windows build is unsigned, so SmartScreen
("Windows protected your PC") may appear on first launch.
The app itself is not damaged. Choose "More info" → "Run anyway".
See `FIRST_LAUNCH_WINDOWS.txt` inside the ZIP.

**Tests**: pure-function 506, Qt widget 410, all passing on Windows 10 64-bit
(offscreen). WebEngine integration suite runs macOS-verified (82 cases);
Windows portable verified by build + launch smoke test.
