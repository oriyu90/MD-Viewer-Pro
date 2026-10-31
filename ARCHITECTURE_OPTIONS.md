# MD Viewer Pro — Rust リライト構成案（調査・分析レポート）

- 作成日: 2026-11-01 (JST)
- 対象: `oriyu90/MD-Viewer-Pro` v1.5.3（Python 3 / PySide6 6.10.3 / QtWebEngine / PyInstaller）
- 目的: 内部をほぼ Rust に置き換え、軽量・安定・クロスプラットフォームなデスクトップアプリにする構成を、複数案の比較として提示する
- 前提: 本レポートの「事実」は一次情報（公式ドキュメント・crates.io・リポジトリ実物）に基づく。数値のうち「概算」と付いたものは実測ではなく設計からの見積もり。実測は Phase 0 で行う

---

## 0. 30秒でわかる結論

1. **「内部をほぼ Rust」と「Markdown の見た目・PDF の忠実度」は両立できる。** ただし描画エンジンをどうするかで 3 系統に分かれる。現実的な本命は **Tauri 2 + Rust コア + システム WebView**（案A）。アプリロジックの 85〜90% が Rust になり、配布物は 119MB → 概算 10〜20MB、起動 8.5 秒 → 概算 1 秒前後、常駐 300MB → 概算 120〜200MB になる見込み
2. **完全ネイティブ（Iced / Slint）にすると RAM は 50〜90MB まで落ちるが、Markdown の表・数式・Mermaid・A4 印刷・PDF を自前で組む必要があり、工数は 3〜4 倍。**「軽さ最優先の Lite 版」としてなら有力
3. **最重要の設計判断はレンダラではなく「文書モデルを Rust が持つこと」。** 現行の最大の負債は MD 編集の HTML→Markdown 逆変換。ここを捨て、`コア（AST）→ 複数レンダラ` の二層にすれば、WebView 版から将来のネイティブ版・Blitz 版へ乗り換えられる
4. **PDF 出力だけは要注意。** Tauri の `Webview::print()` は macOS 限定、`window.print()` は全 OS だが印刷ダイアログ前提。サイレントな PDF 書き出しは OS 別の自前実装（WebView2 `PrintToPdf` / WKWebView `createPDF` / WebKitGTK `PrintOperation`）が必要
5. **推奨: 案A（Tauri 2）で出荷し、コアを案D（レンダラ差し替え可能）として設計。** Linux を v1.0 から必須にするなら、WebKitGTK 依存を許容できるかが最大の分岐点

---

## 1. 現状分析（リライトで何を解くのか）

### 1.1 実測できている現状値（社内記録より）

| 項目 | 現行 v1.5.3 | 出典 |
|---|---|---|
| 配布物（macOS DMG） | 約 175MB | `MD-Viewer-Pro.md`（2026-10-14） |
| 配布物（Windows Setup.exe） | 119,351,777 bytes | 同上 |
| 配布物（Windows portable ZIP） | 173,746,553 bytes | 同上 |
| Windows コールド起動 | 8.5 秒 | 同上（v1.4.7 rev2 実測） |
| Windows 常駐メモリ | 約 300MB | 同上 |
| 本体コード | `main.py` 7,915 行 / 365KB 単一ファイル | GitHub 実物（2026-11-01 取得） |
| テスト | 998 件（純粋関数 506 / Qt 410 / WebEngine 統合 82） | 同上 |

### 1.2 構造的な負債（既存の設計リスク分析レポート 2026-06-30 より）

Rust 化の価値は「言語を変えること」ではなく、**この 4 系統を構造で解くこと**にある。

1. **MD 編集が HTML→Markdown の逆変換に依存**（`_HTML2MD`）。可逆でなく、触るだけで文書が変わる。→ Rust では「原文が常に正本」の設計にし、逆変換自体を廃止する
2. **WebChannel が全モードで開いている**。未信頼 Markdown とアプリ権限の境界が薄い。→ Tauri の capability/command 許可制に置き換え、ブリッジを 5〜8 コマンドに絞る
3. **単一ファイルに UI・HTML・CSS・JS・変換器が混在**。→ Cargo workspace に分割し、コアを GUI 非依存にする
4. **ビルド・配布が手作業スクリプト**（`build_dmg.sh` / `build_win.ps1` / PyInstaller spec）。→ `tauri build` + GitHub Actions マトリクスに統一

### 1.3 機能の技術要件への分解

Markdown ビューアの「軽さ」を決めるのは UI フレームワークではなく、**この 5 つの従属物**である。

| 機能 | 必要な技術 | ネイティブ GUI での難易度 |
|---|---|---|
| GFM（表・脚注・タスクリスト・ frontmatter） | CommonMark パーサ | 低（comrak で完結） |
| コードハイライト | syntect / two-face | 低 |
| LaTeX 数式 | KaTeX 相当の組版 | **高**（JS 前提 / Rust 実装は若い） |
| Mermaid ダイアグラム | Mermaid.js（JS） | **非常に高**（純 Rust 実装は発展途上） |
| A4 印刷・PDF 書き出し | CSS paged media / 印刷 API | **非常に高**（自前組版になる） |
| 日本語・中国語の禁則・行送り | テキストシェーピング | 中（cosmic-text 等） |
| アクセシビリティ（読み上げ） | OS の AX API | 中〜高（ツールキット依存） |

**この表が示すのは「数式・Mermaid・PDF の 3 つが WebView を手放せなくしている」ということ。** 逆に言えば、この 3 つを Rust で代替できるなら完全ネイティブも成立する。

---

## 2. 2026-10-31 時点の技術選択肢（一次情報）

### 2.1 GUI シェル

| 選択肢 | 最新版（crates.io） | 描画 | 特徴 | 判定 |
|---|---|---|---|---|
| **Tauri 2** | 2.12.5（2026-10-21） / wry 0.57.1 | OS の WebView | バイナリ極小、capability による権限分離、mobile 対応、updater/単一インスタンス等プラグイン充実 | **本命** |
| Dioxus 0.7 | 0.7.10（2026-10-16） | 既定は WebView。`dioxus-native` は WGPU + Blitz | Rust だけで UI 記述。ホットパッチ。Blitz は「very young / WIP / 性能未追求」と公式明記 | 次点（案B/D） |
| Iced 0.14 | 0.14.0（2025-12-07） | wgpu ネイティブ | Elm 型、IME 対応、テスト基盤、リアクティブ描画。画面読み上げは限定的 | ネイティブ派の本命 |
| egui 0.37 | 0.37.0（2026-10-15） | wgpu/glow | 即時モードで実装が速い。長文ドキュメントのレイアウト・選択・印刷には不向き | 小物向き |
| Slint 1.18 | 1.18.1（2026-09-21） | ネイティブ | 宣言的 UI、組込強い。**ライセンスが GPLv3 か有償**（MIT の現行アプリとは非互換） | ライセンス次第で除外 |
| gpui | 0.2.2（2026-10-30） | Metal/GPU | Zed 製。API 不安定・ドキュメント薄・エコシステム小 | 現時点では非推奨 |
| Servo / Blitz | servo 0.7.0 / blitz 0.2.1 | Rust 製 HTML/CSS | 「Rust だけで HTML を描く」将来解。組込 API・CSS 対応がまだ実用域でない | 監視対象 |

**Tauri の実務要件（公式）**
- macOS 10.15 以降、Windows 7 以降（ただし Evergreen WebView2 の実運用は Windows 10 1803+ / 11）、Linux は `libwebkit2gtk-4.1`
- Linux のビルド基準は **Ubuntu 22.04 / Debian 12**。AppImage は依存同梱で 2〜6MB → **70MB+** になる
- 署名: macOS は Apple Developer（$99/年）+ notarization、Windows は NSIS か WiX MSI（MSI は Windows 上でのみビルド可）
- WebDriver: `tauri-driver` は Windows/Linux のみ。**macOS は WebdriverIO の `@wdio/tauri-service`（embedded driver）** で対応

出典: <https://v2.tauri.app/start/prerequisites/>、<https://v2.tauri.app/distribute/appimage/>、<https://v2.tauri.app/develop/tests/webdriver/>、<https://v2.tauri.app/distribute/windows-installer/>（取得 2026-11-01）

### 2.2 Markdown / 数式 / 図

| 役割 | クレート | 版 | 備考 |
|---|---|---|---|
| Markdown | **comrak** | 0.59.0（2026-10-26） | GFM 4 拡張 + frontmatter + math-dollars/latex + syntect アダプタ。乗り換え先として最有力 |
| Markdown（代替） | pulldown-cmark | 0.13.6（2026-10-30） | 高速・低依存。拡張は自前 |
| ハイライト | syntect 5.3.0 / two-face 0.5.2 | — | two-face は bat のテーマ資産を利用 |
| サニタイズ | **ammonia 4.2.4** | 2026-10-17 | allowlist 型。現行 `_HTMLSanitizer` を置換 |
| 数式 | KaTeX（JS・現行踏襲） | — | 実績最優先ならこれ |
| 数式（Rust） | katex-rs 0.3.0 / tex2math 2.4.1 | 2026-09 / 2026-08 | 若い。網羅性・フォント Metrics は要検証 |
| Mermaid（JS） | mermaid.min.js | 同梱 3.57MB | 現行資産。オフライン動作実績あり |
| Mermaid（Rust） | mermaid-rs-renderer 0.3.1 / flowmaid 0.33.0 | 2026-07 / 2026-10 | 「23 種対応」等は自己申告。**未検証** |
| エディタ | ropey 1.6.1 / CodeMirror 6 | — | 大文書は rope、UI は CM6 が現実的 |
| PDF | typst 0.15.1 / typst-as-lib 0.17.0 / printpdf 0.12.8 | — | GUI なしの高品質 PDF が必要な場合の保険 |

### 2.3 配布・CI

- `tauri-action`（GitHub Actions）で macOS（arm64 / x86_64 / universal）、Windows（NSIS/MSI）、Linux（deb/rpm/AppImage）を一括生成
- macOS universal は `--target universal-apple-darwin`
- 自動更新は `tauri-plugin-updater`（署名付き manifest）
- 代替: `cargo-dist 0.32.0`（CLI ツール向け。GUI なら Tauri bundler が楽）

---

## 3. 構成案（4 案）

### 案A: Tauri 2 + Rust コア + 薄い Web フロント（推奨）

```
┌──────────────────────────────────────────────┐
│ ネイティブウィンドウ（tao / メニュー / D&D）   │
│ ┌──────────────────────────────────────────┐ │
│ │ システム WebView（WKWebView/WebView2/     │ │
│ │ WebKitGTK）  ← HTML/CSS を表示するだけ     │ │
│ │  ・TOC / スクロール同期 / コピー           │ │
│ └──────────────────────────────────────────┘ │
│        ▲ IPC（5〜8 コマンドのみ）             │
│ ┌──────┴───────────────────────────────────┐ │
│ │ Rust: mdv-core                            │ │
│ │  ファイルIO / 文字コード / comrak 解析     │ │
│ │  HTML 生成 / ammonia / 設定 / 検索 / 輸出  │ │
│ └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

- **Rust 比率**: 85〜90%（UI は HTML/CSS + 最小 JS 500〜1,500 行）
- **強み**: 既存の見た目・A4 印刷 CSS・Mermaid/KaTeX をほぼそのまま資産化できる。実装量が最も少ない
- **弱み**: WebView プロセス分の RAM（概算 80〜150MB）は残る。OS ごとにエンジンが違うため**描画差の検証コスト**が発生。Linux は WebKitGTK 依存
- **向くケース**: 見た目と PDF の忠実度を落とせない本線

### 案B: Tauri 2 + Leptos/Dioxus（WASM）で UI まで Rust

- **Rust 比率**: 95%+。UI ロジックも Rust（WASM にコンパイル）
- **強み**: 「内部ほぼ Rust」を最も強く満たす。型安全な UI
- **弱み**: WASM バンドル +1〜3MB、初回描画が遅れる、ビルドチェーンが複雑（wasm-bindgen / trunk）、WebView の RAM は案Aと同じ
- **判断**: 案Aで十分な場面が多く、**無理に選ぶ利点は薄い**。UI が複雑化した場合の移行先

### 案C: 完全ネイティブ（Iced 0.14 もしくは Slint）

```
winit + wgpu → Iced ウィジェット
  文書ビューは自前（cosmic-text で整形、表は Taffy でレイアウト）
  数式: katex-rs → SVG、Mermaid: mermaid-rs-renderer → SVG
  PDF: typst で別レイアウト生成
```

- **Rust 比率**: 100%。シングルバイナリ 15〜30MB、RAM 50〜90MB、起動 0.2〜0.5 秒（概算）
- **強み**: 真のネイティブ。WebView 更新に振り回されない。Linux でも依存が少ない
- **弱み**: 表・脚注・画像・選択・検索・印刷・数式・図を全部自前。**工数 6〜10 人月**。Rust 製数式/図エンジンは若く、KaTeX/Mermaid.js の再現度は保証できない。Slint は GPLv3/有償で MIT と衝突
- **向くケース**: 「軽さ」が最優先で、機能を 7 割に絞れる Lite 版

### 案D: 二層コア（案Aを土台に、レンダラを交換可能にする）★推奨の設計原則

```
mdv-core（AST・設定・検索・輸出）
   ├─ render-html   → 案A の WebView（今日）
   ├─ render-blitz  → WGPU ネイティブ（Blitz が成熟したら）
   └─ render-typst  → PDF / CLI（印刷専用）
```

- 「どの描画エンジンを使うか」を**アプリの外側の決定**に追い出す。今日は WebView、2 年後に Blitz、という乗り換えが可能
- コアは GUI 非依存なので、CLI（`mdv render x.md -o x.html`）とテストが同じ経路になる
- **推奨は「案A + 案D の構造」**。案C はこのコアの上に載る別フロントとして後から追加できる

### 却下案

| 案 | 理由 |
|---|---|
| Qt を維持してロジックだけ Rust（cxx-qt 0.10） | QtWebEngine の 150MB 超と RAM 300MB が残り、目標を達成できない。移行コストだけ高い |
| Electron + Rust（napi-rs） | 現行より重くなる。論外 |
| Wails（Go）/ Flutter（Dart） | 「内部をほぼ Rust」に反する |

---

## 4. 比較表（概算・Phase 0 で実測に置換する）

| 指標 | 現行 Python+Qt | 案A Tauri+WebView | 案B Tauri+WASM | 案C ネイティブ | 案D A+差し替え |
|---|---|---|---|---|---|
| 配布物サイズ | 119〜175MB | 10〜20MB | 12〜22MB | 15〜30MB | 10〜20MB |
| 常駐 RAM | 約 300MB | 120〜200MB | 130〜210MB | **50〜90MB** | 120〜200MB |
| コールド起動 | 8.5 秒 | 0.6〜1.5 秒 | 0.8〜1.8 秒 | **0.2〜0.5 秒** | 0.6〜1.5 秒 |
| Rust 比率 | 0% | 85〜90% | 95%+ | 100% | 85〜90% |
| 表示忠実度 | 高 | **高** | 高 | 中（自前実装次第） | 高 |
| PDF 忠実度 | 高 | 高（OS 別実装） | 高 | 中（typst 再構築） | 高 |
| OS 差リスク | 中 | 中〜高（Linux） | 中〜高 | **低** | 中〜高 |
| 実装工数 | — | 2〜3 人月 | 3〜4 人月 | **6〜10 人月** | 2〜3 人月 |
| 将来の乗り換え | 不可 | 可（D 構造なら） | 可 | — | **可** |

> 数値は「概算」。WebView の RAM はエンジンとページ内容に強く依存するため、Phase 0 で同一文書（1MB の日本語 MD + 表 + 画像 + Mermaid）を使った実測を行う。

---

## 5. 推奨構成の詳細設計（案A + D）

### 5.1 リポジトリ構成

```
md-viewer-pro/
├─ Cargo.toml                 # workspace
├─ crates/
│  ├─ mdv-core/               # 文書モデル・設定・検索・パス解決（GUI 非依存）
│  │   ├─ doc.rs              # Document, Generation, dirty 管理
│  │   ├─ parse.rs            # comrak → AST / frontmatter / outline
│  │   ├─ settings.rs         # serde + 原子的保存 + schema migration
│  │   ├─ search.rs           # インクリメンタル検索（memchr/aho-corasick）
│  │   └─ theme.rs            # JSON テーマ（schemars で検証）
│  ├─ mdv-render/             # HTML 生成・CSS・sanitize（ammonia）
│  ├─ mdv-export/             # HTML / PDF / 画像埋め込み
│  ├─ mdv-platform/           # ダイアログ・関連付け・単一インスタンス・フォント・クリップボード
│  └─ mdv-cli/                # ヘッドレス描画（テスト・CI・将来のバッチ）
├─ apps/desktop/              # Tauri アプリ（src-tauri）
│  ├─ src/commands.rs         # 公開コマンドは 5〜8 個だけ
│  └─ capabilities/*.json     # 許可制
├─ ui/                        # HTML/CSS + 最小 TS（または Leptos）
├─ assets/                    # themes / katex / mermaid / i18n / サンプル
└─ tests/                     # golden corpus（現行 998 件の移植先）
```

### 5.2 データフロー（原文が常に正本）

```
open(path)
  → サイズ上限・バイナリ判定・文字コード判定（encoding_rs + chardetng）
  → Document { source: String, generation: u64 }
  → comrak で AST 化（フロントマター・見出し・数式・Mermaid を抽出）
  → render_html(ast, theme, layout) → String
  → webview へ差し替え（差分描画 or ブロック単位キャッシュ）

編集
  → CodeMirror 6（ソース編集）→ 150ms デバウンス
  → 変更行を含むブロックだけ再描画（hash 比較）
  → 保存は tempfile + fsync + rename（原子的）
```

**MD 編集の仕様変更（重要）**: 現行の contenteditable + HTML→MD 逆変換は**移植しない**。「ソース編集 + 右プレビュー（TXT 編集の UX を MD にも広げる）」に統一する。これで文書破壊のリスクが構造的に消える。WYSIWYG 風の編集が必須なら、ブロック単位の編集（編集対象ブロックだけソースを見せる）にする。

### 5.3 セキュリティ設計（現行の負債を構造で解く）

| 現行 | 新構成 |
|---|---|
| WebChannel を全モードで公開 | Tauri capability で**ウィンドウ単位**に許可。公開コマンドは `open_file` / `save_file` / `export_*` / `clipboard_write` / `open_external` 程度 |
| Python 側で HTML サニタイズ | `ammonia` で allowlist。`style` は既定で禁止、`class`/`id` は `mdv-` 以外を剥がす |
| 外部画像を WebView が直接取得 | Rust 側で取得（SSRF ガード移植）→ ディスクキャッシュ → asset protocol で配信。WebView から外部ネットワークへは出さない |
| JavaScript ブリッジ | 使わない。CSP は `default-src 'self'; script-src 'self' 'nonce-…'` |
| 一時 HTML ファイル量産 | 文字列を `eval`/asset protocol で渡す。ディスクに書かない |

### 5.4 性能設計

- **起動**: ウィンドウを先に表示 → プレースホルダ → 本文を後追い。Mermaid/KaTeX は初回描画後に遅延ロード
- **再描画**: 全文 innerHTML 置換をしない。ブロック（見出し単位）でハッシュ管理し、変更ブロックのみ差し替え
- **大文書**: 2MB 超は仮想化（画面内ブロックのみ DOM 化）。10MB 超は「簡易表示モード」に落とす
- **画像**: 遅延読み込み + ディスクキャッシュ（上限付き LRU）
- **検索**: 本文のインデックスを Rust 側で保持（大文字小文字・全角半角の正規化）

### 5.5 PDF 書き出し（要検討の最重要項目）

| 方式 | 忠実度 | 実装 | 備考 |
|---|---|---|---|
| OS 別印刷 API（推奨） | ◎（画面と同一） | WebView2 `PrintToPdfAsync` / WKWebView `createPDF` / WebKitGTK `PrintOperation` を `wry` の生ハンドル経由で呼ぶ | OS ごとに 200〜400 行。Tauri の `print()` は macOS のみ、`window.print()` はダイアログ前提 |
| typst で別生成 | ○（要 CSS 再現） | `typst-as-lib` で MD→typst→PDF | 画面と PDF でレイアウトが二重管理になる |
| ヘッドレス Chromium | ◎ | `chromiumoxide` 等 | Chrome 同梱で +150MB。論外 |

**推奨**: まず OS 別 API を実装し、CI で「同じ入力 → 同じページ数・同じ改ページ位置」をゴールデン比較する。

### 5.6 設定・資産の移行

- `~/.mdviewer/`（macOS）、`%APPDATA%/MDViewerPro`（Windows）を読み、新形式（`settings.json` v2）へ**一方向移行**。失敗時は現行値を壊さない
- プラグインテーマ JSON は `schemars` で検証し、色は `#RRGGBB` / `rgb()` のみ許可（現行の緩い検査を置換）
- 5 言語（ja/en/de/fr/zh）は `fluent` もしくは埋め込み JSON。**キー数一致テスト**を現行同様に維持

### 5.7 テスト戦略（998 件の資産を捨てない）

1. **ゴールデンコーパス**: 現行アプリで代表文書（サンプル 5 言語 + 表 + 数式 + Mermaid + 画像 + 巨大文書）を HTML/PDF に出力し、リポジトリに固定
2. **Rust 単体**: 純粋関数 506 件を `#[test]` へ移植。HTML 出力は `insta` スナップショット
3. **CLI 結合**: `mdv render` の出力をコーパスと diff（CI で必須）
4. **UI**: `@wdio/tauri-service`（macOS も embedded driver で可）+ スクリーンショット比較
5. **性能回帰**: 起動時間・RAM・PDF 生成時間を CI で記録し、閾値超えで失敗

---

## 6. 移行ロードマップ

| Phase | 期間目安 | 内容 | ゲート（次へ進む条件） |
|---|---|---|---|
| 0. 計測・固定 | 1〜2 週 | 現行の起動/RAM/サイズ/PDF を実測。ゴールデンコーパス作成。受入閾値の決定 | 閾値合意（例: 起動 1.5 秒、RAM 200MB、配布 25MB） |
| 1. コア | 3〜4 週 | `mdv-core` + `mdv-render` + `mdv-cli`。comrak/ammonia/設定/テーマ | コーパス HTML 一致率 95%+、純粋関数テスト移植完了 |
| 2. ビューア | 4〜6 週 | Tauri シェル、閲覧モード、TOC、テーマ、設定移行、フォント、クリップボード | macOS/Windows で閲覧・設定・テーマが実用 |
| 3. 編集・輸出 | 2〜4 週 | CodeMirror 6 エディタ、プレビュー同期、PDF（OS 別）、Mermaid/KaTeX | PDF のページ数・改ページが現行一致 |
| 4. 配布 | 2 週 | tauri-action、署名/公証、updater、Linux パッケージ | 3 OS でインストール・起動・更新 |
| 5. 切替 | 1 週 | ベータ配布 → 既定化。Python 版は 1 リリース併存 | クラッシュ率・Issue が閾値内 |

**合計**: 2〜3 か月（フルタイム 1 人 + レビュー）／4〜5 か月（片手間）。案C はこの 3〜4 倍。

---

## 7. リスク登録簿

| リスク | 影響 | 確度 | 対策 |
|---|---|---|---|
| PDF の改ページ・余白が現行と変わる | 高 | 高 | Phase 0 で PDF ゴールデンを作り、Phase 3 のゲートにする。OS 別 API を早期にスパイク |
| Linux の WebKitGTK 差（フォント・描画・依存） | 高 | 中 | v1.0 は macOS/Windows に限定し、Linux は beta。AppImage ではなく Flatpak/deb を主力に |
| MD 編集の仕様変更がユーザーに不評 | 中 | 中 | 「ソース編集 + プレビュー」を既定にし、旧 MD 編集は読み取り専用のプレビューとして残す |
| Rust 製数式/Mermaid の品質不足 | 中 | 高 | 案A では JS 版を継続使用（現行資産）。Rust 版は案C の検証時のみ |
| 998 件の回帰テストの移植コスト | 中 | 高 | 純粋関数から優先移植。Qt 依存テストは UI テストへ読み替え |
| 署名・公証の運用（鍵管理） | 中 | 中 | Apple $99/年、Windows は Azure Trusted Signing 等。CI secret 管理を Phase 4 で整備 |
| Tauri の破壊的変更 | 低 | 低 | 2.x 系に固定。四半期ごとに更新 |
| Rust 人材・保守性 | 中 | 中 | コアを CLI としても動かし、GUI なしでテスト可能に保つ |

---

## 8. 判断が必要な論点（次に決めること）

1. **Linux を v1.0 から出すか。** 出すなら WebKitGTK 依存を許容するか、案C のネイティブに寄せるかの分岐になる
2. **MD 編集を「ソース編集 + プレビュー」に変えてよいか。** ここを譲れないなら WYSIWYG の再設計が必要で、工数が +1〜2 人月
3. **受入閾値。** 例: 起動 1.5 秒 / RAM 200MB / 配布 25MB / PDF ページ一致。数値がないと Phase 0 が終わらない
4. **署名予算。** Apple $99/年 + Windows 証明書（年 $100〜400 程度）。未署名を続けるなら Gatekeeper/SmartScreen の案内は現状維持
5. **モバイル。** Tauri 2 は iOS/Android も出せる。ファイルアプリ連携の設計が別途必要
6. **既存ユーザーの移行。** 設定・テーマ・クリップボードの完全移行を必須にするか

---

## 9. 参考資料（取得 2026-11-01 JST）

- Tauri 2 公式: <https://v2.tauri.app/start/prerequisites/>（最終更新 2026 年）／<https://v2.tauri.app/security/>（2026-07-22）／<https://v2.tauri.app/distribute/>／<https://v2.tauri.app/distribute/appimage/>（2026-05-17）／<https://v2.tauri.app/distribute/windows-installer/>／<https://v2.tauri.app/distribute/sign/macos/>／<https://v2.tauri.app/develop/tests/webdriver/>（2026-06-29）
- Tauri ソース（`Webview::print` の macOS 限定注記）: <https://github.com/tauri-apps/tauri/blob/dev/crates/tauri/src/webview/mod.rs>
- WebView2 配布: <https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution>（更新 2025-10-15）
- Dioxus 0.7 リリースノート（Blitz の位置づけ）: <https://dioxuslabs.com/blog/release-070>
- Slint ライセンス: <https://slint.dev/pricing>
- crates.io 各クレート（版・更新日）: tauri 2.12.5、wry 0.57.1、dioxus 0.7.10、blitz 0.2.1、iced 0.14.0、egui 0.37.0、slint 1.18.1、gpui 0.2.2、comrak 0.59.0、pulldown-cmark 0.13.6、ammonia 4.2.4、syntect 5.3.0、katex-rs 0.3.0、mermaid-rs-renderer 0.3.1、typst 0.15.1、cargo-dist 0.32.0
- 現行アプリ: <https://github.com/oriyu90/MD-Viewer-Pro>（README / main.py / 設計リスク分析レポート / 資料箱/MDViewerPro_Design_Doc.md）

---

## 付録: 用語メモ

- **WebView**: OS が提供するブラウザエンジンの埋め込み部品。macOS=WKWebView、Windows=WebView2（Chromium）、Linux=WebKitGTK
- **Blitz**: Dioxus チームが作る Rust 製 HTML/CSS レンダラ（Taffy + Stylo + Vello）。WebView を使わずに HTML を描く将来解
- **capability**: Tauri の権限定義。どのウィンドウがどのコマンドを呼べるかを JSON で制限する
- **ゴールデンコーパス**: 入力文書と期待出力（HTML/PDF）の組。リライトの回帰検出の基準
