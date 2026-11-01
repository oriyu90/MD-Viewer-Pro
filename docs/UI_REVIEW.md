# UI 検査レポート — MD Viewer Pro v26.1.0

- 実施日: 2026-11-01
- 環境: Apple M3 Ultra / macOS 26.4 / 1280×900 ウィンドウ
- 手法: アプリに `--screenshot` モードを実装し、**実 WKWebView をオフスクリーン描画**して PNG 化
  - `screencapture` はディスプレイスリープ中に WebView レイヤーを取得できないため不採用
  - `WKWebView.takeSnapshot` により、画面の状態に依存せず実表示を取得
- 取得状態: 閲覧（ダーク）/ 閲覧（ライト）/ A4 / 編集 / 起動ダイアログ / 詳細設定 /
  PDF 設定 / 検索 / プラグインテーマ / クリップパネル
- 画像: `docs/ui/*.png`

## 検査結果と修正

| # | 画面 | 観測した問題 | 対応 |
|---|---|---|---|
| 1 | 編集 | 行番号が 1 行に潰れて「1234567」と表示 | `.gutter .ln { display:block; height:23.625px }` に行単位のブロック化。エディタと同一行高に統一 |
| 2 | 編集 | 行番号と本文の行がずれる | gutter の font-size / line-height をエディタと一致 |
| 3 | 閲覧 | 目次のレベル2が暗すぎて読めない | level2 を `--text` + opacity .88、level3 以下は .62 に調整。active は select 色 |
| 4 | 設定 | 文字サイズの値「16px」が行からはみ出す | `.range-wrap`（flex）でスライダーと値を一体化 |
| 5 | 設定 | チェックボックス行のラベルと配置が不揃い | `.field.inline { grid-template-columns: 1fr auto }` を適用 |
| 6 | PDF設定 | ダイアログが開かない（`fillPdfDialog is not defined`） | 関数定義の欠落を修正（ビルド時の置換ミス）。トーストでエラー可視化も追加 |
| 7 | クリップ | 項目が3件のときカードの高さ・削除ボタン位置は妥当 | 変更なし（確認のみ） |
| 8 | 検索 | ハイライト・1/31 表示・前後移動ボタンが動作 | 変更なし（確認のみ） |
| 9 | 起動 | ダイアログの背景にウェルカム文が重複して見える | 仕様として許容（ダイアログが前面） |
| 10 | ライト | 本文が灰色背景に直接乗り、紙面に見えない | `body[data-theme="light"] #doc` に白背景・枠・影を追加 |
| 11 | PDF | 1ページ目が途中で切れ、次ページ先頭が見出しの途中だった | ページ分割を「境界を越えるブロックを次ページへ送る」方式に変更。見出し単位で改ページ |
| 12 | PDF | ページ下部が黒く抜けた | `#app/#workspace/#preview-pane/.doc-scroll` の `overflow:hidden` を PDF モードで解除し、`body` 背景をページ色に統一 |

## 残っている軽微な事項

- ウィンドウタイトルバーの文書名更新は、`setTitle` の反映タイミングに依存（WebView 内表示には影響なし）
- 起動ダイアログの背景ウェルカム文は意図的な二重表示（ダイアログを閉じた直後の状態）
- クリップの並びは「新しい順 + 重複排除」（旧版は末尾追加）。UX 上は現行を採用

## 再現方法

```bash
cargo build -p md-viewer-pro
./target/debug/md-viewer-pro tests/fixtures/measure.md --screenshot /tmp/ui.png --mode view --theme dark
./target/debug/md-viewer-pro tests/fixtures/measure.md --screenshot /tmp/dlg.png --dialog settings
```

`--dialog` は `settings` / `margin` / `pdf` / `clip` / `search` に対応。
