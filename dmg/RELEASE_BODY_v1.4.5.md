# MD Viewer Pro v1.4.5

入力した改行とコードの中身が、保存・再読込の往復で失われる問題を直したリリースです。

## 日本語

### 修正

- **コードブロック内の空行が保存のたびに詰まる問題**: コードブロックの中に入れた連続した空行が、保存 → 開き直しを繰り返すたびに 1 行に詰まっていました。コードの中身（フェンス内・インラインコード）は空行整形の対象外とし、入力したとおりに保存されるようにしました。
- **改行設定が「オフ」のとき、明示的な改行が消える問題**: 「改行をそのまま改行として表示する」をオフにしていると、行末スペース 2 個で入れた改行が MD編集の保存で失われていました。設定に合わせて復元するようにしました。
- **保存中のエラーで既存ファイルが失われる恐れ**: 一時ファイルへ書いたうえで置き換える方式（原子的置換）に変更しました。書込みに失敗したときは既存ファイルと「未保存」状態を保ちます。
- **読み取れないファイルを開くと内容が空になる問題**: 読み取りに失敗したときは、いま開いている文書をそのまま維持します。
- **MD編集の取り込みがタイムアウトしたとき**: 失敗時に現在の内容を維持して保存するようにしました。

## English

### Fixes

- **Blank lines inside code blocks collapsed on every save**: consecutive blank lines inside a fenced code block were collapsed each time the file went through MD Edit and a save. Code content is now exempt from paragraph normalisation and is preserved exactly as entered.
- **Explicit line breaks lost when hard breaks are off**: a line break written as two trailing spaces was dropped when saving from MD Edit. The converter now restores the correct form for the current setting.
- **A failed save could destroy the existing file**: saving now writes to a temporary file in the same folder and replaces the target atomically; on failure the old file and the unsaved state are kept.
- **Opening an unreadable file replaced the current document with an empty one**: the current document is now preserved when a read fails.
- **MD Edit capture timeout**: a timed-out capture no longer risks clobbering the current content.

---

**ダウンロード / Download**: [MDViewerPro-1.4.5-Installer.dmg](https://github.com/oriyu90/MD-Viewer-Pro/releases/download/1.4.5/MDViewerPro-1.4.5-Installer.dmg)

- macOS 10.13 以降 / Apple Silicon & Intel
- 未署名・ad-hoc署名ビルドです。初回起動時に「システム設定 → プライバシーとセキュリティ」からの許可が必要になる場合があります。
  (Unsigned / ad-hoc signed build. You may need to allow it in System Settings → Privacy & Security on first launch.)
