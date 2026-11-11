# 正本データ

`sources/*.json`は情報源ごとの正本です。施設（`facilities`）と読み・表記（`entries`）を分け、原文・所在地・出典・確認日・検証状態を保存しています。

| ファイル | 内容 |
| --- | --- |
| `manifest.json` | 都道府県別の件数・収集範囲・未確認理由 |
| `source_catalog.json` | 公式性・掲載項目・取得方法・利用条件 |
| `locations.json` | 出典付きの所在地補完 |
| `corrections.json` | 名称・読み・外字の補正と未採用候補 |
| `reviews.json` | 個別の編集判断と根拠 |
| `decisions.json` | 登録の除外判断 |
| `identities.json` | 改称・移転などを照合した施設IDの対応 |
| `source_aliases.json` | 同一施設の別掲載を整理する対応 |
| `reading_research.json` | 読みが未確認の登録と確認した資料の範囲 |

生成時に補正・判断を適用し、確認済みの登録だけをIMEへ出力します。取得原文は上書きしません。生成辞書はGitHub Releaseで配布します。

ページ本文・画像・キャッシュは含みません。コードのMITライセンスとは別に、データには出典ごとの利用条件が適用されます。

[データ仕様](../docs/DATA.md) · [情報源と利用条件](../docs/SOURCES.md)
