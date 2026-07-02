**MD Viewer Pro**

設計書 & ユーザー説明書

v1.3.2 (安定版 / Python 3.9+)

macOS 向け Markdown ビューア & エディタ

# **1. アプリ概要**

MD Viewer Pro は macOS 向けの Markdown ビューア & エディタです。PySide6 と QWebEngineView を使ったデスクトップアプリで、Markdown ファイルのリアルタイムプレビュー・編集・印刷・クラウドアップロードが行えます。

| **項目** | **内容** |
| --- | --- |
| アプリ名 | MD Viewer Pro |
| バージョン | v1.3.2 |
| 言語 | Python 3.9+ |
| フレームワーク | PySide6 + QWebEngineView |
| 対応OS | macOS (Apple Silicon / Intel 両対応) |
| 対応ファイル | .md / .txt |

# **2. ウィンドウ構成**

ウィンドウは上からメインツールバー (72px)、書式ツールバー (52px・MD/TXT編集時のみ)、コンテンツ領域の3段構成です。コンテンツ領域は QSplitter で左（エディタ）と右（プレビュー）に分かれています。

## **2-1. 全体レイアウト**

┌───────────────────────────────────────────────────────┐

│ メインツールバー (72px) │

│ 戻る│閲覧│MD編集│TXT編集│フリー│A4│B5│余白│スケール──│詳細│目次│PDF書き出し

├───────────────────────────────────────────────────────┤

│ 書式ツールバー (52px) ← MD/TXT編集モード時のみ │

│ B│I│~~│コード│H1│H2│H3│本文│リスト│番号│引用… │

├─────────────────────┬─────────────────────────────────┤

│ エディタ (左) │ プレビュー (右・常時可視) │

│ StackedWidget │ QWebEngineView ← 1個だけ │

│ Page0: 空(閲覧) │ Markdown→HTML変換して表示 │

│ Page1: MD/TXT エディタ │ │

│ │ 閲覧時: 左列を幅0に折りたたむ │

└─────────────────────┴─────────────────────────────────┘

## **2-2. 設計の核心：プレビューを常時可視にする理由**

QWebEngineView は非表示状態ではレンダリングを保留します。過去のバージョンでは全モードのビューを StackedWidget に入れていたため、非表示ページが描画されないバグが繰り返し発生しました。現行版では QWebEngineView を StackedWidget の外に常時配置し、StackedWidget にはエディタのみを入れることでこの問題を根本的に解決しています。

| **旧設計（バグあり）** | **現行設計（修正済）** |
| --- | --- |
| QWebEngineView×3 を StackedWidget に格納 | QWebEngineView×1 を Splitter 右側に常時表示 |
| 非表示ページはレンダリング保留 | 常に可視→即座に描画 |
| モード切替時に表示が空になる | load() を呼ぶと必ず反映 |
| 一時ファイルの競合が発生 | SafeWebLoader が連番で管理 |

# **3. クラス設計**

| **クラス名** | **役割** | **主なメソッド** |
| --- | --- | --- |
| MDApplication | QApplication サブクラス。マルチウィンドウ管理・macOS Dock メニュー | new\_window(), event() |
| MDViewerPro | メインウィンドウ。全機能の統括 | \_build\_ui, \_set\_mode, \_refresh\_view, \_load\_file |
| MDWebPage | QWebEnginePage サブクラス。リンク制御＋安全な WebAttribute 設定 | set\_mode(), acceptNavigationRequest() |
| SafeWebLoader | QWebEngineView への安全な HTML ロード | load\_html(html), cleanup() |
| ImageFetchWorker | リモート画像をバックグラウンドスレッドで取得 (QThread) | run(), cancel(), fetched シグナル |
| \_HTMLSanitizer | Markdown 由来の未信頼 HTML を allowlist で無害化 | \_sanitize\_html(html) |
| PianoBtn | アクティブ状態を持つカスタムボタン | set\_active(on) |
| MarginDialog | A4/B5余白設定ダイアログ | get\_margins() |
| SettingsDialog | フォント・言語・テーマ設定ダイアログ | get\_result() |
| StartupDialog | 起動時ダイアログ（開く/新規/ガイド） | action, selected\_lang |
| PdfExportDialog | PDF書き出し設定ダイアログ | get\_settings() |
| ContentBridge | QWebChannel ブリッジ（MD編集モード用） | contentChanged(html) |
| ClipboardBridge | QWebChannel ブリッジ（クリップボード） | copyText(text) |

## **3-1. SafeWebLoader の仕組み**

setHtml() には 2MB の文字数制限があります。SafeWebLoader は HTML を一時ディレクトリ内の連番ファイルに書き出し、QUrl.fromLocalFile() でロードします。

* 起動時に mkdtemp() で専用の一時ディレクトリを1つ作成
* load\_html() 呼び出しごとに page\_1.html, page\_2.html ... と連番保存
* closeEvent で shutil.rmtree() により一時ディレクトリごと削除

## **3-2. 主な状態変数**

| **変数名** | **型** | **説明** |
| --- | --- | --- |
| edit\_mode | str | "view" / "md" / "txt" |
| page\_mode | str | "free" / "a4" / "b5" |
| current\_theme | str | "dark" / "light" / プラグイン名 |
| scale\_idx | int | 0〜4 (50% / 75% / 100% / 125% / 150%) |
| \_content\_text | str | 全モードで共有するテキストバッファ |
| current\_file\_path | Optional[str] | 現在開いているファイルのパス |
| a4\_margins | tuple | (上, 右, 下, 左) mm |
| b5\_margins | tuple | (上, 右, 下, 左) mm |
| lang | str | "ja" / "en" / "de" / "fr" |
| bold\_mode | bool | True=テキスト太字強調 |
| \_show\_toc | bool | True=目次サイドパネル表示 |

# **4. データフロー**

## **4-1. ファイルオープン**

QFileDialog → \_load\_file(path)

open(path) → \_content\_text に読み込み

md\_editor に setPlainText（シグナル停止中）

\_refresh\_view() → \_build\_md\_html(\_content\_text)

SafeWebLoader.load\_html(html) → tmpdir/page\_N.html

preview\_web.load(QUrl.fromLocalFile(path)) → 描画

## **4-2. エディタ入力**

textChanged → \_on\_editor\_changed()

\_content\_text を更新

QTimer(300ms) スタート（デバウンス）

\_flush\_preview() → \_refresh\_view() → プレビュー更新

## **4-3. モード切替**

PianoBtn クリック → \_set\_mode(mode)

\_save\_buf() ← \_content\_text に現在のエディタ内容を保存

editor\_stack のページを切替

閲覧/MD編集: splitter.setSizes([0, 1]) ← エディタ列を折りたたむ

TXT編集: splitter.setSizes([480, 720])

\_refresh\_view() → プレビューを即座に更新

# **5. ツールバー仕様**

## **5-1. メインツールバー**

| **ボタン** | **機能** | **備考** |
| --- | --- | --- |
| 戻る | 閲覧モードに戻る | 編集モード時のみ有効 |
| 閲覧 | 閲覧モードに切替 | アクティブ時強調表示 |
| MD編集 | MD編集モードに切替 | 書式ツールバーが出現 |
| TXT編集 | TXT編集モードに切替 | 書式ツールバーが出現 |
| フリー | フリーレイアウト | — |
| A4文書 | A4ページレイアウト | 余白設定が有効になる |
| B5文書 | B5ページレイアウト | 余白設定が有効になる |
| 余白設定 | A4/B5余白を mm 単位で設定 | A4/B5モード時のみ有効 |
| スケール | 50%〜150% の5段階切替 | スライダー操作 |
| 詳細設定 | フォント・言語・テーマ設定 | SettingsDialog を開く |
| 目次 | TOCサイドパネルの表示切替 | アクティブ時強調表示 |
| PDF書き出し | PDF書き出し設定ダイアログ | PdfExportDialog を開く |

## **5-2. 書式ツールバー（MD/TXT編集時のみ）**

| **ボタン** | **挿入** | **ボタン** | **挿入** |
| --- | --- | --- | --- |
| B | \*\*テキスト\*\* | リスト | - （箇条書き） |
| I | \*テキスト\* | 番号 | 1. （番号付き） |
| ~~ | ~~テキスト~~ | 引用 | > （引用） |
| コード | ` ``` `コードブロック` ``` ` | 水平線 | --- |
| H1 | # 見出し | リンク | [テキスト](URL) |
| H2 | ## 見出し | 画像 | ![説明](URL) |
| H3 | ### 見出し | テーブル | 3列2行テンプレ |
| 本文 | 現在ブロックを通常の本文(段落)に戻す | — | — |

> v1.3 で「チェック」ボタンを廃止し、H3 の隣に「本文」ボタンを
> 追加しました。「本文」は現在カーソル位置のブロック(見出し/引用/
> コード等)を通常の段落に戻します。引用・コードブロック内で押した
> 場合は、その直後に新しい本文行を作って抜けます。

# **6. テーマ / スタイル設計**

## **6-1. カラーパレット（ダーク / ライト）**

| **キー** | **ダーク値** | **ライト値** | **用途** |
| --- | --- | --- | --- |
| bg | #000000 | #f0f0f0 | メイン背景 |
| bg2 | #111111 | #ffffff | サブ背景・ダイアログ |
| bg3 | #1c1c1c | #e6e6e6 | コードブロック等 |
| text | #c0c0c0 | #000000 | 本文テキスト |
| heading | #7ab8f5 | #1a5fa0 | 見出し |
| accent | #4a9eff | #1a6abf | リンク・アクセント |
| btn\_active\_bg | #4a4a4a | #888888 | アクティブボタン |
| sep | #2a2a2a | #b0b0b0 | 区切り線 (1px) |

## **6-2. プラグインテーマ**

`~/.mdviewer/themes/` に JSON ファイルを配置することでカスタムテーマを追加できます。必須キーはすべての DARK\_PALETTE キーと同じです。起動時にサンプルの `solarized_dark.json` が自動生成されます。

## **6-3. スタイル適用の流れ**

* \_apply\_theme(refresh=True/False) で Qt ウィジェットの StyleSheet を更新
* エディタは個別 editor\_ss を適用（scale に合わせたフォントサイズ）
* プレビュー HTML は \_build\_md\_html() 内で CSS を生成
* refresh=False で呼ぶと StyleSheet のみ更新しプレビューはそのまま

# **7. 設定の永続化**

設定は `~/.mdviewer/settings.json` に JSON 形式で保存されます。

| **キー** | **型** | **説明** |
| --- | --- | --- |
| lang | str | 表示言語 ("ja" / "en" / "de" / "fr") |
| theme | str | テーマ名 ("dark" / "light" / プラグイン名) |
| font\_family | str | UIフォント名 |
| bold\_mode | bool | テキスト太字強調 |
| scale\_idx | int | スケールインデックス (0〜4) |
| last\_pdf\_dir | str | 最後にPDFを保存したディレクトリ |
| pdf\_embed\_images | bool | PDFに画像を埋め込む |
| window\_geometry | str | ウィンドウサイズ・位置 (Base64エンコード) |

`window_geometry` は `QMainWindow.saveGeometry()` の戻り値を Base64 エンコードした文字列です。次回起動時に `restoreGeometry()` で復元されます。

# **8. ファイル操作・クラウドアップロード**

| **メニュー項目** | **ショートカット** | **動作** |
| --- | --- | --- |
| 新規ウィンドウ | Cmd+Shift+N | 新しいウィンドウを開く |
| 新規作成 | Cmd+N | 空のファイルを新規作成 |
| 開く... | Cmd+O | Markdown / テキストファイルを開く |
| 保存 | Cmd+S | 現在のパスに上書き保存 |
| 名前を付けて保存... | Cmd+Shift+S | 新しい名前で保存 |
| PDFとして書き出し... | Cmd+P | PDF書き出しダイアログを開く |
| HTMLとして書き出し... | — | HTMLファイルに書き出し |
| Google Drive へアップロード | — | ブラウザで Google Drive を開く |
| OneDrive へアップロード | — | ブラウザで OneDrive を開く |

クラウドアップロードは OAuth 認証未実装です。ブラウザを開いてユーザーが手動でファイルをアップロードする方式です。

# **9. ビルド方法 (DMG インストーラ作成)**

## **9-1. 前提条件**

* macOS (Apple Silicon または Intel)
* Python 3.9 以上
* Xcode Command Line Tools

## **9-2. セットアップ**

```
cd ~/Used_ai/"MD Viewer Pro"
python3 -m venv venv_new
source venv_new/bin/activate
pip install pyinstaller pyside6 markdown pygments
```

## **9-3. DMG ビルド**

```
chmod +x build_dmg.sh
./build_dmg.sh
```

| **生成ファイル** | **説明** |
| --- | --- |
| ./dist/MDViewerPro.app | macOS アプリケーションバンドル |
| ./MDViewerPro-Installer.dmg | 配布用 DMG インストーラ |

## **9-4. インストール手順**

* MDViewerPro-Installer.dmg をダブルクリック
* MDViewerPro を Applications フォルダへドラッグ
* Launchpad または Applications フォルダから起動

# **10. ユーザー説明書**

## **10-1. 起動とファイルを開く**

起動するとスタートアップダイアログが表示されます。「ファイルを開く」または「新規作成」を選択してください。「説明を開く」でサンプルガイドが表示されます。

## **10-2. 3つのモード**

| **モード** | **説明** | **切替** |
| --- | --- | --- |
| 閲覧 | Markdown をレンダリングして全幅表示。読み取り専用。 | 「閲覧」ボタン |
| MD編集 | 右にリアルタイムプレビュー。レンダリング済みHTMLをリッチテキスト編集。 | 「MD編集」ボタン |
| TXT編集 | 左にテキストエディタ、右にリアルタイムプレビュー。Markdown記法で直接編集。 | 「TXT編集」ボタン |

## **10-3. スケール変更**

ツールバーのスケールスライダーを左右に動かすと 50% / 75% / 100% / 125% / 150% の5段階で変更できます。エディタとプレビューの両方に反映されます。

## **10-4. A4/B5文書モード**

「A4文書」または「B5文書」ボタンを押すとプレビューが用紙サイズで表示されます。「余白設定」で上下左右の余白を mm 単位で指定できます。Cmd+P で PDF に書き出せます。

## **10-5. 詳細設定**

| **設定項目** | **選択肢** | **説明** |
| --- | --- | --- |
| フォント | システムフォント全て | プレビュー・エディタで使用するフォント |
| 言語 | 日本語 / English / Deutsch / Français | UI のボタンラベルとメニューが切り替わる |
| テーマ | ダーク / ライト / プラグイン | アプリ全体の配色が切り替わる |
| テキスト太字強調 | ON / OFF | 本文テキストの太さを変更 |

## **10-6. Markdown 書き方早見表**

| **表示** | **書き方** | **表示** | **書き方** |
| --- | --- | --- | --- |
| 見出し1 | # テキスト | 見出し2 | ## テキスト |
| 太字 | \*\*テキスト\*\* | 斜体 | \*テキスト\* |
| 取り消し線 | ~~テキスト~~ | コード | `コード` |
| 箇条書き | - テキスト | 番号付き | 1. テキスト |
| チェック | - [ ] テキスト | 引用 | > テキスト |
| リンク | [表示](URL) | 画像 | ![説明](URL) |
| 水平線 | --- | テーブル | \| 列 \| 列 \| |

# **11. v1.1 変更点**

## **11-1. 起動高速化**

旧実装では WebEngine の初期化完了（`loadFinished` シグナル）を待ってからスタートアップダイアログを表示していたため、起動に最大 4 秒の遅延が発生していました。

v1.1 では起動ダイアログを即座に表示し、WebEngine の初期化をバックグラウンドで並行して行うように変更しました。

| **旧実装 (v1.0)** | **新実装 (v1.1)** |
| --- | --- |
| loadFinished 待ち → 最大4秒の遅延 | QTimer.singleShot(0) で即座にダイアログ表示 |
| フォールバックタイマー 4000ms | 不要（即起動） |
| WebEngine 初期化中は UI 未表示 | ダイアログ表示中に WebEngine が並行初期化 |

## **11-2. ウィンドウサイズ・位置の永続化**

ウィンドウを閉じる際に現在のサイズ・位置を `settings.json` の `window_geometry` キーに保存し、次回起動時に復元するようになりました。

* `QMainWindow.saveGeometry()` → Base64エンコード → JSON保存
* 起動時に `restoreGeometry()` で復元
* 設定ファイルが存在しない場合はデフォルトサイズ (1280×900) で起動

# **12. v1.2 変更点**

## **12-1. 新規作成 → MD編集モードで開く**

`file_new()` の初期モードを TXT編集から **MD編集** に変更しました。スタートアップダイアログの「新規作成」ボタン、メニューの「新規作成 (Cmd+N)」のどちらからも MD編集モードで開きます。

| **変更前 (v1.1)** | **変更後 (v1.2)** |
| --- | --- |
| 新規作成 → TXT編集モード | 新規作成 → MD編集モード |

## **12-2. スタートアップダイアログの UX 改善**

ボタンを押さずにダイアログを閉じたとき・ダイアログ以外をクリックしたときの動作を変更しました。

| **操作** | **変更前 (v1.1)** | **変更後 (v1.2)** |
| --- | --- | --- |
| × ボタンで閉じる | ガイドを読み取り専用で開く | 新規作成 |
| Escape キー | ガイドを読み取り専用で開く | 新規作成 |
| ダイアログ背後の本体ウィンドウをクリック | ガイドを読み取り専用で開く | 新規作成 |

### 実装詳細

`StartupDialog` に以下のメソッドを追加しました。

**`reject()`**: × / Escape による閉じ操作を「新規作成」として処理し、`super().accept()` を呼ぶことで `exec()` の戻り値を 1 (Accepted) にします。

**`changeEvent()` + `_check_deactivation()`**: ダイアログが非アクティブになった際に 200ms 待機してから判定します。ComboBox のドロップダウン等による一時的な非アクティブ化（誤トリガー）を除外するためのガードです。

```
ActivationChange イベント
  └─ QTimer.singleShot(200ms) → _check_deactivation()
       ├─ isActiveWindow() == True  → 何もしない（一時的な非アクティブだった）
       ├─ active window が自身の子   → 何もしない（ComboBox ポップアップ等）
       └─ それ以外（本体ウィンドウ等がアクティブ）→ 新規作成として処理
```

# **13. 既知の制約・注意事項**

| **項目** | **内容** |
| --- | --- |
| クラウドアップロード | OAuth 認証は未実装。ブラウザで手動アップロードが必要。 |
| ファイル形式 | .md と .txt のみ対応。 |
| PDF書き出し | QWebEnginePage.printToPdf() を使用。loadFinished の取りこぼし防止と 20 秒タイムアウト復帰に対応 (v1.3.1)。 |
| Python バージョン | 3.9 以上が必要。 |
| WebEngine サンドボックス | 既定で**有効**。開発時のみ環境変数 `MDVP_DISABLE_SANDBOX=1` で無効化可能 (v1.3.1)。配布版では設定しない。 |
| HTML サニタイズ | Markdown 由来の生 HTML/JS は allowlist 方式で無害化 (`_sanitize_html`)。script・イベント属性・javascript: 等を除去 (v1.3.1)。 |
| 一時ファイル | 起動中は /tmp/mdvp\_XXXXX/ を使用。終了時に自動削除。 |
| 外部画像 | ファイルを開く時に確認ダイアログ。取得はバックグラウンドスレッドで実行し、内部アドレス(SSRF)拒否・件数/サイズ上限・タイムアウトを適用 (v1.3.1)。編集中の自動取得は廃止。画像はセッション中メモリにキャッシュ。 |
| MD編集の未保存チェック | MD編集中は WebChannel の 400ms デバウンス経由でテキストバッファが更新される。非常に素早い操作では未保存判定が遅れる場合がある。 |

# **14. v1.3 変更点**

## **14-1. 改行表示の修正**

Markdown レンダリングに `nl2br` 拡張を追加し、ファイル内の単一改行を `<br>` として表示するようにしました。あわせて、閲覧 / MD編集 / TXT編集モードを切り替えても改行が失われないようにしました（contenteditable が生成する `<div>` 行を改行として往復変換）。

## **14-2. コピー / 貼り付けの書式制御**

| **モード** | **コピー** | **貼り付け** |
| --- | --- | --- |
| 閲覧 | プレーンテキスト | — |
| MD編集 | プレーンテキスト | 書式なし(プレーンテキスト)で挿入 |
| TXT編集 | 編集欄のテキストそのまま | 書式なし(プレーンテキスト)で挿入 |

MD編集モードでは copy イベントで `text/plain` のみを書き込み、paste イベントで `text/plain` を `insertText` するため、貼り付け箇所だけ別書体になりません。

## **14-3. 「本文」ボタンの追加**

書式ツールバーの「チェック」ボタンを廃止し、H3 の隣に「本文」ボタンを追加しました（5-2 参照）。

# **15. v1.3.1 変更点**

## **15-1. バンドル軽量化**

PyInstaller spec に未使用 Qt モジュールの除外フィルタを追加しました。QtWebEngine の依存関係を otool で実測した「保持セット(19 framework)」以外（Qt3D / Charts / Graphs / DataVisualization / Multimedia / Quick3D / Location / Bluetooth / 開発ツール等）と対応する QML・プラグインを除外し、アプリサイズを約 130MB 削減しました。

## **15-2. セキュリティ・安定性の強化（設計リスク分析レポート対応）**

| **項目** | **対応** |
| --- | --- |
| 生 HTML/JS の実行 | `_sanitize_html` で allowlist 無害化（13章参照） |
| サンドボックス常時無効化 | 既定で有効化。`MDVP_DISABLE_SANDBOX=1` でのみ無効化 |
| WebAttribute | `MDWebPage` で JavascriptCanOpenWindows 等を明示的に無効化 |
| PDF の loadFinished 競合 | 接続→ロードの順序厳守＋状態管理＋タイムアウト復帰 |
| 画像取得の UI ブロック | `ImageFetchWorker`(QThread) で非同期化 |
| SSRF / 自動通信 | 内部アドレス拒否・件数/サイズ上限、編集中の自動取得を廃止 |

これらの追加は Python 標準ライブラリ(`ipaddress` / `socket` / `html`)のみで実装しており、新たな第三者依存は増えていません（ライセンス構成は不変）。

# **16. v1.3.2 変更点（バグ修正）**

コードレビュー指摘に基づく修正。いずれも Python 標準ライブラリのみで実装し、依存構成は不変。

| **# | 内容** | **修正** |
| --- | --- | --- |
| コードブロックの言語欠落 | MD編集→逆変換で ` ```python ` の言語指定が失われていた。編集モードは codehilite を使わず fenced_code のみを使用し `<code class="language-xxx">` を出力、`_HTML2MD` が言語を復元。往復での空行累積も解消。 |
| コピーボタンの空文字 | detach した clone に `innerText` を使うと Chromium で空になる問題。ライブ DOM の `<code>` から `textContent` を取得する方式に変更。 |
| DNS リバインディング | `_host_is_safe` の事前チェック後に urllib が再解決する TOCTOU を、接続時に IP を再検査・固定する `_PinnedHTTPConnection` / `_PinnedHTTPSConnection` で塞いだ。 |
| PDF 余白の二重適用 | CSS `@page { margin }` を 0 にし、余白は `printToPdf()` に渡す QPageLayout（ユーザー設定値）へ一本化。 |
| 画像 URL 抽出漏れ | `![alt](url "title")` のタイトル付き構文に `_REMOTE_IMG_RE` がマッチするよう修正。 |
| 入れ子 `<a>` タグ | `_HTML2MD` で `_a_depth` を導入し、最外の `<a>` のみをリンクとして扱う。 |

> 注: 指摘のうち「リサイズ時のスタイル再設定によるちらつき」は、`_apply_responsive_style` が
> 既にスケール区分(large/medium/small)の変化時のみ再適用するガードを持つため、実際には
> 毎リサイズでの再設定は発生しておらず、修正不要と判断した。
>
> MD編集モードのコードブロックは、往復の正確さを優先して編集中はシンタックスハイライトを
> 行わない（閲覧モードでは従来どおりハイライト表示）。
