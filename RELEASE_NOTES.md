# Release Notes / 更新履歴

## v1.4.2

書き心地まわりの不具合をまとめて直したバグ修正リリースです。新機能はありません。

### 日本語

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
