# Release Notes / 更新履歴

## v1.4.7

### 日本語

- MD編集でリンク・画像が挿入できるようになりました。ツールバーの「リンク」「画像」ボタンがURL入力ダイアログを開き、選択中の文字列をリンク文言にして挿入します。URLや `[文言](URL)` 形式の貼り付けもリンクとして貼り付けられ、危険なスキーム（javascript: 等）は除外されます。
- PDF書き出しの形式崩れを改善しました。印刷は表示とは別の専用ページで行うため、書き出し中に画面のスクロールやカーソル位置が失われなくなりました。表・コード・図・数式がページの境目で切断されにくく、画面の配色がPDFにも反映されます。
- 閲覧・MD編集・TXT編集のプレビューで、右側の広い空白と意図しない横スクロールが出ないよう、文書の表示範囲に収まる表示にしました。長いURLや広い表も折り返して表示されます。
- 回帰テストは計989件（純粋関数506・Qt401・WebEngine統合82）ですべて成功しました。

### 初回起動について（v1.4.7 の配布物）

本アプリはad-hoc署名・未公証のため、「"MDViewerPro"は壊れているため開けません。」と
表示されることがありますが、アプリ自体は壊れていません。MDViewerPro.app を
Applications フォルダへ入れ、ターミナルで `xattr -cr /Applications/MDViewerPro.app`
を実行してから開いてください。DMG 内の `FIRST_LAUNCH.txt` に同じ手順（日英）を
入れています。詳しくは README の「初回起動について」をご覧ください。

実際にMD編集で変更した複雑なMarkdownはHTMLからの逆変換で表記が変わることがあります。厳密な原文編集にはTXT編集を使用してください。

### English

- Links and images can now be inserted in MD Edit. The toolbar's Link and Image buttons open a URL dialog and insert the selected text as the link label. Pasting a URL or `[label](URL)` now pastes as a link, and dangerous schemes (such as javascript:) are rejected.
- PDF export layout is improved. Printing now uses a dedicated off-screen page, so the on-screen scroll position and cursor are no longer disturbed during export. Tables, code blocks, figures, and math are kept from splitting across page breaks, and on-screen colors carry over to the PDF.
- View, MD Edit, and TXT Edit previews no longer show a wide blank area on the right or allow accidental horizontal scrolling; content now fits within the document display range. Long URLs and wide tables wrap instead of overflowing.
- All 989 regression tests pass (506 pure functions, 401 Qt, 82 WebEngine integration).

### First launch (v1.4.7 distribution)

This app is ad-hoc signed and not notarized, so macOS may say "MDViewerPro" is damaged
and can't be opened. The app itself is not damaged. Put MDViewerPro.app into the
Applications folder, run `xattr -cr /Applications/MDViewerPro.app` in Terminal, then
open it. The DMG contains `FIRST_LAUNCH.txt` with the same steps (Japanese and English).
See "First Launch" in the README for details.

Complex Markdown can still change formatting after an actual visual edit. Use TXT Edit for exact source editing.

This macOS build is ad-hoc signed and not notarized. First launch may require approval in System Settings → Privacy & Security.

## v1.4.6

### 日本語

- 未編集のMD編集モードから保存・画面切替をしても、Setext見出し、エスケープ、末尾の空行を含む元のMarkdownをそのまま保持します。
- WebEngineから編集内容を取得できない場合は、古い内容での保存・書き出しや文書を閉じる操作を中止し、再試行できるよう警告します。
- 編集直後の入力を保存する既存の動作を維持し、追加のWebEngine統合テストで成功・失敗両経路を検証しました。
- MD編集で実際に内容を変更した場合のHTML→Markdown変換は、複雑な構文を完全には往復できません。原文の細部を維持したい編集にはTXT編集を使用してください。

### English

- Saving or leaving MD Edit without making changes now preserves the original Markdown, including Setext headings, escapes, and trailing blank lines.
- If WebEngine cannot capture an edit, saving, exporting, and closing are stopped with a retryable warning instead of writing stale content.
- Existing immediate-save behavior remains covered, with additional real-WebEngine regression tests for success and failure paths.
- Actual visual edits still use a lossy HTML-to-Markdown conversion for complex syntax. Use TXT Edit when exact source formatting matters.

This macOS build is ad-hoc signed and not notarized. First launch may require approval in System Settings → Privacy & Security.

## v1.4.5

入力した改行とコードの中身が、保存・再読込の往復で失われる問題を直した
リリースです。

### 日本語

#### 修正

- **コードブロック内の空行が保存のたびに詰まる問題**: コードブロックの中に
  入れた連続した空行が、保存 → 開き直しを繰り返すたびに 1 行に詰まって
  いました。MD編集モードでは画面の内容を Markdown に戻して保存するため、
  その逆変換のときに段落間の空行を整える処理がコードの中まで効いていたのが
  原因です。コードの中身（フェンス内・インラインコード）は整形の対象外とし、
  空行・行頭インデントともに入力したとおりに保存されるようにしました。
- **改行設定が「オフ」のとき、明示的な改行が消える問題**: 詳細設定で
  「改行をそのまま改行として表示する」をオフにしていると、行末に半角
  スペース 2 個を置いて入れた改行が MD編集の保存で失われていました。
  設定に合わせて、オフ時は行末スペース 2 個として復元するようにしました
  （オン時は従来どおり改行として復元されます）。
- **保存中のエラーで既存ファイルが失われる恐れがあった問題**: 保存は
  直接ファイルを上書きする書き方だったため、書込みの途中でエラーが起きると
  それまでの内容が失われる恐れがありました。一時ファイルへ書いたうえで
  置き換える方式（原子的置換）に変え、書込みに失敗したときは既存の
  ファイルと「未保存」の状態を保つようにしました。
- **読み取れないファイルを開くと内容が空の文書になる問題**: アクセス権が
  ないファイルなどを開いたとき、警告のあとに現在の文書が空に置き換わる
  場合がありました。読み取りに失敗したときは、いま開いている文書を
  そのまま維持するようにしました。
- **MD編集の取り込みがタイムアウトしたときの挙動**: 画面からの取り込みが
  時間切れになった場合に、直前の内容を壊す恐れがあったため、取り込みに
  失敗したときは現在の内容を維持して保存するようにしました。

---

### English

#### Fixes

- **Blank lines inside code blocks collapsed on every save**: consecutive blank
  lines inside a fenced code block were collapsed into one each time the file
  went through MD Edit and a save. The HTML → Markdown converter normalised
  paragraph boundaries over the whole document, including code content. Code
  (fenced or inline) is now exempt from that normalisation, so blank lines and
  indentation are preserved exactly as entered.
- **Explicit line breaks lost when hard breaks are off**: with "Render a single
  newline as a line break" turned off in Settings, a line break written as two
  trailing spaces was dropped when saving from MD Edit. The converter now
  restores two trailing spaces when the setting is off (and a plain newline
  when it is on, as before).
- **A failed save could destroy the existing file**: saving wrote directly over
  the target file, so an error mid-write could leave the previous content lost.
  Saving now writes to a temporary file in the same folder and replaces the
  target atomically; on failure the old file and the unsaved state are kept.
- **Opening an unreadable file replaced the current document with an empty one**:
  when a file could not be read (e.g. permission denied), the current document
  could be blanked after the warning. The current document is now preserved.
- **Behaviour when MD Edit capture times out**: a timed-out capture no longer
  risks clobbering the current content; the existing content is kept.

---

## v1.4.4

Mermaid ダイアグラムの表示に対応したリリースです。

### 日本語

#### 新機能

- **Mermaid ダイアグラムに対応**: ` ```mermaid ` フェンスに書いたフローチャート・
  シーケンス図・グラフなどを、閲覧モード・TXT編集のプレビュー・PDF / HTML 書き出しで
  図として描画するようにしました。mermaid.js をアプリに完全同梱しており、
  ネットワーク接続は一切不要です。ダーク / ライトなど選択中のテーマに合わせて
  配色が自動的に変わります。MD編集モードでは他の言語のコードブロックと同様、
  フェンスをそのまま直接編集できます（保存しても記法は壊れません）。

---

### English

#### New features

- **Mermaid diagram support**: flowcharts, sequence diagrams, graphs and other
  diagrams written in a ` ```mermaid ` fence are now rendered as figures in View
  mode, the TXT Edit preview, and PDF / HTML export. mermaid.js is bundled
  entirely with the app, so no network connection is required at all. Colours
  follow the currently selected theme (dark, light, etc.) automatically. In MD
  Edit, the fence is edited directly like any other language's code block, and
  survives a save unchanged.

---

## v1.4.3

表示の細かい不具合を直し、対応言語に中国語を追加したリリースです。

### 日本語

#### 新機能

- **中国語（简体中文）に対応**: 詳細設定と起動画面の言語に「简体中文」を
  追加しました。ツールバー・メニュー・各種ダイアログ・使用ガイド・
  新規作成時のサンプル文書まで中国語で表示されます。
  これで日本語 / English / Deutsch / Français / 简体中文 の 5 言語になります。

#### 修正

- **言語や文字サイズを変えると、編集中の改行や見出しが消える問題**:
  MD編集モードでは画面がそのまま編集領域のため、表示設定を変えると
  画面を作り直す必要があります。このとき、まだ内部に取り込まれていない
  直前の編集（Enter で入れた改行や、H1 / H2 にした見出し）が
  作り直しで失われていました。描き直す前に必ず編集内容を取り込むように
  しました。言語・文字サイズのほか、テーマ・フォント・目次の表示切替・
  レイアウト変更（フリー / A4文書 / B5文書）・余白設定でも同じ問題が
  起きていましたが、まとめて直っています。
- **水平線が細すぎて見えない問題**: `---` で入れる水平線が 1px で背景に
  溶けてしまい、特にダークモードではほとんど見えませんでした。太さを
  4 倍にし、色のコントラストも少し上げて、はっきり見えるようにしました。
  テーマごとの雰囲気は保つよう、線の色はテーマの枠線色と淡色テキストの
  中間から決めています。プラグインテーマにもそのまま反映されます。

---

### English

#### New features

- **Chinese (简体中文) support**: "简体中文" is now available in Settings and on
  the startup screen. The toolbar, menus, dialogs, the built-in guide and the
  sample document for new files are all translated. That makes five UI languages:
  日本語 / English / Deutsch / Français / 简体中文.

#### Fixes

- **Changing the language or text size wiped out line breaks and headings you had
  just typed**: in MD Edit the page itself is the editing surface, so changing a
  display setting has to rebuild it. Edits that had not yet been captured — a line
  break from Enter, or a line just turned into H1 / H2 — were lost in that rebuild.
  The content is now captured before redrawing. The same problem affected theme and
  font changes, toggling the TOC, switching layout (Free / A4 / B5) and changing
  margins; all are fixed together.
- **Horizontal rules were too thin to see**: a `---` rule was drawn as a 1px line
  that blended into the background, and was nearly invisible in dark mode. It is now
  four times thicker with slightly more contrast. The colour is derived from the
  theme's border and dim-text colours, so each theme keeps its own character and
  plugin themes benefit as well.

---

## v1.4.2

書き心地まわりの不具合をまとめて直したリリースです。
あわせて LaTeX の体裁コマンド（`\newpage` 等）に対応しました。

### 日本語

#### 新機能

- **LaTeX の体裁コマンド（`\newpage` 等）に対応**: `\newpage` のように文書の体裁を
  指示するコマンドを、文字列として表示するのをやめ、指示として解釈して表示に
  反映するようにしました。
  - **改ページ** (`\newpage` / `\pagebreak` / `\clearpage` / `\cleardoublepage`):
    PDF 書き出しでは実際にそこでページが分かれます（A4文書 / B5文書 / フリーの
    いずれでも）。A4文書 / B5文書の表示では次のページの先頭まで送られ、
    ページ区切り線が入ります。フリー表示ではページの概念がないため何も表示しません。
  - **縦の空き** (`\vspace{1cm}` / `\bigskip` / `\medskip` / `\smallskip`):
    指定された分の空きを入れます。
  - **改行・段落** (`\newline` / `\linebreak` / `\par`): 指示どおりに改行します。
  - **体裁のみのコマンド** (`\noindent` / `\centering` / `\raggedright` 等):
    表示には反映できないため、隠すだけにします。
  - MD編集モードでは、場所が分かるように破線とコマンド名を薄く表示します
    （削除・移動できます）。開いて保存しても元の記述はそのまま残ります。
  - コードブロック / インラインコード / 数式の中のコマンドは対象外です。説明として
    `` `\newpage` `` と書いたものが消えることはありません。対応していない
    コマンドも消さずにそのまま表示します。

#### 修正

- **改行が無視される問題**: 文章を書いて改行しても、閲覧モードでは前の行に
  つながって表示されていました。空行を入れないと改行できない状態で、v1.4.1 で
  編集して保存した文書を開き直すと、書いたはずの改行が消えてしまっていました。
  Enter で入れた改行をそのまま改行として表示するようにしました。
  行の途中の折り返しではなく、書いた行のとおりに表示されます。
  コードブロック・表の中は今までどおりで、変わりません。
  素の Markdown の挙動が必要な場合は、詳細設定の「改行の扱い」でオフに
  できます（既定はオン）。
- **HTML / PDF に書き出すと改行が消える問題**: 上と同じ原因です。書き出しは
  閲覧モードと同じ描画を使っているため、こちらも一緒に直っています。
  画面で見えているとおりに書き出されます。
- **見出しで改行すると次の行も見出しになる問題**（MD編集）: H1 / H2 / H3 に
  した行で Enter を押すと、続きの行まで見出しの書式のままになり、本文に
  戻せなくなることがありました。見出しの行で改行したときは、新しくできる行を
  必ず本文にするようにしました。行末・行の途中・行頭のどこで改行しても同じです。
  中身が空の見出しで Enter を押した場合は、その行自体が本文に戻ります。
- **見出しにした直後に「本文」を押しても戻らない問題**: 何も入力していない行を
  H1 / H2 / H3 にしてから、そのまま「本文」を押しても書式が戻りませんでした。
  - MD編集: 空の見出しや、ツールバーを押してカーソルの選択が外れた状態でも
    確実に本文へ戻るようにしました。
  - TXT編集: 見出しボタンが行頭の記号を「足すだけ」だったため、H1 のあと H2 を
    押すと `## # 本文` のように記号が積み重なり、「本文」を押しても 1 段しか
    外れませんでした。見出し・引用・箇条書き・番号付きのボタンは、いま付いている
    書式を「置き換える」ようにし、「本文」はすべての記号を一度に外すようにしました。
    同じ書式のボタンをもう一度押すと本文に戻ります。
    過去のバージョンで記号が積み重なってしまった行も、「本文」を一度押せば戻ります。
- **MD編集で Enter を押して入れた空行が、保存すると消える問題**: 段落と段落の間を
  もう少し空けようと Enter を押しても、保存して開き直すと元に戻っていました。
  空行は Markdown の仕様上そのままでは表現できない（連続した空行は無視される）ため、
  空行を表す `<br>` の行として保存するようにしました。開き直しても同じ空行が残り、
  編集と保存を繰り返しても増えたり減ったりしません。
  ※ このためファイルの中に `<br>` という行が入ります。
- **MD編集で入力した直後に保存すると、その編集が保存されない問題**: MD編集モードの
  内容は、入力が途切れてから少し遅れて内部に取り込まれる作りになっていました。
  そのため、文字を打ってすぐに保存すると直前の編集がファイルに入らず、
  **Enter で入れた改行ごと消えて**しまい、開き直すと改行されていない状態に
  なっていました。保存・PDF / HTML 書き出しの直前に必ず取り込むようにしました。
  あわせて、入力した直後にウィンドウを閉じると「変更あり」と判定されず、
  確認も出ないまま編集が捨てられていた問題も直しました。
- **改行の扱いを詳細設定で切り替えられるようにしました**: 詳細設定に「改行の扱い」を
  追加しました。既定はオン（書いたとおりに改行する）で、オフにすると素の Markdown
  仕様どおりの表示に戻せます。設定は次回起動時にも引き継がれます。

#### あわせて直したもの

- **MD編集で開くと引用が本文になってしまう問題**: 引用を含む文書を MD編集モードで
  開いて保存すると、2 行目以降の `>` が失われて引用が崩れていました。
- **MD編集で開くたびに箇条書きの行間が広がる問題**: 項目の間に空行が入り、
  編集を繰り返すうちに箇条書きが崩れていました。入れ子の箇条書きの階層も
  保たれるようにしました。
- **TXT編集で、折り返した長い行の途中に書式記号が入る問題**: 画面の折り返し位置を
  行頭と見なしていたため、長い行では `#` が行の途中に入ってしまうことがありました。

---

### English

#### New features

- **LaTeX layout commands such as `\newpage`**: commands that describe document
  layout are no longer printed as literal text — they are interpreted and applied
  to the rendering.
  - **Page breaks** (`\newpage` / `\pagebreak` / `\clearpage` /
    `\cleardoublepage`): PDF export produces a real page break (in A4 Document,
    B5 Document and Free alike). In A4 / B5 Document view the content is pushed to
    the top of the next page and a page separator is drawn. Free view shows
    nothing, since it has no pages.
  - **Vertical space** (`\vspace{1cm}` / `\bigskip` / `\medskip` /
    `\smallskip`): inserts the requested amount of space.
  - **Line and paragraph breaks** (`\newline` / `\linebreak` / `\par`): break
    as instructed.
  - **Layout-only commands** (`\noindent` / `\centering` / `\raggedright`, …):
    cannot be reflected in the rendering, so they are simply hidden.
  - MD Edit shows a faint dashed marker with the command name so you can find,
    move or delete it. Opening and saving keeps the original text intact.
  - Commands inside code blocks, code spans and math are left alone, so writing
    `` `\newpage` `` as an example never disappears. Unsupported commands are
    still shown verbatim.

#### Fixes

- **Line breaks were ignored**: pressing Enter did not produce a line break in
  View mode — the next line was joined onto the previous one, and a blank line was
  the only way to break text. Documents written and saved with v1.4.1 lost their
  line breaks when reopened. Line breaks you type are now rendered as line breaks.
  Code blocks and tables are unaffected. If you need standard Markdown behaviour,
  turn it off under Settings → Line Breaks (on by default).
- **HTML / PDF export dropped line breaks**: same root cause — export uses the same
  rendering as View mode, so it is fixed as well. Exports now match what you see.
- **Pressing Enter in a heading kept the heading format** (MD Edit): after making a
  line H1 / H2 / H3, the following line stayed a heading and could not be turned
  back into body text. A line created by pressing Enter inside a heading is now
  always body text, whether the caret is at the end, in the middle, or at the start.
  Pressing Enter in an empty heading turns that line back into body text.
- **The Body button did nothing right after applying a heading**: applying H1 / H2 /
  H3 to a line and pressing Body without typing anything left the format in place.
  - MD Edit: now works reliably for empty headings and when the selection has been
    lost because focus moved to the toolbar.
  - TXT Edit: heading buttons only ever *prepended* their marker, so H1 followed by
    H2 produced `## # text` and Body stripped just one level. Heading, quote, list
    and numbered-list buttons now *replace* the current block format, and Body
    removes every marker at once. Pressing the same format button again returns the
    line to body text. Lines that accumulated markers in earlier versions are fixed
    by a single press of Body.
- **Blank lines added with Enter in MD Edit disappeared on save**: pressing Enter to
  put more space between paragraphs had no effect once the file was saved and
  reopened. A blank line cannot be expressed in plain Markdown (consecutive blank
  lines are ignored), so it is now written as a `<br>` line. The blank line survives
  reopening and does not grow or shrink across repeated edits. Note that this puts a
  literal `<br>` line into the file.
- **Edits made just before saving were lost in MD Edit**: MD Edit content was only
  picked up a moment after you stopped typing. Saving right after typing therefore
  wrote the file without your most recent edits — **including the line breaks you
  had just entered** — so reopening the file showed no break. The content is now
  captured synchronously before saving and before PDF / HTML export. Closing the
  window right after typing also failed to register as "modified" and discarded
  the edits without asking; that is fixed too.
- **A setting to choose how line breaks are handled**: Settings now has a
  "Line Breaks" section. It is on by default (render what you typed); turning it
  off restores standard Markdown rendering. The choice is remembered.

#### Also fixed

- **Blockquotes were flattened into body text** when a document was opened in MD Edit
  and saved: the `>` marker was lost from every line after the first.
- **Bulleted lists grew looser on every MD Edit round trip**, eventually breaking
  apart. Nested list levels are now preserved too.
- **TXT Edit inserted format markers mid-line on long wrapped lines**, because the
  visual wrap position was treated as the start of the line.

---

## v1.4.1

### 日本語

#### 新機能

- **LaTeX 数式の表示に対応**: 本文中の `$…$`（インライン）と `$$…$$`（別行立て）、
  および `\(…\)` / `\[…\]` を数式として組版し、Computer Modern 系のセリフ体で
  表示するようにしました。分数・根号・上下付き・総和/積分などの大型演算子・
  伸縮する括弧・行列（`pmatrix` / `bmatrix` / `vmatrix` / `cases` / `aligned`）・
  `\mathbb` などの書体・アクセント記号・多数のギリシャ文字と数学記号に対応します。
  組版はアプリ内部で完結しており、外部ライブラリのインストールもネットワーク接続も
  必要ありません。PDF / HTML 書き出しにもそのまま反映されます。
  コードブロックやインラインコードの中の `$`、および `$5 と $10` のような
  通貨表記は数式として扱いません。未対応のコマンドは消さずにそのまま表示するため、
  書いた内容が失われることはありません。
- **YAML に対応**: 文書の先頭を `---` で囲んだ YAML フロントマターを、本文とは別の
  メタ情報パネルとして表示するようにしました。また `.yml` / `.yaml` ファイルを
  開けるようになり、YAML として構文強調表示します（この場合 MD編集は使えません。
  TXT編集で編集してください）。
- **フォントを選べるようにしました**: 詳細設定のフォント欄を、推奨フォント・
  追加したフォント・システムフォントの 3 つに分けて選べるようにしました。
  推奨フォントには IPAmj明朝 と Source Han Serif を加えています
  （未インストールのものは「（未インストール）」と表示されます）。
  「フォントを追加...」から TTF / OTF / TTC ファイルを取り込むと
  `~/.mdviewer/fonts/` に保存され、次回起動以降も使えます。自分で追加した
  フォントは「選択中のフォントを削除」で取り除けます（システムに元から入っている
  フォントは削除されません）。フォントの変更は再起動しなくても UI 全体に反映されます。

#### 修正

- **モードを切り替えるとスクロール位置が先頭に戻る問題**: 閲覧モードから MD編集 /
  TXT編集へ切り替えると、今読んでいた場所ではなく必ず文書の先頭が表示されて
  いました。切替時に「画面最上部に見えているブロックとその中の位置」を記録し、
  切替先で同じ位置を復元するようにしました。閲覧 ⇔ MD編集 ⇔ TXT編集 の
  どの向きの切り替えでも位置を引き継ぎます。
- **目次を標準でオンにしました**: 既定でオフだったため、目次機能があること自体に
  気づきにくい状態でした。初回起動から目次が開いた状態になります。
  オン / オフの状態は次回起動時にも引き継がれます。
- **ウィンドウを狭くするとボタンの文字が枠からはみ出す問題**: ウィンドウ幅に応じた
  一律の文字サイズだったため、「戻る」は余裕があるのに「PDF書き出し」は溢れる、
  という状態になっていました。ボタンごとに実際の文字幅を測り、枠に収まらない
  ボタンだけ文字をさらに小さくするようにしました。あわせて、狭い幅では
  ツールバー全体がウィンドウ幅を超えてしまい文字が切れていた問題も修正し、
  最小ウィンドウ幅 (480px) でもすべてのボタンが収まるようにしています。
- **フロントマターが目次に紛れ込む問題**: `---` で囲んだ YAML の閉じ行を
  下線形式の見出しと誤検出し、直前の `key: value` 行が目次に現れていました。
- **字下げコードブロック内の行が目次に紛れ込む問題**: 4スペース(またはタブ)で
  字下げして書いたコードブロックを本文として扱っていたため、その中の `#` 行や
  `---` の行が見出しとして目次に現れていました。あわせて、その取りこぼしが原因で
  目次のジャンプ先がずれることもありました。

---

### English

#### New features

- **LaTeX math rendering**: `$…$` (inline) and `$$…$$` (display), as well as `\(…\)` /
  `\[…\]`, are now typeset as formulas in a Computer Modern style serif face.
  Supported notation includes fractions, radicals, sub/superscripts, big operators
  (`\sum`, `\int`, …), auto-stretching delimiters, matrix environments
  (`pmatrix` / `bmatrix` / `vmatrix` / `cases` / `aligned`), styles such as
  `\mathbb`, accents, and a large set of Greek letters and mathematical symbols.
  Typesetting happens entirely inside the app — no extra library to install and no
  network access — and it carries over to PDF/HTML export. A `$` inside a code block
  or code span is never treated as math, and currency such as `$5 and $10` is left
  alone. Unsupported commands are shown verbatim rather than dropped, so nothing you
  wrote is lost.
- **YAML support**: a `---` delimited YAML front matter block at the top of a document
  is now shown as a separate metadata panel instead of leaking into the body. `.yml`
  and `.yaml` files can also be opened and are shown with YAML syntax highlighting
  (MD Edit is unavailable for these; use TXT Edit).
- **Font selection**: the font setting is now split into recommended fonts, fonts you
  added, and system fonts. IPAmj Mincho and Source Han Serif were added as recommended
  fonts (shown as "(not installed)" when unavailable). "Add Font..." imports a
  TTF / OTF / TTC file into `~/.mdviewer/fonts/` so it stays available on later
  launches, and "Remove selected font" removes fonts you added (fonts installed on the
  system are never touched). Font changes now apply to the whole UI without a restart.

#### Fixes

- **Switching modes jumped back to the top**: going from View to MD Edit or TXT Edit
  always showed the beginning of the document instead of where you were reading. The
  app now records the block visible at the top of the viewport (and the position within
  it) and restores it in the target mode, in every direction between View, MD Edit and
  TXT Edit.
- **The TOC is now on by default**: it used to be off, which made the feature easy to
  miss entirely. It is open from the first launch, and your on/off choice is remembered.
- **Button labels overflowed their buttons on narrow windows**: font size followed only
  the window width, so "Back" had room to spare while "Export PDF" spilled out of its
  button. Each button now measures its own label and shrinks only if it does not fit.
  A related issue where the whole toolbar exceeded the window width (clipping labels)
  was fixed too — every button now fits at the 480px minimum window width.
- **Front matter leaked into the TOC**: the closing `---` of a YAML block was detected
  as a Setext (underlined) heading, so the preceding `key: value` line appeared in the
  headings list.
- **Indented code blocks leaked into the TOC**: code blocks written with a 4-space (or
  tab) indent were treated as body text, so `#` lines and `---` lines inside them showed
  up as headings — which could also make TOC entries jump to the wrong place.

---

## v1.4.0

### 日本語

#### 新機能

- **起動速度の改善**: アプリ起動時にウィンドウがすぐ表示されるよう改善しました。従来はプレビュー用の
  WebEngine（重い初期化処理）をウィンドウ表示前に生成していたため起動が遅く感じられましたが、
  ウィンドウ表示後にバックグラウンドで初期化するよう変更し、体感速度を大幅に改善しました。
- **見出し(目次)パネルを追加**: MD編集・TXT編集モードで、左側に見出し一覧パネルを表示できるように
  なりました。H1〜H6を検出して一覧表示し、クリックするとその見出しの位置までジャンプします。
  ウィンドウを横に広げるとパネル幅も追従して広がります(220〜420px)。
- **TXT編集モードのプレビュー同期**: TXT編集中、カーソルがある行が右側のプレビューに表示されて
  いない場合は自動的にスクロールし、対応する箇所を薄い赤色でハイライト表示します。

#### 修正

- **見出し(目次)の検出漏れとジャンプ先のズレ**: 目次が「`#` の後にスペースがない見出し」
  「下線形式(Setext)の見出し」「閉じられていないコードフェンス以降の見出し」を検出できず
  一覧から漏れていました。さらにその取りこぼしが原因で、MD編集モードで目次の項目をクリックすると
  別の見出しにジャンプしてしまう不具合がありました。見出しの判定を Markdown の実際の描画結果と
  一致するよう作り直し、解消しています。
- **目次の文字が小さすぎる問題**: 閲覧モードの目次は最小9px・最大14pxと極端に小さく表示されて
  いました。閲覧モードとMD/TXT編集モードで基準を統一し、常に読みやすい大きさ(16px以上)に
  なるようにしました。
- **MD編集中に目次が更新されない問題**: MD編集モードで見出しを追加・削除しても目次一覧が
  古いままでした。編集内容に追従して更新されるようにしています(内容に変化がないときは
  作り直さないため、ちらつきません)。
- **ウィンドウのリサイズで分割位置がリセットされる問題**: エディタとプレビューの境界を手動で
  ドラッグして調整しても、ウィンドウの大きさを変えるたびに初期状態へ戻ってしまいました。
  リサイズ時は目次の幅だけを調整し、手動で決めた比率は保つようにしました。あわせて、
  レイアウト確定前に目次の幅が過大に計算されることがある問題も修正しています。
- **MD編集モードのリスト書式の不具合**: 番号付き/箇条書きリストの直後に意図しない空行ができる、
  番号が「1.」から増えていかない、一度付けた番号や箇条書きを解除できない、リスト項目内で
  「本文」ボタンを押しても書式が本文に戻らない、といった不具合はすべて同じ原因(リスト操作時に
  ブラウザ側が生成する不正なHTMLの入れ子構造)によるものでした。編集後のHTML構造を自動的に
  修復する処理を追加して解消しています。TXT編集モードの「番号」ボタンも、常に「1.」を挿入する
  だけだった実装を、直前の行を見て連番にする・既存の番号を解除できるように修正しました。
- **左側の空白パネル**: 閲覧モード・MD編集モードで、左端から何もない空白パネルがドラッグで
  引き出せてしまう不具合を修正しました。
- **多言語UIの翻訳漏れ**: 日本語・English・Deutsch・Français のすべてで、UI文字列の翻訳漏れ
  (目次パネルのタイトル、テーブル挿入時の初期セル文字列、設定画面の「言語」ラベルなど)を
  修正しました。あわせて、A4/B5文書のページ区切りラベルが日本語では
  「page_label_prefix2 ページ目」のような未翻訳のキー名を含んで表示され、英語・ドイツ語・
  フランス語では日本語が混ざって表示される不具合も修正しています。
- **Markdownの改行・段落の扱い**: MD編集モードで編集・保存したファイルを再度開いた際に、段落の
  空行が詰まって表示されたり改行が無効になったりする不具合を修正しました。行間の解釈を
  Markdown本来の仕様(空行で段落区切り、行末の強制改行以外は単一の改行で改行しない)に
  合わせています。

---

### English

#### New features

- **Faster startup**: The app window now appears immediately on launch. Previously, the
  preview's WebEngine (an expensive initialization step) was created before the window was
  shown, making startup feel slow. It is now initialized in the background after the window
  appears, significantly improving perceived startup speed.
- **Added a headings (TOC) panel**: In MD Edit and TXT Edit modes, a headings panel can be
  shown on the left. It lists H1–H6 headings, and clicking one jumps to that location. The
  panel also widens along with the window (220–420px).
- **Preview sync in TXT Edit mode**: While editing in TXT mode, if the line you're typing on
  is not visible in the preview pane, it auto-scrolls into view and the corresponding block
  is highlighted in a light red.

#### Fixes

- **Missing headings and wrong-target jumps in the TOC**: The headings list silently missed
  ATX headings with no space after `#`, Setext-style (underlined) headings, and any heading
  following an unterminated code fence. That gap also made clicking a TOC entry in MD Edit
  mode jump to the wrong heading. Heading detection was rewritten to match what Markdown
  actually renders.
- **TOC text too small**: In View mode the TOC was rendered at 9–14px. View mode and
  MD/TXT Edit modes now share one sizing rule and never go below 16px.
- **TOC not updating while editing in MD mode**: Adding or removing a heading in MD Edit mode
  left the TOC list stale. It now follows the edits (and is left untouched when nothing
  changed, so it doesn't flicker).
- **Window resize reset the split position**: Manually dragging the editor/preview divider was
  undone every time the window was resized. Resizing now only adjusts the TOC width and keeps
  the ratio you set. A related issue where the TOC could be sized far too wide before layout
  settled was also fixed.
- **List formatting bugs in MD Edit mode**: an unwanted blank line after a list, numbered lists
  stuck at "1." instead of incrementing, being unable to remove numbering/bullets once applied,
  and the "Body" button not switching back to plain text inside a list item — all traced to the
  same cause (invalid nested HTML the browser produces around lists during editing). Editable
  content is now repaired automatically after list operations. The TXT Edit "Num." button — which
  previously just inserted a literal "1." — now increments from the previous line and toggles off.
- **Blank draggable panel on the left**: In View and MD Edit modes, an empty panel could be
  dragged open from the left edge with no functionality. Fixed.
- **Multi-language UI gaps**: Fixed untranslated UI strings across Japanese, English, Deutsch and
  Français (TOC panel title, default table cell text, the "Language" label in Settings, and more).
  Also fixed the A4/B5 page-break label, which could show a raw key name in Japanese
  (e.g. "page_label_prefix2 ページ目") and leak Japanese text into the English/German/French label.
- **Markdown line-break/paragraph handling**: Fixed an issue where re-opening a file edited and
  saved in MD Edit mode could show paragraph spacing collapsed or line breaks lost. Line and
  paragraph handling now follows standard Markdown semantics (blank line = new paragraph; a
  single line break does not force a visual break).

---

## v1.3.0 – v1.3.2

Earlier releases. See project history for details.
