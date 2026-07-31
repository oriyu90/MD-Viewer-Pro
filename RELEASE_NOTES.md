# Release Notes / 更新履歴

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
