# REVIEW_REPORT — MD Viewer Pro v26.0.1（独立レビュー / WP-07）

- 対象コミット: `e5ab3d7`（v26.0.1: Rust/Tauri rewrite, pre-release）
- レビュー方法: 静的読解 + 実行による検証（`cargo test`、render の入出力プローブ）
- 制約遵守: 既存コードの変更なし、コミットなし、ネットワーク利用なし。書き込みは本ファイルのみ。
- 注記: レビュー中、作業ツリーに **未コミットの変更が追加され続けている**（`commands.rs` `main.rs` `state.rs` `doc.rs` `settings.rs` `theme.rs` `app.js` `index.html` `app.css` `scripts/measure.sh`）。本レビューは **HEAD `e5ab3d7` を対象**とした。未コミット差分への指摘は末尾の「未コミット差分に関する注記」に分離した。

---

## 1. 総評

- 良い点: 原文を正本とする設計、comrak の `unsafe` を有効にした上での ammonia allowlist サニタイズ、`javascript:`/`data:` リンク・`onerror`/`onclick`/`<script>`/`<iframe>`/`<svg>` の除去が確認できた。設定とファイル保存は tmp → fsync → rename の原子的保存になっている。`mdv-core` の単体テストは 25 件すべて通過。
- 主な懸念: (1) 見出し ID 注入が **生 HTML ブロック中の `<h1>`〜`<h6>` を誤マッチ**し、TOC と DOM の id が食い違う（実証済み）。(2) Tauri の **アプリ定義コマンドが ACL で絞られておらず**、webview 内の任意コードから任意パスへの書き込み（`save_text`）が可能。(3) i18n キーの欠落、(4) ショートカットの二重発火の可能性。
- 判定: **REWORK**（CRITICAL は無いが、HIGH 2 件（見出し ID の誤マッチ、アプリコマンドの権限境界）を修正してから再レビューを要する）。

---

## 2. 指摘一覧

凡例: 重大度 / 対象 / 観測事実 / 影響 / 修正案

### HIGH-1: 見出し ID 注入が生 HTML 内の `<hN>` を誤マッチし、TOC と DOM がずれる
- 対象: `crates/mdv-core/src/render.rs:252-280`（ID 注入ループ）
- 観測事実（実行で再現）: 入力 `<h2>raw</h2>\n\n# Real\n\n## Second\n` に対し、
  - `headings` = `[{Real, id:"real"}, {Second, id:"second"}]`
  - 出力 HTML = `&lt;<h2 id="real">raw</h2>` / `&lt;<h1 id="second">Real</h1>` / `<h2>Second</h2>`
  - すなわち、生の `<h2>` がエスケープされずに残り（comrak が text 扱いにした `<` の直後）、注入器がそれを見出しとして数えて `id="real"` を奪う。その結果 `# Real` には `id="second"`、`## Second` には id が付かない。
- 原因: `headings` は AST（`NodeValue::Heading`）から収集する一方、注入は `comrak::markdown_to_html` 出力の文字列走査（`rest.find("<h")`）で行う。両者の出現順が一致する保証がない（生 HTML・blockquote 内見出し等で不一致）。
- 影響: 目次クリック（`document.getElementById(h.id)`）が **誤った見出しへスクロール**する。`id` 属性の二重付与・欠落も起きる。アンカーリンクの正当性が崩れる。
- 修正案: 見出し ID を comrak の AST 上で直接付与する（`NodeHeading` の出力 hook、もしくは comrak の `header_ids` 拡張（`options.extension.header_ids`）を用い、自前の文字列走査を廃止する）。少なくとも `<h` の走査で `<hN>` の直前が `<` 始まりの生 HTML 行でないことを検証する。回帰テストとして上記入力を追加する。

### HIGH-2: アプリ定義コマンドが権限で制限されず、webview から任意パスへ書き込み可能
- 対象: `apps/desktop/src/commands.rs:235-237`（`save_text`）、`:263-276`（`reveal_path`）、`apps/desktop/capabilities/default.json`、`apps/desktop/build.rs`
- 観測事実: `capabilities/default.json` は `core:default` のみ付与。`build.rs` は `tauri_build::build()` のみで `AppManifest` を宣言していない。よって `save_text(path, content)` は **任意の絶対パスへ任意内容を書き込める**（検証なし）。`reveal_path` も任意パスを `open -R` に渡す。Markdown 由来 HTML の無害化（ammonia）は通っているが、万一の XSS（将来の ammonia 設定ミス・依存の脆弱性・`ui/` 内の innerHTML 経路）が起きた場合、これが権限昇格の経路になる。
- 影響: コンテンツ内スクリプトから `~/.zshrc`・LaunchAgents 等への書き込みが可能（深刻度は XSS 成立が前提のため HIGH）。
- 修正案: (a) `build.rs` で `tauri_build::Attributes::new().app_manifest(AppManifest::new().commands(&[...]))` を用い、アプリコマンドを ACL 化して capability で `main` に限定付与する。(b) `save_text` は「ユーザーが保存ダイアログで選んだパス」だけを受け付ける（Rust 側で発行したトークンと照合）か、少なくとも拡張子と親ディレクトリを検証する。(c) `reveal_path` は `open -R -- <path>` とし、対象が既存ファイルであることを確認する。

### MEDIUM-1: i18n キーの欠落（ja/en/de/fr/zh すべて）
- 対象: `ui/i18n.json`、`ui/js/app.js`、`ui/index.html`
- 観測事実: コード・HTML が参照するキーのうち `copied` `copy` `saved` `clip_copy_hint` `fmt_text_placeholder` `cancel` `ok` `theme_color_label` `find_unavailable` が `i18n.json` の ja に存在しない（全言語で欠落）。`t(key, fallback)` は日本語のハードコード fallback に落ちる。`applyI18n` は欠落キーをスキップするため、`index.html` の `cancel`/`ok` ボタン等は日本語のまま残る。
- 影響: 英語・ドイツ語・フランス語・中国語ユーザーに日本語が表示される。
- 修正案: 上記キーを全 5 言語に追加。`i18n.json` と参照キーを照合する検査を `cargo test` 相当の CI に入れる（現状 JS テストは無い）。

### MEDIUM-2: ショートカットの二重発火の恐れ
- 対象: `apps/desktop/src/menu.rs:21-38`（Cmd+N/O/S/Shift+S の accelerator）、`ui/js/app.js:761-770`（document keydown で同じキーを処理）、`ui/js/app.js:803-807`（`listen("menu")` で同じ関数を呼ぶ）
- 観測事実: ネイティブメニューの accelerator が `menu` イベントを発火して `saveFile`/`openFile` を呼ぶ経路と、DOM の keydown が同じ関数を呼ぶ経路が両方存在する。JS 側の `e.preventDefault()` はネイティブ accelerator のイベント発行を止めない。
- 影響: Cmd+O で開く/保存ダイアログが二度出る、Cmd+S が二重保存になる可能性。実 GUI 未検証（後述の未確認事項）。
- 修正案: キーボード操作はどちらか一方に統一する。推奨はネイティブメニュー側（accelerator）に集約し、JS の keydown からは Cmd+S/O/N を外す。

### MEDIUM-3: `find` メニューが未実装のまま UI に露出
- 対象: `apps/desktop/src/menu.rs:67-68`、`ui/js/app.js:817`
- 観測事実: 「検索…」(Cmd+F) が「検索は次のアップデートで対応します」と toast するだけ。ただし未コミット差分では `findState`（検索 UI）が追加されつつある。
- 影響: 機能が無いことが利用者に分かる形で出ているが、i18n キー `find_unavailable` が欠落（MEDIUM-1）しており日本語固定。
- 修正案: 実装完了まで項目を非表示にするか、リリースノートに明記する。

### MEDIUM-4: 設定の破損退避が既存 `.bak` を上書きする
- 対象: `crates/mdv-core/src/settings.rs:126-128`
- 観測事実: 破損時 `fs::rename(path, path.with_extension("json.bak"))`。既に `settings.json.bak` が存在すると上書きされ、2 回目の破損で 1 回目の退避内容が失われる。また rename の失敗は無視（`let _ =`）される。
- 影響: 復旧用の退避データが消える（データ保全の観点で MEDIUM）。
- 修正案: タイムスタンプ付き退避名（`settings.json.bak-<unix>`）にする。rename 失敗時はログを残す。

### MEDIUM-5: 数式・Mermaid 用の `onerror` インラインハンドラが CSP で無効
- 対象: `ui/index.html:8`
- 観測事実: `<link ... onerror="this.remove()">`。CSP は `script-src 'self'`（inline 禁止）のため、インラインのイベントハンドラは実行されない。`katex.min.css` が無くても remove されず、404 のリンクが残るだけ。
- 影響: 機能への影響は軽微（CSS 欠落時の見た目）。ただし「フォールバックが効いている」という誤った前提を生む。
- 修正案: 削除するか、起動時に JS で存在確認してから読み込む。

### MEDIUM-6: 見出し ID の重複解決がテキスト衝突時に順序依存
- 対象: `crates/mdv-core/src/render.rs:237-247`
- 観測事実: `# a` `# a-1` `# a` → ids = `["a","a-1","a-2"]`。`a-1` を明示見出しにした場合は「後から来た `a` が `a-1` と衝突して `a-2`」となり、ID 自体は一意。ただし HIGH-1 の不整合と組み合わさると、TOC 上の id と実 DOM id が一致しない。
- 影響: 単独では問題なし。HIGH-1 解消後に再検証が必要。
- 修正案: HIGH-1 の修正で AST 上の ID 付与に統一した後、衝突ケースの回帰テストを追加する。

### LOW-1: 画像 `img-src` に `https:` を許可（外部トラッキング）
- 対象: `apps/desktop/tauri.conf.json:25`（CSP `img-src 'self' data: blob: https:`）
- 観測事実: Markdown 内の `![](https://...)` が外部へ取得される（プライバシー上の既知の挙動）。
- 修正案: 既定で遮断し、ユーザーが許可した場合のみ読み込む、もしくは仕様として README に明記する。

### LOW-2: `reveal_path` が `open` の終了コードを無視
- 対象: `apps/desktop/src/commands.rs:263-270`
- 観測事実: `.status()` の結果（終了コード）を見ず `Ok(())` を返す。`-R` の後にオプション扱いされ得る `-` 始まりのパスに `--` を付けていない。
- 影響: 失敗が UI に出ない。現状呼び出し元は `state.docPath`（アプリが設定した値）のみで悪用可能性は低い。
- 修正案: `status.success()` を検証し、`open -R -- <path>` とする。

### LOW-3: 設定の `recent` が存在確認されない
- 対象: `crates/mdv-core/src/settings.rs`、`apps/desktop/src/commands.rs:157-168`
- 観測事実: `recent` は保存時に検証されるが、開く前に存在を確認しない（開く時点で `read_file` がエラーを返す）。
- 修正案: 起動時にリストを正規化し、存在しないものを除く。

### LOW-4: `selftest.json` / `startup.json` を非原子的に書き込む
- 対象: `apps/desktop/src/commands.rs:128`、`:439`、`:450`
- 観測事実: 直接 `fs::write`。途中で落ちると壊れたファイルが残る。
- 影響: 検証・計測用ファイルのみで、ユーザーデータには影響しない。
- 修正案: 既存の原子的保存関数を流用する。

### LOW-5: 単一インスタンスのソケットが異常終了後に残る可能性（一応対策済み）
- 対象: `apps/desktop/src/state.rs:134`
- 観測事実: 起動時に `remove_file(&sock)` で古いソケットを除去している（対策あり）。ただし既存インスタンスが生きている場合も `remove_file` してから bind するため、**2 つ目のインスタンスが起動時に 1 つ目の listener を奪う**競合が起きる（`forward_to_running_instance` が先に成功すれば回避されるが、同時起動では競合）。
- 修正案: 接続テスト後にのみ削除する、もしくはロックファイルを併用する。

### LOW-6: `write_file` の一時ファイル名が拡張子依存
- 対象: `crates/mdv-core/src/doc.rs:113-116`
- 観測事実: 一時名は `x.md.tmp`。同名の既存 `x.md.tmp` を上書きする。拡張子なしの場合は `"md"` 固定で `x.md.tmp` になり、`.md` 以外の拡張子も同様。
- 影響: 並行保存時のわずかな競合のみ。
- 修正案: `tempfile` の `NamedTempFile::persist` を用いる（同一ディレクトリ・一意名）。

### LOW-7: 大容量ファイルの上限が UI 固まり防止の目安に留まる
- 対象: `crates/mdv-core/src/doc.rs:56`（32 MiB 上限）
- 観測事実: 上限チェックは実装済み（`TooLarge`）。ただし上限内でも render は同期処理。
- 修正案: 大きいファイルでは render をバックグラウンドに移す（性能課題、今回は未計測）。

---

## 3. 実行した検証

| 項目 | 結果 |
|---|---|
| `cargo test -p mdv-core --offline` | **PASS** — 25 件すべて成功（exit 0） |
| `cargo test --workspace --offline` | **PASS** — exit 0（mdv-core 25 件、desktop 0 件） |
| XSS プローブ（`onerror`/`javascript:`/`data:`/`<iframe>`/`<svg>`/`onclick`） | 全て無害化を確認 |
| 見出し ID 注入の順序検証 | **FAIL（HIGH-1 を再現）** |
| i18n キー照合（`ui/i18n.json` vs 参照） | 9 キー欠落を確認（MEDIUM-1） |
| バージョン整合（`tauri.conf.json` / workspace `Cargo.toml` = 26.0.1） | PASS |
| `package_macos.sh` の `rm -rf` 対象 | `$APP` `$STAGE` `$DMG` のみ。いずれも `$ROOT/dist` 配下の固定パス。安全 |

- 一時的な検証ファイル（`crates/mdv-core/tests/`）は作成→実行→削除済み。`git status` で追加物がないことを確認。
- 観測: 検証途中で作業ツリーの別ファイルが変更されたため、初回の `cargo test --workspace` では `apps/desktop/src/commands.rs:460` に一時的なコンパイルエラーが出た（`let ... else` の型不一致）。再実行時には当該箇所は `return Ok(())` となり解消していた。最終結果は再実行後のもの。

## 4. 未確認事項

- **GUI 実行は未実施**: ショートカットの二重発火（MEDIUM-2）、ドラッグ＆ドロップ、印刷、単一インスタンス転送は実機確認していない。
- **`desktop` クレートのテストは 0 件**: `commands.rs` / `state.rs` の振る舞い（保存・設定の移行・クリップ上限）は単体テストが無く、コードを読んでの判断のみ。
- **署名・公証**: `package_macos.sh` は ad-hoc 署名のみ。配布時の Gatekeeper 挙動は未検証。
- **性能**: 大きな Markdown の render 時間、`--selftest` の結果は未計測。
- **`mermaid` の `securityLevel: "strict"`**: 設定は確認したが、Mermaid 側のスクリプト実行防止の実効性は未検証。
- **未コミット差分**: 本レビュー中に作業ツリーが継続変更されている。最終的なリリース候補（コミット）が本報告の HEAD と一致するかは未確認。

## 5. 指摘件数（重大度別）

| 重大度 | 件数 | 主な項目 |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 2 | 見出し ID の誤マッチ（HIGH-1）、アプリコマンドの権限境界（HIGH-2） |
| MEDIUM | 6 | i18n 欠落、ショートカット二重発火の恐れ、find 未実装露出、.bak 上書き、CSP 無効な onerror、ID 衝突の順序依存 |
| LOW | 7 | img-src https、reveal_path、recent 未検証、非原子的な補助ファイル、単一インスタンス競合、tmp 名、大容量 render |

## 6. 判定

**REWORK**

理由: HIGH 2 件（HIGH-1: 見出し ID の誤マッチにより TOC のアンカーが誤った見出しを指す。HIGH-2: アプリ定義コマンドに権限境界が無く、webview から任意パスへ書き込めるため、無害化の失敗が権限昇格に直結する）を修正する必要がある。MEDIUM の i18n 欠落と二重発火は、リリース前に解消することを強く推奨する。`mdv-core` の既存テストは全て通過しており、修正後は HIGH-1 の回帰テストを追加して再レビューを行うこと。

## 未コミット差分に関する注記（HEAD 対象外）

レビュー中の作業ツリーには以下の未コミット変更があった。HEAD の指摘とは別に確認を推奨する。
- `commands.rs`: `reveal_path` / `print_page` の `return` を除去（clippy 的修正、問題なし）。`mark_start`/`ui_ready` で `startup.json` を `fs::write`（LOW-4 と同種）。
- `state.rs`: 未使用の `Clip` 構造体を削除（問題なし）。
- `doc.rs`: `head.iter().any(|&b| b==0)` → `contains(&0)`（問題なし）。
- `theme.rs`: `#[derive(Default)]` へ移行（問題なし）。
- `app.js`: `boot()` 末尾に `invoke("ui_ready")` 追加。
- `index.html` / `app.css` / `scripts/measure.sh`: 未精査（今回の対象外として差分のみ確認）。
