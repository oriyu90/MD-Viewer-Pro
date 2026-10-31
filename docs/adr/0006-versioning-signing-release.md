# ADR-0006: バージョニング・署名・リリース手順

- 状態: 採用（2026-11-01）

## 決定

- バージョンは `26.0.1`（Tauri 設定 / Cargo workspace / Info.plist を一致させる）
- macOS は common rules 8 に従い **ad-hoc 署名**（Developer ID 未取得）
- 配布は DMG。README / リリースノートに「ad-hoc・未公証」と初回起動手順を明記
- 公開（GitHub Release / 公開リポジトリ）はユーザー承認後に行う

## 結果

- Gatekeeper 警告は残る（既存アプリと同じ運用）
- 将来 Developer ID を取得したら `codesign` + `notarytool` に差し替える
