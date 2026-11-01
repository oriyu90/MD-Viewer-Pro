# QA レポート — MD Viewer Pro v26.2.0

- 実施日: 2026-11-01
- 対象: `MDViewerPro-26.1.0-macOS.dmg`（SHA-256 `22d69413daea312705c1e559834ebd70dc9be4fb213d35962b18a3bb692be842`）
- 環境: Apple M3 Ultra / macOS 26.4 / arm64

## 1. テスト構成

| 層 | 内容 | 件数 | 結果 |
|---|---|---|---|
| 単体（Rust） | 描画・サニタイズ・見出し ID・設定・I/O・テーマ | 27 | PASS |
| E2E（実 WKWebView） | `--selftest`：描画 / TOC / 数式 / Mermaid / ハイライト / 開く / 保存往復 | 1 シナリオ | PASS |
| UI プレビュー | 同一 HTML/CSS/JS をブラウザで表示（閲覧・編集・A4・検索） | 4 画面 | PASS（目視） |
| 署名 | `codesign --verify --deep --strict` | 1 | PASS（ad-hoc） |

### 単体テスト内訳

```
crates/mdv-core
  doc.rs       5  （BOM/UTF-16/文字化け/バイナリ拒否/原子的保存/種別判定）
  render.rs   10  （見出しID/生HTML/重複ID/GFM表/タスク/サニタイズ/改行/数式図/コード/フロントマター）
  settings.rs  5  （既定値/検証/旧JSON/破損退避/原子的保存）
  theme.rs     4  （パレット/混色/アクセント正規化/ライト補正）
```

## 2. E2E セルフテスト結果（実測）

`--selftest` はアプリを実際に起動し、WKWebView 上でレンダリングして DOM を検査、
`~/.mdviewer/selftest.json` に結果を書き出す。

```json
{
  "ok": true,
  "version": "26.0.1",
  "title": "Self Test",
  "headings": 1,
  "frontMatter": 2,
  "tables": 2,
  "taskItems": 2,
  "codeBlocks": 1,
  "highlighted": 2,
  "katex": 1,
  "mermaidSvg": 1,
  "tocItems": 1,
  "i18nKeys": 157,
  "lang": "ja",
  "openedHeadings": 2,
  "openedToc": 2,
  "openedSourceBytes": 84,
  "savedBytes": 89,
  "savedHasAppend": true,
  "pdfBytes": 33661
}
```

確認できたこと:

- Markdown → HTML → サニタイズ → WebView 表示の全経路
- 見出し ID と TOC の生成（2 見出しで 2 項目）
- KaTeX による数式 1 件、Mermaid の SVG 1 件（オフライン）
- highlight.js によるキーワード着色 2 件
- ファイルを開く → 保存 → 読み直しの往復（追記が保持される）
- 5 言語 160 キーの読み込み
- PDF 直接書き出し（A4 1 ページ、34KB）
- MD編集のブロック単位反映（段落変更が原文へ反映され、見出しは保持）

## 3. 性能（実測）

| 指標 | v1.5.3（Python/Qt） | v26.0.1 | 改善 |
|---|---|---|---|
| 起動〜UI ready | 数秒（Windows 実機 8.5 秒） | **1,229 ms** | 約 8 倍 |
| プロセスツリー RSS | 約 300 MB | **112 MB** | 約 2.7 倍軽量 |
| 実行ファイル | —（PyInstaller バンドル） | **8.3 MB** | — |
| .app | — | **8 MB** | — |
| DMG | 約 175 MB | **5.9 MB** | 約 30 倍小さい |

計測方法: `scripts/measure.sh`（起動経過msは JS の `ui_ready`、RSS は起動 1.5 秒後に
プロセスツリーを再帰合算。入力は 120 見出し・表・コード・数式を含む約 40KB の Markdown）。

## 4. セキュリティ検証

| 項目 | 結果 |
|---|---|
| `<script>` / `<iframe>` / `onclick` / `onerror` / `javascript:` / `data:` | ammonia により除去（レビュー時のプローブで確認、回帰テストあり） |
| CSP | `default-src 'self'; script-src 'self'`（自前アセットのみ） |
| 任意パス書き込み | ダイアログ/起動引数で選んだパスの allowlist のみ許可 |
| 外部 URL | http/https/mailto のみ `open_external` で許可 |

## 4.5 UI 検査（実 WKWebView スナップショット）

`--screenshot` モードで実表示を PNG 化し、以下を確認・修正しました。

- 閲覧（ダーク/ライト）、A4、編集、起動ダイアログ、詳細設定、PDF 設定、検索、プラグインテーマ、クリップ
- 修正: 行番号の潰れ、目次のコントラスト、設定の文字サイズ行、PDF 設定ダイアログの未表示、
  ライトテーマの紙面化、PDF のページ境界での見出し切断、ページ下部の黒抜け
- 詳細: `docs/UI_REVIEW.md` / 画像: `docs/ui/*.png`

## 5. 未実施・未確認

- GUI の目視（印刷ダイアログ、ドラッグ＆ドロップ、Finder 関連付け、単一インスタンス転送）
  - 実行環境のディスプレイがスリープし、画面キャプチャが黒画像になるため
  - 代替: 実 WKWebView のセルフテスト + ブラウザプレビュー
- Windows / Linux ビルド
- 多人数環境での同時起動（単一インスタンスの競合）
- 大きいファイル（数 MB 超）での描画時間

## 6. 再現手順

```bash
cargo test --workspace
./scripts/package_macos.sh
./scripts/measure.sh
"dist/MD Viewer Pro.app/Contents/MacOS/md-viewer-pro" --selftest
cat ~/.mdviewer/selftest.json
codesign --verify --deep --strict "dist/MD Viewer Pro.app"
```
