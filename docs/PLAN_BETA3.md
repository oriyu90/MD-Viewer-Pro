# 実装計画 — β3.0（26.3.0-beta.3.0）

作成: 2026-11-05。対象作業は 6 件。すべて `ui/` + パレット + アイコンが範囲で、Rust のロジック変更は最小。

## 1. 配色 — ダークは黒背景に白文字、ライトは逆

- ダーク: `text` `#c0c0c0` → `#f5f5f5`（白に近い）。`text_dim` `#484848` → `#b3b3b3`
  （「灰色は用いてもかなり明るく」を満たす）。
- ライト: `text` `#000000` のまま、`text_dim` `#909090` → `#636363`（暗めの灰）。
- `crates/mdv-core/src/theme.rs` の `dark_palette` / `light_palette` と、
  `ui/css/app.css` `:root` の既定値を同値に更新（Rust 側が注入するので既定値はフォールバック）。
- コード行・テーブル罫などの色は変えない（本文文字色のみ要求）。
- 検証: スクショの画素サンプリングで `text` が #f5f5f5 付近になること。

## 2. フォント — 本文と UI 全体を太く

- 1.5.3 の考え方: 本文は `font-weight 400 / bold_mode 時 600`（`_css:5090`）。
  要求は「少し太い」なので本文は **600 固定**にする（`bold_mode` の設定は残すが無効化しない。
  `body.bold-mode` の条件は外す）。
- UI 全体: `html, body` に `font-weight: 600` を入れ、継承で全体が太くなり、ボタンは
  従来どおり 700。
- エディタ: `font-weight: 600`（1.5.3 の `fw_editor=600` 時と同値）。
- 検証: 画素で文字が太くなっていること、`bold_mode` の設定切り替えでも レイアウトが
  崩れないこと（行高不変のため）。

## 3. アイコン — 主流の squircle に作り直す

- 現状: 512x512 フルブリード四角（角が不透明黒、図柄が 94% 幅）。macOS の丸角標準と外れる。
- 主流の作り方: 1024x1024 キャンバス ／ squircle（角半径 ≈ 22.37%）マスク ／
  図柄はセーフゾーン内（約 83%）に収める ／ 透過部分は角だけ。
- 生成: Python + Pillow で 1024 画像（四角クリップ＋スーパー楕円マスク `|x/a|^n+|y/b|^n<=1`,
  n≈4.5）を作り、既存図柄を 848px に縮小して中央配置。`iconutil` で `.iconset` → `icon.icns`。
- 置き場所: `apps/desktop/icons/icon.png`（1024）＋ `icon.icns` を上書き。
  `tauri.conf.json` は icns のみ参照で変更不要。
- 検証: 角 4 隅が透過（alpha 0）、`sips` で 1024x1024、`file` で icns。

## 4. 説明MD — 1.5.3 の内容を表示

- 1.5.3 は `資料箱/sample_{ja,en,de,fr,zh}.md` を読み取り専用で開く。ファイルが無い場合は
  `_set_sample()` の埋め込み文面で代替する（`main_v1.5.3.py:7681`）。
- 本リポジトリに `資料箱/sample_*.md` は無いため、**埋め込み文面をそのまま転用**する
  （`_set_sample` の ja 文面を `GUIDE_JA` に置き換える。5 言語あるが UI 言語で切り替え済み
  のため ja を中心に、現行の `loadI18n` 仕組みと合わせて他言語は簡易に残す）。
- 起動ダイアログを閉じたら説明が出るようにする:
  - `wireStartup` の `cancel`（Esc / ×）ハンドラは現状 `newDocument()`（空の TXT 編集）で
    何も開かない。→ `guide()` に変更する（閲覧モードで説明を表示）。
  - これで「ファイルを開くで何も開かなかった時」に説明が出る。
- 検証: `--dialog` 相当で起動し、Esc で説明文面が表示されること。

## 5. 表の列/行プラスボタン — 1.5.3 の `_mdvSetupTableBtns` を移植

- 1.5.3 `main_v1.5.3.py:5029-5082`: MD 編集時に各 `table` の直後に
  `.mdv-table-ctrl`（`contenteditable=false`）を挿入し、`+ 列` / `+ 行` ボタンを出す。
  `+ 列` は `thead` なら `th`、他は `td` を全行に足し、`+ 行` は `tbody` 末尾に
  同列数の行を足す。ボタンは青い輪郭（`rgba(74,158,255,.5)`・11px 太字）。
- 移植:
  - `ui/js/app.js` に `setupTableBtns()` を追加し、`enhance()`（描画直後）で
    MD 編集モードのときだけ呼ぶ（`state.mode === "md"`）。
  - `ui/css/app.css` に `.mdv-table-ctrl` のスタイルを追加（ラッパー側では
    インライン style を使う 1.5.3 と同じく、ボタンの見た目は CSS に集約してよいが
    色・サイズは同じ）。
  - **往復変換の漏れ対策**: `commitMdEdits` で Turndown に渡す前に
    `.mdv-table-ctrl` を取り除く（クローンで除去）。1.5.3 も保存/書き出しで除去する
    （`:1527, :6194`）。
  - ボタン押下で DOM が変わったとき、`commitMdEdits` の dirty 判定に乗るよう
    `markDirty` + 対象ブロックの dirty を立てる（現状 `applyFormatMd` の table は
    `markDirty` のみでブロック dirty が立たず保存されない既知の落とし穴があるため、
    同じ経路で修正）。
- 検証: MD 編集で表を持つ文書を開き、`+ 列` を押すと列が増え、`commitMdEdits`
  後に Markdown の表に新しい列が反映されること。保存後もボタン文言が混入しないこと。

## 6. 目次 — 閲覧モードで出ない問題の修正

- 原因（実証済み）: `updateTocVisibility`（`app.js:335`）
  `show = show_toc && (mode !== "view" || tocPinned)`。冷起動では
  `boot` が `tocPinned=false` にし、`setMode("view")` するため、設定が
  `show_toc: true` でも閲覧では常に隠れる。MD/TXT 編集では出るので報告と一致する。
- 修正: `tocPinned` の条件を削除し、`show = !!settings.show_toc` に一本化。
  ボタンの切り替えは設定値のトグルだけで済む（1 回のクリックで出入する）。
  `applySettings` 経由で `updateTocVisibility()` も呼ぶ（`refreshBootstrap` 後に
  パネルの表示がずれない）。
- 検証: 冷起動 → 閲覧モードで目次が出ること。目次のボタン 1 回で隠れる／出ること。
  MD 編集でも出ること。開いている文書に `<h1>` 生 HTML しか無い場合でも
  クリックでジャンプできること（raw HTML 見出しの id 付与は render 側で対応済みか確認）。

## 7. 公開

- `Cargo.toml` / `apps/desktop/tauri.conf.json` の version を `26.3.0-beta.3.0` に。
- セルフテストで `bootLabel=β3.0`、DMG を作り、GitHub Release `v26.3.0-beta.3.0`
  （prerelease）を公開。公開ブランチと README も更新。private memo 更新。

## 停止条件

- スクショ 6 枚（閲覧/MD/TXT/A4/ライト/起動）で色・太さ・目次の目視確認
- セルフテスト `ok: true`、`mdEditChanged: true`、PDF が出ること
- 表ボタンの往復テストが通ること
- 失敗時はコミットせず、直前のコミット（`4e698bf`）に戻す
