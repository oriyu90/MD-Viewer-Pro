# I18N 抽出レポート (WP-01)

- 元ファイル: `reference/main_v1.5.3.py` の `I18N = {...}`（197〜830行目）
- 出力: `ui/i18n.json`
- 日付: 2026-11-01（実行時点）

## 1. キー数

| 言語 | キー数 |
|------|--------|
| ja   | 148 |
| en   | 148 |
| de   | 148 |
| fr   | 148 |
| zh   | 148 |

## 2. キー集合の一致

- 全5言語のキー集合は一致（欠落 0 / 余剰 0）。
- キー順は全言語で ja と同一。重複キーなし。
- 欠落/余剰キー一覧: **なし**。

## 3. 抽出方法

1. `ast.parse` でソースを解析し、`I18N` に代入している `ast.Assign` ノードを特定。
2. `ast.literal_eval(node.value)` で辞書を評価。Python の隣接文字列リテラル（`"..." "..."`）は評価時に連結される。
3. `json.dump(d, ensure_ascii=False, indent=2)` で `ui/i18n.json` に出力（UTF-8、LF、末尾改行あり）。
   値は一切加工せず、JSON エスケープのみ。

## 4. 検証コマンドと結果

```
python3 -c "import json;d=json.load(open('ui/i18n.json'));print({k:len(v) for k,v in d.items()})"
→ {'ja': 148, 'en': 148, 'de': 148, 'fr': 148, 'zh': 148}
```

元ファイルとの突合（`ast.literal_eval` 結果と JSON 読込結果を比較）:
```
JSON == ast.literal_eval result: True
key order preserved: True
key sets equal across langs: True
```

プレースホルダ（`{...}`）の検証: 全言語で ja と一致（不一致 0）。

## 5. 値の注意点（原文保持・未修正）

以下は意図的に**そのまま保持**した（誤記の可能性を含む。修正は行っていない）:

- 改行を含む値: `hard_breaks_hint`, `gdrive_msg`, `onedrive_msg`, `img_confirm_msg`, `font_hint`, `clip_delete_msg`（全言語）。
- 空文字: `ja.page_label_prefix`（空）、`en/de/fr/zh` の `page_label_suffix`（空）。言語ごとの仕様上の差と思われるが要確認。
- 前後空白あり: `ja.page_label_suffix`、`en/de/fr.page_label_prefix`、`zh.page_label_prefix/suffix`、`en/de/fr.font_not_installed`。意図的か要確認。

## 6. 未確認事項

- 上記 §5 の空文字・前後空白が意図されたものかは、旧アプリの表示を見て確認が必要。
- 翻訳文の品質（誤記・不自然な訳）は本作業の対象外として未確認。
