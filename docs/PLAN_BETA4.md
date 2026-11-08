# β4.0 作業プラン — 標準アプリ対応 / TXT 保存維持 / ツールバー縦幅

対象: `md-viewer-pro-rust`（Rust + Tauri 2）。基準版 β3.0（`26.3.0-beta.3.0`）。
本ドキュメントは実装前の計画と、実装後に確定した設計・検証結果を併記する。

---

## 0. 要求の整理

| # | ユーザー要求 | 解釈（受け入れ条件） |
|---|---|---|
| 1 | txt や md を開く時に標準アプリとして開くことができない | Finder の「このアプリケーションで開く」に MD Viewer Pro が現れ、`.md` / `.txt` / `.markdown` / `.mdown` / `.yml` / `.yaml` の既定（標準）アプリに設定でき、ダブルクリックで開ける。既存インスタンスがあればそこへ渡す |
| 2 | txt を開いて編集した時、特に md 系ツールバーの機能を使っていない場合は保存も txt で行われるように | `.txt` を開いて書式ツールバー（太字・見出し・表など）を使わずに保存した場合、拡張子は `.txt` のまま。書式ツールバーで Markdown 記法を挿入した場合のみ、保存時に `.md` への変換を案内する |
| 3 | 上部バーボタンの縦幅を 0.9 倍。window 横幅に応じて縦幅が変わるときはスムーズに。さらに window 縦幅に応じて 1x–0.8x | ツールバー高さの基準を従来比 0.9 倍に。幅による段階変化はアニメーションで滑らかに。さらにウィンドウ縦幅に応じて 1.0 倍〜0.8 倍の係数を掛ける |

安全設計の制約（common rules / ユーザー指示）:
互換性（設定ファイル・旧アプリと併存）、既存機能の維持、クラッシュ安全性、
メモリ安全性、日本語と英語の完全対応 UI。

---

## 1. 現状分析（実測）

### 1-1. 問題 1 の原因

`scripts/package_macos.sh` が生成する Info.plist は次の状態だった。

- `CFBundleDocumentTypes` は 1 件だけ（`Markdown Document` / role=Viewer / rank=Alternate）。
- `UTImportedTypeDeclarations` が無い。
- `public.plain-text` を 1 つの書類型に同居させているため、`.txt` の扱いが
  「Markdown 書類」として曖昧になる。

`lsregister -dump` で実測した登録内容（β3.0 の .app）:

```
claims: net.daringfireball.markdown, public.plain-text
rank:   Alternate
roles:  Viewer
```

さらに、旧 Python 版（`MDViewerPro.spec`）は次の 3 点を持っていたが、Rust 版で失われていた。

1. `UTImportedTypeDeclarations` で `net.daringfireball.markdown` を宣言（拡張子 `.md`/`.markdown`、
   MIME `text/markdown`、`public.plain-text` に準拠）
2. Markdown 書類は `LSHandlerRank: Owner` / `CFBundleTypeRole: Editor`
3. YAML 書類を別エントリ（`Alternate`）として分離

加えて Rust 版固有の不足:

4. `RunEvent::Reopen`（Dock アイコン再クリック・Finder でアプリ選択時）に反応しない
5. 起動時のファイル引数が「最初の非 `-` 引数」で、`open -a` の `-psn_...` や
   `--flag value` 形式の値、複数ファイルを正しく扱えない
6. 既存インスタンスへ転送するとき、転送先ウィンドウを前面に出す処理が無い

### 1-2. 問題 2 の原因

- `save_document` は渡されたパスへそのまま書くため、既存 `.txt` への保存は
  実際には `.txt` のままで書かれていた（拡張子は変わらない）。
- ただし `.txt` を開いても UI 上は「Markdown 文書」として扱われ、
  書式ツールバーで Markdown 記法を入れると `.txt` の中身が Markdown になる。
  ユーザーから見ると「txt なのに md として保存された」状態になる。
- `pick_save` の推奨名は常に `untitled.md`、フィルタも Markdown 先頭。
- 新規作成（`newDocument`）は常に TXT 編集で開くが、保存は `.md` 既定。
- 「どこまでが書式ツールバー由来の変更か」を判定する仕組みが無い。

### 1-3. 問題 3 の現状

- `ui/css/app.css` の `:root` に `--tb-h: 72px` があり、メディアクエリで
  `58 / 46 / 40px` に段階的に切り替わる（`max-width: 1099 / 779 / 619`）。
- 切り替えは瞬時で、リサイズ中にガタつく。縦幅は考慮していない。
- 書式ツールバーは `--fmt-h: 52 / 44 / 36 / 32px` で同じ構造。

---

## 2. 設計

### 2-1. 問題 1 — 標準アプリ対応

**(a) Info.plist（`scripts/package_macos.sh`）**

| 書類型 | UTIs | 拡張子 | role | rank |
|---|---|---|---|---|
| Markdown Document | `net.daringfireball.markdown`, `public.plain-text` | md, markdown, mdown, mkd | Editor | Owner |
| Plain Text Document | `public.plain-text` | txt | Editor | Alternate |
| YAML Document | `public.yaml`, `public.plain-text` | yml, yaml | Viewer | Alternate |

- `UTImportedTypeDeclarations` に `net.daringfireball.markdown`
  （`public.plain-text`/`public.content` 準拠、拡張子 `.md`/`.markdown`、MIME `text/markdown`）を宣言。
- `LSHandlerRank: Owner` は「このアプリを既定にできる」ことを LaunchServices に示す。
  既に他アプリが既定なら、ユーザーが「常にこのアプリで開く」を選んだ時点で切り替わる。
- `CFBundleTypeRole: Editor` にして「開く」だけでなく「編集して保存」できることを宣言する
  （保存は既存の原子的書き込みで行う）。YAML は `Viewer` のまま。
- `NSPrincipalClass` は付けない（Tauri 既定のまま。付けると AppKit 初期化が変わる）。
- バンドルに `CFBundleLocalizations`（ja, en）を追加し、Finder の表示言語を揃える。

**(b) 起動引数の解析（`apps/desktop/src/main.rs` / `commands.rs`）**

- `-psn_…` や `-…` で始まる引数は除外（従来どおり）。
- 値を取るフラグ（`--screenshot <out>`、`--mode <m>`、`--theme <t>`、`--page <p>`、
  `--dialog <d>`、`--export-pdf <in> <out>`）の直後の値はパスとして扱わない。
- 複数ファイル引数は最初の 1 つを開き、残りは `open-path` イベントで順次開く。

**(c) Dock 再オープン（`RunEvent::Reopen`）**

- `has_visible_windows == false` なら既存ウィンドウを表示して前面へ。
- それ以外は前面化のみ。前面化は `NSApp activate`（macOS 14+）または
  `activateIgnoringOtherApps(true)`（13 以前）をメインスレッドで呼ぶ。
  Tauri の `set_focus` だけでは Dock からの再オープン時に前面に来ないことがあるため。

**(d) 既存インスタンスへの転送**

- 転送メッセージを JSON ライン化（`{"path": "..."}`、空は起動要求）。
  旧形式（生パスのみ）も受け付ける（後方互換）。
- 受信側は `open-path` イベント発行に加えてウィンドウを前面化する。
- 転送の読み取りは `read_to_string` ではなく上限付き読み取りにする
  （壊れたクライアントで無制限にメモリを確保しない）。

**(e) 起動時のファイル受け取り**

- `RunEvent::Opened`（Finder/`open` コマンド）に加え、起動引数のパスも
  `bootstrap.initial` と `open-path` の両方で渡す（フロントエンドの準備待ちを取りこぼさない）。

### 2-2. 問題 2 — TXT 保存の維持

**方針**: 「書式ツールバー（Markdown 記法）を使ったか」を文書ごとに記録し、
未使用なら拡張子を変えず、使用した場合だけ `.md` への変換を提案する。

1. **書式ツールバーの使用検出**
   - `applyFormat(kind)` 実行時に `state.formatUsed = true` を立てる。
   - `applyFormatMd` / `applyFormatText` の両方を対象（MD編集・TXT編集）。
   - 書式バーのボタンは `data-fmt` で識別済みなので、配線を 1 か所に集約する。
2. **文書の書類種別**
   - `state.docKind`: `"md"` / `"txt"` / `"yaml"`。`open_path` の戻り値 `kind` を
     拡張子から確定（`doc.rs` の `DocKind` をそのまま使う）。
   - 新規作成は `"md"`（従来どおり）。`untitled.txt` として保存した場合は `"txt"` へ。
3. **保存**
   - 保存先が既にある（`state.docPath`）場合は**必ずそのパスへ書く**。
     拡張子は変わらない（従来の挙動を明示的に保証し、回帰テストを追加）。
   - `.txt` 文書で書式ツールバーを使った場合のみ、保存前に確認ダイアログ:
     「Markdown 記法が含まれています。`.md` として保存しますか？」
     - 「.md で保存」→ 保存ダイアログ（推奨名 `name.md`）
     - 「.txt のまま保存」→ そのまま
     - 「キャンセル」→ 何もしない
   - 保存後、拡張子に応じて `docKind` とモード可用性を更新する
     （`.txt` になったら MD編集は使えないため TXT編集へ寄せる）。
4. **保存ダイアログの推奨名・フィルタ**
   - 既存パスがあればそのファイル名、無ければ `untitled.md`（`docKind` が `txt` なら `untitled.txt`）。
   - `pick_save` に `kind` 引数を追加し、フィルタの先頭を文書種別に合わせる
     （`.txt` 文書なら Text 先頭）。拡張子を補完するのは保存ダイアログ側の挙動に任せ、
     アプリ側で勝手に付け替えない。
5. **互換性**
   - 既存の `.md` 文書の保存挙動は完全に不変。
   - `.txt` 文書でも、書式ツールバーを使わなければ従来どおりそのまま保存される
     （＝要求どおり。変更点は「使ったときに確認する」だけ）。

### 2-3. 問題 3 — ツールバー縦幅

**基準値**（従来の段階値 × 0.9）:

| 幅の段階 | 従来 `--tb-h` | 新基準 `--tb-base` | 従来 `--fmt-h` | 新 `--fmt-base` |
|---|---|---|---|---|
| ≥ 1100px | 72 | **64.8** | 52 | **46.8** |
| 780–1099px | 58 | **52.2** | 44 | **39.6** |
| 620–779px | 46 | **41.4** | 36 | **32.4** |
| < 620px | 40 | **36.0** | 32 | **28.8** |

**縦幅係数**（ウィンドウ高さ。単調増加・連続）:

```
h <= 360px   -> 0.80
360 < h < 900 -> 0.80 + 0.20 * (h - 360) / 540
h >= 900px   -> 1.00
```

- 360px（最小ウィンドウ高）で 0.80、900px 以上で 1.00。中間は線形。
- 範囲は常に `[0.80, 1.00]` にクランプ（数値の異常値・NaN でも破綻しない）。
- 係数はウィンドウ**縦幅**（`innerHeight`）で決める。幅は段階値の切り替えにだけ使う。
- 実効高さは「基準値 × 係数」なので、大きい幅の段階では 64.8→51.8px（0.72 倍）、
  小さい幅の段階でも同率で縮む。

**スムーズ化**:

- 段階値の切り替えは CSS 変数 `--tb-base` / `--fmt-base` を JS で書き換え、
  `transition: height 180ms cubic-bezier(.4,0,.2,1)` で補間する。
- 縦幅係数は `requestAnimationFrame` で 1 フレーム 1 回にまとめて更新し、
  リサイズ中のレイアウトスラッシングを避ける。
- `prefers-reduced-motion: reduce` では遷移を無効化する（アクセシビリティ）。
- 印刷・PDF 書き出し時はツールバーを非表示にするため影響なし。

**実装位置**:

- CSS: `:root` の既定値を新基準へ、`--tb-scale` を追加し
  `height: calc(var(--tb-base) * var(--tb-scale))` に変更。
  メディアクエリは `--tb-base` / `--fmt-base` の段階値のみを定義。
- JS: `syncToolbarMetrics()` を追加し、`resize`（rAF で間引き）と起動時に呼ぶ。
  既存の `syncWrapWidth()` と統合して 1 本のリサイズハンドラにする。

---

## 3. 日本語 / 英語の完全対応

- 追加する文言はすべて `ui/i18n.json` の 5 言語（ja/en/de/fr/zh）へ追加する。
- 今回の要求で必須なのは日本語・英語。ドイツ語・フランス語・簡体中文も同じキーで埋める
  （キー数一致をテストで担保）。
- `index.html` の未翻訳の直書き文言（PDF ダイアログの「上:」「右:」、設定の「テキスト」、
  検索バーの placeholder、書式ボタンの `title` 属性など）を `data-i18n` / `data-i18n-title` /
  `data-i18n-placeholder` 化する。
- `applyFormatText` 内の直書き（「リンク」「見出し」「内容」）も i18n 化する。
- 日本語・英語の両方で、ダイアログ・ツールバー・トーストに未翻訳の日本語が出ないことを
  セルフテストで検査する（`lang=en` 時に日本語文字が残らない）。

---

## 4. 安全設計

| 観点 | 対策 |
|---|---|
| 互換性 | 設定スキーマ v2 のまま。新規キーは持たない（`docKind` はセッション内のみ）。旧 Python 版の Info.plist 宣言と同等以上にする。旧形式のインスタンス転送メッセージも受理 |
| 既存機能 | 保存・PDF/HTML 書き出し・MD編集・目次・検索・テーマ・クリップの経路は変更しない。ツールバーは見た目のみ |
| クラッシュ安全性 | 保存は従来の原子的書き込み（tmp → fsync → rename）。転送ソケットの読み取りは上限付き。リサイズ処理は例外を握りつぶして UI を止めない |
| メモリ安全性 | `unsafe` は既存の objc2 呼び出しのみ。追加の Objective-C 呼び出しはメインスレッドで実行し、`MainThreadMarker` を取得できない場合は何もしない |
| データ損失 | `.txt` の保存は必ず同一パス。変換はユーザー確認付き。キャンセル時は何も書かない |

---

## 5. 実装タスク

1. [P] `scripts/package_macos.sh`: Info.plist の書類型・UT 宣言・`CFBundleLocalizations`
2. [P] `apps/desktop/src/main.rs`: 引数解析の分離・`Reopen` 対応・複数ファイル
3. [P] `apps/desktop/src/state.rs`: 転送メッセージの JSON 化と上限付き読み取り・前面化
4. [P] `apps/desktop/src/commands.rs`: `open_path` の `kind` を拡張子から確定、`pick_save` の `kind`
5. [P] `crates/mdv-core/src/doc.rs`: `DocKind` の拡張子判定に `txt` 明示・テスト追加
6. `ui/js/app.js`: `docKind` / `formatUsed` の追跡、保存フロー、ツールバー計測
7. `ui/css/app.css`: ツールバー基準値・係数・遷移
8. `ui/index.html` / `ui/i18n.json`: 未翻訳の除去と新規キー
9. `ui/js/app.js` セルフテスト拡張: ツールバー高さ・TXT 保存・i18n 検査
10. ドキュメント: README / RELEASE_NOTES / docs / 保守文書

---

## 6. 検証計画

| 検証 | 方法 | 合格条件 |
|---|---|---|
| 単体テスト | `cargo test --workspace` | 全件成功（既存 25 件 + 追加） |
| 静的解析 | `cargo clippy --workspace -- -D warnings` | 警告 0 |
| 書式 | `cargo fmt --check` | 差分なし |
| Info.plist | `plutil -lint` / `plutil -p` | 書類型 3 件・UT 宣言 1 件 |
| LaunchServices | `lsregister -f` 後に `lsregister -dump` | `net.daringfireball.markdown` と `public.plain-text` の claim が Owner/Editor で登録 |
| 標準アプリ起動 | `open -a "MD Viewer Pro" sample.txt` / `sample.md` | 起動し、タイトルにファイル名が出る |
| 二重起動 | 起動中に `open -a` で別ファイル | プロセス 1 個のまま既存ウィンドウで開く |
| TXT 保存 | セルフテスト（`--selftest`） | `.txt` への保存後も拡張子 `.txt`、内容一致 |
| ツールバー高さ | セルフテストで `getBoundingClientRect().height` を複数サイズで記録 | 幅 1280/900 で 64.8、幅 800 で 52.2、高さ 500 で係数 0.8 が掛かる |
| 実画面 | `--screenshot` | ツールバーが 0.9 倍で描画されている |
| i18n | セルフテスト | ja/en のキー数一致、en で日本語文字が出ない |

---

## 7. リリース・サイト更新（検証合格後）

1. バージョンを `26.4.0-beta.4.0` へ（表示 β4.0）。
2. `./scripts/package_macos.sh` で DMG を作成し、SHA-256 を記録。
3. 開発リポジトリ（private）へ push。
4. 公開リポジトリ `oriyu90/MD-Viewer-Pro` の `v26-rust` ブランチへスナップショットを反映し、
   公開 Release `v26.4.0-beta.4.0`（prerelease）を作成して DMG を添付。
5. `studio-rizi` の `website/projects/md-viewer-pro/` を 4 言語で更新し、
   `npm run build` / `validate` / `count-files` / `test` を通して push。
6. 保守文書（common-rules-document）を更新。

---

## 8. 実装結果（確定）

実装後の差分・検証結果は `docs/QA_REPORT.md` の β4.0 節と本ドキュメントの
「9. 実装メモ」に記録する。

## 9. 実装メモ（実装後に確定した内容）

計画から変わった点と、実装中に発見した落とし穴を記録する。

### 9-1. 計画から変えた点

| 項目 | 計画 | 実装 | 理由 |
|---|---|---|---|
| ツールバーの補間 | CSS `transition: height` | JS が `--tb-scale` を 180ms で補間 | 実測でプログラム的リサイズ時に CSS transition が止まり、高さが更新されなかった |
| フレーム制御 | `requestAnimationFrame` | `setTimeout(16ms)` | この WebView で rAF が発火しない場合があり、リサイズ処理が二度と走らなくなった |
| 縦幅係数 | 3 区分の折れ線（720px で不連続） | 360→900px の単調線形 | 当初案は 720px で 0.9994→0.900 と不連続になり、リサイズ中にガタつくため |
| リサイズ検知 | `resize` イベントのみ | `resize` + `ResizeObserver` + 250ms ポーリング | `set_size` 等では `resize` が発火しないことを実測で確認 |
| 確認ダイアログ | Tauri dialog プラグイン | アプリ内 `<dialog>` | `withGlobalTauri` のバンドルに dialog プラグインが含まれず、ボタン名を i18n できない |
| ウィンドウリサイズ（テスト） | JS の `window.setSize` | Rust の `selftest_resize` コマンド | `core:default` の ACL では `plugin:window|set_size` が許可されない。ACL は広げない |

### 9-2. 発見した不具合（β3.0 まで潜在）

1. **起動時ファイルの取りこぼし（要求 1 の主因）**
   `RunEvent::Opened` は起動直後（実測 0ms）に発火するが、フロントエンドが
   `open-path` を購読するのは `ui_ready`（実測 460ms）以降。そのため emit が捨てられ、
   Finder や `open -a` で開いても起動ダイアログが出るだけだった。
   → `pending_paths` に溜めて `ui_ready` で流す方式に変更。

2. **`.txt` が Markdown 文書として扱われていた**
   `open_path` が `.txt` でも `kind: "md"` を返していたため、UI 側で区別できなかった。
   → `DocKind::id()` を追加し、`"txt"` を返すようにした。

3. **既存の clippy 警告 2 件**
   `cfg` 分岐の `return` に `needless_return` が出ていた（β3.0 から）。
   `#[allow]` と理由コメントで抑止（CI の `-D warnings` を通すため）。

### 9-3. 変更ファイル

```
apps/desktop/src/main.rs       起動引数・Opened/Reopen・pending 経由の受け渡し
apps/desktop/src/state.rs      pending_paths / ui_ready / JSON 転送 / 前面化 / 単体テスト
apps/desktop/src/commands.rs   kind の返却 / pick_save の kind / startup_paths / selftest_resize
crates/mdv-core/src/doc.rs     DocKind::id() / prefers_plain_text() / kind_for_save() / テスト
scripts/package_macos.sh       書類型 3 件・UTI 宣言・Info.plist 自動検証
ui/js/app.js                   docKind / formatUsed / 保存フロー / ツールバー計測 / セルフテスト
ui/css/app.css                 --tb-base / --tb-scale / calc / .txt 案内 / 確認ダイアログ
ui/index.html                  未翻訳の直書きを data-i18n 化、.txt 案内要素
ui/i18n.json                   160 → 186 キー（5 言語すべて）
docs/PLAN_BETA4.md             本ドキュメント
docs/QA_REPORT.md              β4.0 の検証結果
```

### 9-4. 検証結果の要約

- `cargo test --workspace`: 34 件 PASS
- `cargo clippy --workspace --all-targets -- -D warnings`: 警告 0
- `--selftest`: `ok=true`、`tbMatrix.allOk=true`（6 サイズすべて期待値一致）、
  `.txt` 保存で `savedExt=txt`、i18n 5 言語でキー一致・英語に日本語なし
- LaunchServices: Markdown=Owner/Editor、Plain Text=Alternate/Editor、YAML=Alternate/Viewer
- 実機: `.txt` / `.md` の起動時オープン、二重起動の転送（プロセス 1 個）を確認
