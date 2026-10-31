# ADR-0003: サニタイズは Rust、IPC は capability で最小化

- 状態: 採用（2026-11-01）

## 文脈

旧アプリは QWebChannel を全モードで公開し、Python 側の独自サニタイザに依存していた。
未信頼 Markdown とアプリ権限の境界が薄い。

## 決定

- HTML サニタイズは `ammonia`（allowlist）で Rust 側 1 箇所に集約
- WebView へ渡す前に必ずサニタイズ済み HTML にする
- JS から呼べるコマンドは capabilities/default.json の `core:default` と
  明示的に登録したコマンドのみ。WebChannel 相当の汎用ブリッジは作らない
- CSP: `default-src 'self'; script-src 'self'`（自前アセットのみ）
- 外部 URL は http/https/mailto のみ `open_external` で許可

## 結果

- script / iframe / on* / javascript: は表示前に除去
- 将来ブリッジを増やす場合も capability とコマンド単位でレビューできる
