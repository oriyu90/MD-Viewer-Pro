# ADR-0004: 数式・図・ハイライトは WebView 側アセットで描画する

- 状態: 採用（2026-11-01）

## 文脈

KaTeX / Mermaid は JS 実装が事実上の標準。Rust 実装（katex-rs 0.3、
mermaid-rs-renderer 0.3）は若く、再現度が未検証。

## 決定

- comrak で HTML を生成し、コードフェンスは `language-*` クラスを保持
- 表示後に WebView 内で以下を実行する（すべて同梱・オフライン）
  - highlight.js: コードハイライト
  - KaTeX auto-render: `$…$` / `$$…$$` / `\(…\)`
  - mermaid: ` ```mermaid ` を SVG に変換（securityLevel: strict）
- Rust は「プレースホルダを残す」責務まで。DOM 操作はしない

## 結果

- 忠実度と実装速度を確保。Rust 側はテスト可能な純粋関数のまま
- JS バンドル（約 5MB）を同梱する。旧アプリの Mermaid 3.5MB と同水準
- 将来 Rust 実装へ差し替える場合も、HTML の契約（class 名）を保てば移行可能
