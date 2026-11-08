# QA レポート — MD Viewer Pro β2.0（beta.2.0）

- 実施日: 2026-11-01
- 対象: `MDViewerPro-26.1.0-macOS.dmg`（SHA-256 `932238ab79b4f1bcc2f1ff45029c3ac6b348c6d41babb6370db04869969f9a2b`）
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

---

# QA レポート — MD Viewer Pro β4.0（26.4.0-beta.4.0）

- 実施日: 2026-11-08
- 環境: Apple M3 Ultra / macOS 26.4 / arm64 / Rust 1.99.1
- 対象の変更: 標準アプリ対応（要求 1）/ TXT 保存の維持（要求 2）/ ツールバー縦幅（要求 3）

## 1. テスト構成

| 層 | 内容 | 件数 | 結果 |
|---|---|---|---|
| 単体（Rust） | `cargo test --workspace`（doc/settings/render/theme + state の転送プロトコル） | 34 | PASS |
| 静的解析 | `cargo clippy --workspace --all-targets -- -D warnings` | — | 警告 0 |
| E2E（実 WKWebView） | `--selftest`（既存シナリオ + β4.0 の回帰検査） | 1 シナリオ | PASS |
| Info.plist | `plutil -lint` + 書類型の自動検証（`package_macos.sh`） | 1 | PASS |
| LaunchServices | `lsregister -dump` で claim を実測 | 3 書類型 + 1 UTI | PASS |
| 実機起動 | `open -a` で `.txt` / `.md` を開く、二重起動の転送 | 3 | PASS（目視） |

### 追加した単体テスト

```
mdv-core/doc.rs
  kind_identifiers_are_stable          （md/txt/yaml の識別子と prefers_plain_text）
  txt_extension_is_plain_text          （.txt / .TXT / 拡張子なし）
  kind_for_save_keeps_extension_...    （.txt へ保存しても Markdown へ化けない）
md-viewer-pro/state.rs
  instance_message_roundtrip_with_path （新形式 JSON）
  instance_message_activate_only       （{} / 空文字）
  legacy_raw_path_is_accepted          （旧形式の生パス）
  broken_json_does_not_panic           （壊れたメッセージで落ちない）
```

## 2. 要求 1 — 標準アプリとして開ける

### 原因（実測で特定）

1. Info.plist の書類型が 1 件だけで、`UTImportedTypeDeclarations` が無かった
   （旧 Python 版にあった宣言が Rust 版で失われていた）。
2. **`RunEvent::Opened` が起動直後（約 0ms）に発火し、フロントエンドの購読開始
   （`ui_ready` 実測 460ms）より前に emit していたため、イベントが捨てられていた。**
   `~/.mdviewer/opened.log` に時刻を記録して確認（Opened 0ms / ready 460ms）。
3. Dock 再オープン（`RunEvent::Reopen`）に未対応。
4. 起動引数の解析が「最初の非 `-` 引数」で、複数ファイルや `--flag value` に弱かった。

### 修正

- Info.plist を 3 書類型に分割（Markdown = Owner/Editor、Plain Text = Alternate/Editor、
  YAML = Alternate/Viewer）し、`UTImportedTypeDeclarations` で
  `net.daringfireball.markdown` を宣言。`CFBundleLocalizations`（ja/en）も追加。
- 起動直後のパスを `AppState::pending_paths` に溜め、`ui_ready` で流す方式に変更
  （転送・起動引数も同じ経路）。上限 64 件でメモリを保護。
- `RunEvent::Reopen` を追加し、Dock 再クリックでウィンドウを前面化。
- 転送メッセージを JSON 化（旧形式の生パスも受理）。読み取りは 64KiB 上限。
- 起動引数の解析を `startup_paths()` に集約（値付きフラグの値を誤認しない）。

### 実測結果

```
LS claims（dist/MD Viewer Pro.app を lsregister -f で登録後）
  Markdown Document   rank=Owner      roles=Editor   bindings=net.daringfireball.markdown, public.plain-text
  Plain Text Document rank=Alternate  roles=Editor   bindings=public.plain-text
  YAML Document       rank=Alternate  roles=Viewer   bindings=public.yaml, public.plain-text
  UTImportedTypeDeclaration: net.daringfireball.markdown（.md/.markdown, text/markdown）

open -a "MD Viewer Pro" /tmp/mdvp-open-test.txt
  → 起動し、タイトル "mdvp-open-test.txt — MD Viewer Pro"、本文表示、.txt 案内バー表示
起動中に open -a "MD Viewer Pro" /tmp/mdvp-open-test.md
  → プロセス数 1 のまま既存ウィンドウで .md を表示、.txt 案内バーが消える
```

## 3. 要求 2 — TXT の保存形式を維持

### 実装

- Rust の `DocKind::id()` を UI に返し、`.txt` を Markdown 文書として扱わない。
- 書式ツールバーの使用を `state.formatUsed` で記録（MD編集・TXT編集の両方）。
- `.txt` 文書で書式ツールバーを使った場合のみ、保存前に
  「.md で保存 / .txt のまま保存 / キャンセル」を確認するダイアログを表示。
- 書式ツールバーを使っていなければ、保存先・拡張子を一切変えない。
- 保存ダイアログの推奨名・フィルタを書類種別に合わせる（`.txt` なら Text 先頭）。
- `.txt` を開いている間は、保存形式の案内バーを表示（要求の可視化）。

### 実測結果（E2E）

```
txtKind=txt / txtFormatUsed=false / txtSaved=true
savedExt=txt / savedKind=txt / savedHasAppend=true
txtStillPlainAfterToolbar=true（書式ツールバー使用後も .txt 文書のまま）
txtHintVisible=true
```

## 4. 要求 3 — ツールバー縦幅

### 実装

- 基準値 = 従来の段階値 × 0.9（64.8 / 52.2 / 41.4 / 36.0px、書式バーも同率）。
- 縦幅係数 = `clamp(0.80 + 0.20 × (h − 360) / 540, 0.80, 1.00)`（単調増加・連続）。
- 実効高さは CSS の `calc(var(--tb-base) * var(--tb-scale))`。
  JS は `--tb-scale` だけを 180ms かけて ease-out で補間する。
- **CSS の `height` transition は使わない**: 実測でプログラム的リサイズ時に
  遷移が止まり、高さが更新されない事象を確認したため。
- **`requestAnimationFrame` も使わない**: この WebView では発火しない場合があり、
  リサイズ処理が二度と走らなくなる事象を確認したため `setTimeout` で間引く。
- リサイズ検知は `resize` イベント + `ResizeObserver` + 250ms ポーリングの三重化。

### 実測結果（E2E、実ウィンドウを 6 通りにリサイズして計測）

| 要求サイズ | 基準値 | 係数 | 期待値 | 実測値 | 判定 |
|---|---|---|---|---|---|
| 1280×900 | 64.8 | 0.988 | 64.0 | 64.0 | OK |
| 1280×700 | 64.8 | 0.916 | 59.3 | 59.3 | OK |
| 1280×500 | 64.8 | 0.841 | 54.5 | 54.5 | OK |
| 1000×900 | 52.2 | 0.987 | 51.5 | 51.5 | OK |
| 800×900 | 52.2 | 0.988 | 51.6 | 51.6 | OK |
| 600×900 | 36.0 | 0.988 | 35.6 | 35.6 | OK |

## 5. 日本語 / 英語の完全対応

- i18n キーを 160 → 186 に増やし、5 言語すべてでキー集合が一致。
- `index.html` の直書き文言（PDF 余白ラベル、設定の「テキスト」、検索 placeholder、
  書式ボタンの title、ドロップ案内など）を `data-i18n*` 化。
- JS 内の直書き（表の見出し・セル、リンク既定文字）も i18n 化。
- 実測: `i18nSameKeys=true` / `i18nEnJapaneseKeys=[]` / `i18nUiJapaneseInEn=false`。
- 実画面: 日本語・英語それぞれでツールバーと確認ダイアログを撮影して確認。

## 6. 回帰（既存機能）

E2E の既存シナリオはすべて PASS。

```
headings=1 frontMatter=2 tables=2 taskItems=2 codeBlocks=1 highlighted=2
katex=1 mermaidSvg=1 tocItems=1 openedToc=2
mdEditChanged=true mdEditKeptHeading=true pdfBytes=27250 savedHasAppend=true
```

## 7. 既知の制約

- `~/.mdviewer/selftest.json` の `tbMatrix` は `--selftest` 専用コマンド
  `selftest_resize` を使う（通常起動では ACL によりウィンドウ操作 API は無効）。
- 標準アプリの既定登録はユーザー操作（「このアプリケーションで開く」→
  「常にこのアプリで開く」）で確定する。`LSHandlerRank: Owner` は候補として
  最上位に出すための宣言であり、他アプリの既定を強制変更はしない。
