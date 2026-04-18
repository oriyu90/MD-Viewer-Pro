**MD Viewer Pro**

設計書 & ユーザー説明書

v6 (安定版 / Python 3.9+)

macOS 向け Markdown ビューア & エディタ

# **1. アプリ概要**

MD Viewer Pro は macOS 向けの Markdown ビューア & エディタです。PyQt6 と QWebEngineView を使ったデスクトップアプリで、Markdown ファイルのリアルタイムプレビュー・編集・印刷・クラウドアップロードが行えます。

| **項目** | **内容** |
| --- | --- |
| アプリ名 | MD Viewer Pro |
| バージョン | v6（安定版） |
| 言語 | Python 3.9+ |
| フレームワーク | PyQt6 + QWebEngineView |
| 対応OS | macOS (Apple Silicon / Intel 両対応) |
| 対応ファイル | .md / .txt |

# **2. ウィンドウ構成**

ウィンドウは上からメインツールバー (64px)、書式ツールバー (48px・MD編集時のみ)、コンテンツ領域の3段構成です。コンテンツ領域は QSplitter で左（エディタ）と右（プレビュー）に分かれています。

## **2-1. 全体レイアウト**

┌───────────────────────────────────────────────────────┐

│ メインツールバー (64px) │

│ 戻る│閲覧│MD編集│TXT編集│フリー│A4│余白│文字サイズ──│詳細│印刷

├───────────────────────────────────────────────────────┤

│ 書式ツールバー (48px) ← MD編集モード時のみ │

│ B│I│~~│コード│H1│H2│H3│リスト│番号│チェック│引用… │

├─────────────────────┬─────────────────────────────────┤

│ エディタ (左) │ プレビュー (右・常時可視) │

│ StackedWidget │ QWebEngineView ← 1個だけ │

│ Page0: 空(閲覧) │ Markdown→HTML変換して表示 │

│ Page1: MD エディタ │ │

│ Page2: TXT エディタ │ 閲覧時: 左列を幅0に折りたたむ │

└─────────────────────┴─────────────────────────────────┘

## **2-2. 設計の核心：プレビューを常時可視にする理由**

QWebEngineView は非表示状態ではレンダリングを保留します。過去のバージョンでは全モードのビューを StackedWidget に入れていたため、非表示ページが描画されないバグが繰り返し発生しました。v6 では QWebEngineView を StackedWidget の外に常時配置し、StackedWidget にはエディタのみを入れることでこの問題を根本的に解決しています。

| **旧設計（バグあり）** | **新設計 v6（修正済）** |
| --- | --- |
| QWebEngineView×3 を StackedWidget に格納 | QWebEngineView×1 を Splitter 右側に常時表示 |
| 非表示ページはレンダリング保留 | 常に可視→即座に描画 |
| モード切替時に表示が空になる | load() を呼ぶと必ず反映 |
| 一時ファイルの競合が発生 | SafeWebLoader が連番で管理 |

# **3. クラス設計**

| **クラス名** | **役割** | **主なメソッド** |
| --- | --- | --- |
| MDViewerPro | メインウィンドウ。全機能の統括 | \_build\_ui, \_set\_mode, \_refresh\_view, \_load\_file |
| SafeWebLoader | QWebEngineView への安全な HTML ロード | load\_html(html), cleanup() |
| PianoBtn | 白鍵デザインのカスタムボタン | set\_active(on) |
| MarginDialog | A4余白設定ダイアログ | get\_margins() |
| SettingsDialog | フォント・言語・テーマ設定ダイアログ | get\_result() |

## **3-1. SafeWebLoader の仕組み**

setHtml() には 2MB の文字数制限があります。SafeWebLoader は HTML を一時ディレクトリ内の連番ファイルに書き出し、QUrl.fromLocalFile() でロードします。

* 起動時に mkdtemp() で専用の一時ディレクトリを1つ作成
* load\_html() 呼び出しごとに page\_1.html, page\_2.html ... と連番保存
* loadFinished シグナルで古いファイルをクリーンアップ
* closeEvent で shutil.rmtree() により一時ディレクトリごと削除

## **3-2. 主な状態変数**

| **変数名** | **型** | **説明** |
| --- | --- | --- |
| edit\_mode | str | "view" / "md" / "txt" |
| page\_mode | str | "free" / "a4" |
| dark\_mode | bool | True=ダーク / False=ライト |
| scale\_idx | int | 0=100% / 1=125% / 2=150% |
| \_content\_text | str | 全モードで共有するテキストバッファ |
| current\_file\_path | Optional[str] | 現在開いているファイルのパス |
| a4\_margins | tuple | (上, 右, 下, 左) mm |
| lang | str | "ja" / "en" |

# **4. データフロー**

## **4-1. ファイルオープン**

QFileDialog → \_load\_file(path)

open(path) → \_content\_text に読み込み

md\_editor / txt\_editor に setPlainText（シグナル停止中）

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

閲覧: splitter.setSizes([0, 1]) ← エディタ列を折りたたむ

編集: splitter.setSizes([480, 720])

\_refresh\_view() → プレビューを即座に更新

# **5. ツールバー仕様**

## **5-1. メインツールバー**

| **ボタン** | **機能** | **備考** |
| --- | --- | --- |
| 戻る | 閲覧モードに戻る | 編集モード時のみ有効 |
| 閲覧 | 閲覧モードに切替 | アクティブ時グレー表示 |
| MD編集 | MD編集モードに切替 | 書式ツールバーが出現 |
| TXT編集 | TXT編集モードに切替 | — |
| フリー | フリーレイアウト | — |
| A4文書 | A4ページレイアウト | 余白設定が有効になる |
| 余白設定 | A4余白を mm 単位で設定 | A4モード時のみ有効 |
| 文字サイズ | 100% / 125% / 150% の切替 | スライダー操作 |
| 詳細設定 | フォント・言語・テーマ設定 | SettingsDialog を開く |
| 印刷 | 現在のプレビューを印刷 | A4設定が適用される |

## **5-2. 書式ツールバー（MD編集時のみ）**

| **ボタン** | **挿入** | **ボタン** | **挿入** |
| --- | --- | --- | --- |
| B | \*\*テキスト\*\* | リスト | - （箇条書き） |
| I | \*テキスト\* | 番号 | 1. （番号付き） |
| ~~ | ~~テキスト~~ | チェック | - [ ] （チェック） |
| コード | `テキスト` | 引用 | > （引用） |
| H1 | # 見出し | 水平線 | --- |
| H2 | ## 見出し | リンク | [テキスト](URL) |
| H3 | ### 見出し | 画像 | ![説明](URL) |
| テーブル | 3列2行テンプレ | — | — |

# **6. テーマ / スタイル設計**

## **6-1. カラーパレット（ダーク / ライト）**

| **キー** | **ダーク値** | **ライト値** | **用途** |
| --- | --- | --- | --- |
| bg | #000000 | #f0f0f0 | メイン背景 |
| bg2 | #111111 | #ffffff | サブ背景・ダイアログ |
| bg3 | #1c1c1c | #e6e6e6 | コードブロック等 |
| text | #c0c0c0 | #1a1a1a | 本文テキスト |
| heading | #7ab8f5 | #1a5fa0 | 見出し |
| accent | #4a9eff | #1a6abf | リンク・アクセント |
| btn\_active\_bg | #4a4a4a | #888888 | アクティブボタン |
| sep | #2a2a2a | #b0b0b0 | 区切り線 (1px) |

## **6-2. スタイル適用の流れ**

* \_apply\_theme(refresh=True/False) で Qt ウィジェットの StyleSheet を更新
* エディタは個別 editor\_ss を適用（scale に合わせたフォントサイズ）
* プレビュー HTML は \_build\_md\_html() / \_build\_txt\_html() 内で CSS を生成
* refresh=False で呼ぶと StyleSheet のみ更新しプレビューはそのまま

# **7. ファイル操作・クラウドアップロード**

| **メニュー項目** | **ショートカット** | **動作** |
| --- | --- | --- |
| 開く... | Cmd+O | Markdown / テキストファイルを開く |
| 保存 | Cmd+S | 現在のパスに上書き保存 |
| 名前を付けて保存... | Cmd+Shift+S | 新しい名前で保存 |
| 印刷... | Cmd+P | 印刷ダイアログを開く |
| Google Drive へアップロード | — | ブラウザで Google Drive を開く |
| OneDrive へアップロード | — | ブラウザで OneDrive を開く |

クラウドアップロードは OAuth 認証未実装です。ブラウザを開いてユーザーが手動でファイルをアップロードする方式です。

# **8. ビルド方法 (DMG インストーラ作成)**

## **8-1. 前提条件**

* macOS (Apple Silicon または Intel)
* Python 3.9 以上
* Xcode Command Line Tools

## **8-2. セットアップ**

cd ~/Downloads/my\_md\_viewer2

python3 -m venv venv

source venv/bin/activate

pip install pyinstaller pyqt6 pyqt6-webengine markdown

## **8-3. DMG ビルド**

chmod +x build\_dmg.sh

./build\_dmg.sh

| **生成ファイル** | **説明** |
| --- | --- |
| ./dist/MDViewerPro.app | macOS アプリケーションバンドル |
| ./MDViewerPro-Installer.dmg | 配布用 DMG インストーラ |

## **8-4. インストール手順**

* MDViewerPro-Installer.dmg をダブルクリック
* MDViewerPro を Applications フォルダへドラッグ
* Launchpad または Applications フォルダから起動

# **9. ユーザー説明書**

## **9-1. 起動とファイルを開く**

起動すると自動的にファイル選択ダイアログが開きます。.md または .txt ファイルを選んでください。キャンセルするとサンプルテキストが表示されます。

## **9-2. 3つのモード**

| **モード** | **説明** | **切替** |
| --- | --- | --- |
| 閲覧 | Markdown をレンダリングして全幅表示。読み取り専用。 | 「閲覧」ボタン |
| MD編集 | 左にエディタ、右にリアルタイムプレビュー。Markdown 記法で編集。 | 「MD編集」ボタン |
| TXT編集 | 左にエディタ、右に等幅テキストプレビュー。プレーンテキスト編集。 | 「TXT編集」ボタン |

## **9-3. 文字サイズの変更**

ツールバーの文字サイズスライダーを左右に動かすと 100% / 125% / 150% の3段階で変更できます。エディタとプレビューの両方に反映されます。

## **9-4. A4文書モード**

「A4文書」ボタンを押すとプレビューが A4 用紙サイズで表示されます。「余白設定」で上下左右の余白を mm 単位で指定できます。Cmd+P で印刷できます。

## **9-5. 詳細設定**

| **設定項目** | **選択肢** | **説明** |
| --- | --- | --- |
| フォント | システムフォント全て | プレビューで使用するフォントを変更 |
| 言語 | 日本語 / English | UI のボタンラベルとメニューが切り替わる |
| テーマ | ダーク / ライト | アプリ全体の配色が切り替わる |

## **9-6. Markdown 書き方早見表**

| **表示** | **書き方** | **表示** | **書き方** |
| --- | --- | --- | --- |
| 見出し1 | # テキスト | 見出し2 | ## テキスト |
| 太字 | \*\*テキスト\*\* | 斜体 | \*テキスト\* |
| 取り消し線 | ~~テキスト~~ | コード | `コード` |
| 箇条書き | - テキスト | 番号付き | 1. テキスト |
| チェック | - [ ] テキスト | 引用 | > テキスト |
| リンク | [表示](URL) | 画像 | ![説明](URL) |
| 水平線 | --- | テーブル | | 列 | 列 | |

# **10. 既知の制約・注意事項**

| **項目** | **内容** |
| --- | --- |
| クラウドアップロード | OAuth 認証は未実装。ブラウザで手動アップロードが必要。 |
| ファイル形式 | .md と .txt のみ対応。 |
| 印刷 | QWebEngineView.page().print() を使用。プリンタドライバに依存。 |
| Python バージョン | 3.9 以上が必要。 |
| WebEngine サンドボックス | QTWEBENGINE\_DISABLE\_SANDBOX=1 で無効化済（Mac 起動対策）。 |
| 一時ファイル | 起動中は /tmp/mdvp\_XXXXX/ を使用。終了時に自動削除。 |