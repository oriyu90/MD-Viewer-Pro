# ADR-0001: Tauri 2 + システム WebView を採用する

- 状態: 採用（2026-11-01）
- 決定者: メイン（設計）

## 文脈

旧アプリは PySide6 + QtWebEngine。配布物 119–175MB、常駐 300MB、コールド起動 8.5 秒。
Rust 化にあたり、描画エンジンを (a) システム WebView、(b) 完全ネイティブ、
(c) Rust 製 HTML レンダラ（Blitz/Servo）から選ぶ必要があった。

## 決定

Tauri 2（2.12 系）を使い、描画は OS の WebView（macOS: WKWebView）に任せる。
アプリロジック・文書処理・I/O・設定・輸出はすべて Rust。

## 理由

- Markdown の見た目と A4 印刷は CSS 前提であり、WebView が最も忠実度が高い
- Mermaid / KaTeX という JS 資産をそのまま使える（オフライン同梱）
- 配布物が数 MB 台になり、Qt 同梱が不要
- capability による権限分離が旧 WebChannel より明確

## 結果

- 長所: 小ささ、忠実度、実装量、macOS の WKWebView 最適化
- 短所: WebView プロセスのメモリ（概算 100–150MB）は残る。Linux は WebKitGTK 依存
- 監視: 描画差（WKWebView 以外）は将来の Windows/Linux 対応時に検証する

## 代替案

- Electron: さらに重い。却下
- Iced/Slint: 表・数式・図・印刷を自前になり工数 3–4 倍。Lite 版の将来候補
- Blitz/Dioxus Native: 0.2 系で CSS 網羅・実績不足。将来のレンダラ差し替え候補
