# ADR-0002: 文書モデルを Rust が所有し、原文を正本とする

- 状態: 採用（2026-11-01）

## 文脈

旧アプリの最大の負債は MD 編集が contenteditable の innerHTML を
HTML→Markdown 逆変換して保存すること。可逆でなく、触るだけで文書が壊れる。

## 決定

- `mdv-core` が Document（source, generation, kind）を所有する
- レンダリングは常に source → HTML の一方向
- HTML から Markdown への逆変換は実装しない
- 編集はソース（textarea）で行い、プレビューは従属表示とする

## 結果

- 文書破壊が構造的に起きない
- テストが「source → HTML」のゴールデン比較で済む
- WYSIWYG の編集体験は失われる（v26 の既知の差分として明記）
