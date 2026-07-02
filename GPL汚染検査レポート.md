# MD Viewer Pro — GPL汚染検査レポート

## 検査結果サマリー

| 項目 | 結果 |
| :--- | :--- |
| GPL汚染 | **なし** ✅ |
| アプリ本体のライセンス | **MIT** |
| 配布可能か | **可能**（条件あり→下記参照） |

---

## 検査対象

MD Viewer Pro (`main.py`) および依存ライブラリ全体。

---

## 依存ライブラリのライセンス一覧

| ライブラリ | バージョン | ライセンス | GPL汚染リスク |
| :--- | :--- | :--- | :--- |
| **PySide6** (Qt本体) | 6.10.3 | LGPL-3.0 OR GPL-2.0 OR GPL-3.0 | ✅ なし（LGPL選択で使用） |
| **shiboken6** (Qtバインディング) | 6.10.3 | LGPL-3.0 OR GPL-2.0 OR GPL-3.0 | ✅ なし（LGPL選択で使用） |
| **Python-Markdown** | 3.9 | BSD-3-Clause | ✅ なし |
| **Pygments** (シンタックスハイライト) | 2.20.0 | BSD-2-Clause | ✅ なし |
| **PyObjC** (Dockメニュー) | 12.0 | MIT | ✅ なし |
| **PyInstaller** (ビルドツール) | 6.19.0 | GPL v2+ + Bootloader Exception | ✅ なし（ビルドツールのみ、配布物に含まれない） |
| **altgraph / macholib** | 各種 | MIT | ✅ なし（ビルドツールのみ） |
| **Python 標準ライブラリ** | - | PSF-2.0 | ✅ なし |

---

## 各ライブラリの詳細

### PySide6 / shiboken6（重要）

ライセンス表記が `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` となっています。

**これはどういう意味か？**

「3種類のライセンスから選んで使える」という表記です。**LGPL-3.0 を選択すれば、GPLの強制伝播（感染）は発生しません**。

LGPL（劣等GPL）はGPLと異なり、  
**プロプライエタリ・MITなどの非GPL アプリケーションにも使用できます**。

ただし LGPL には以下の義務があります：

- 帰属表示（クレジット）を行う → `NOTICE.md` に記載済み ✅
- ユーザーが PySide6/Qt を差し替えてリビルドできるよう、ソースとビルド手順を提供する → `main.py` + `MDViewerPro.spec` を公開 ✅
- LGPL ライセンス文書を配布物に同梱する → `NOTICE.md` に全文記載 ✅

### PyInstaller（注意点）

PyInstaller 自体は GPL ライセンスですが：

1. **ビルドツールとして使うだけ**であり、配布物（DMG/app）には含まれません
2. PyInstaller が生成する「ブートローダー」には **Bootloader Exception** という特例条項があり、非GPLアプリへの組み込みが明示的に許可されています

```
"...the authors give you unlimited permission to link or embed compiled
bootloader and related files into combinations with other programs,
and to distribute those combinations without any restriction..."
```

→ **PyInstaller による GPL 汚染は発生しません** ✅

### Pygments の「Emacs 22 に着想」について

Pygments のデフォルトスタイルは「*inspired by Emacs 22*」と書かれており、Emacs は GPL です。ただし：

- Pygments のカラースキームは**独自に実装された**もの（色のコード値を独自に定義）
- 「着想を得た」という記述は著作権継承を意味しない
- Pygments 自体が **BSD-2-Clause** ライセンスを付与して配布している
- 色コード（`#008000` など）は機能的情報であり著作権の対象外

→ **Pygments 使用による GPL 汚染は発生しません** ✅

---

## アプリ本体のライセンス（MIT）

`main.py` をはじめとするアプリケーション固有のコードは **MIT ライセンス** のもとで配布されます。

MIT ライセンスは LGPL・BSD・MIT の各依存ライブラリと完全に共存できます。

```
MIT License — Copyright (c) 2026 Yuki_Orita
（全文は LICENSE ファイルを参照）
```

---

## 配布時に必要な対応（LGPL準拠）

DMG に以下を同梱すること → **対応済み** ✅

| ファイル | 内容 |
| :--- | :--- |
| `LICENSE` | MIT ライセンス全文 |
| `NOTICE.md` | 全依存ライブラリの帰属表示・ライセンス文 |

加えて、ソースコードとビルド方法（`main.py` + `MDViewerPro.spec` + `build_dmg.sh`）を配布または公開することで、LGPL の「再リンク条項」を満たせます。

---

## 結論

**MD Viewer Pro に GPL 汚染はありません。**  
MIT ライセンスのもとで自由に配布できます。  
LGPL 準拠のため `LICENSE` と `NOTICE.md` を DMG に同梱済みです。

---

*検査日: 2026-04-22*  
*検査対象バージョン: MD Viewer Pro v1.01*

---

## 追記 (v1.3.1 – v1.3.2 / 2026-07-02)

v1.3.1〜v1.3.2 で追加したセキュリティ強化・バグ修正（HTML サニタイズ・
SSRF 対策・DNS リバインディング対策・画像取得の非同期化など）は
**Python 標準ライブラリのみ**（`html` / `ipaddress` / `socket` / `urllib` /
`http.client` / `html.parser`）で実装しており、**新たな第三者依存ライブラリは
追加していません**。したがって上記のライセンス構成・GPL 非汚染の結論は
v1.3.2 においても変わりません。MIT ライセンスでの配布が可能です。
