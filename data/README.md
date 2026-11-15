# 共通正本

辞書の編集元は `sources/` だけです。情報源別JSON（schema_version=2）の施設と登録に、原文・採用値・根拠・判断・調査履歴をまとめています。各IME辞書は同じ正本から直接生成します。

| 場所 | 内容 |
| --- | --- |
| `sources/<情報源>.json` の `facilities[]` | 施設の採用値、`source_record`に原観測、`judgments`に所在地・別掲載の判断 |
| 同ファイルの `entries[]` | 登録の採用値、`source_record`に原登録、`judgments`に補正・編集・除外判断、`research`に調査履歴 |
| 同ファイルの `collection` | 取得範囲・原資料の公式性・利用条件 |
| 同ファイルの `catalog_entries` | 情報源の本文確認・調査メタデータの継承記録 |
| `sources/research_index.json` | 情報源一覧、共通の調査試行、固定調査対象、継承した全体履歴 |

`source_record`は取得原文の証拠で、採用値の別の編集元ではありません。採用値と`judgments`の根拠が食い違うと検証に失敗します。補正の検証結果などの詳細は生成時に組み立て、正本へ重複保存しません。派生登録の`source_record`はnullで、元登録への参照を保持します。

従来の `corrections.json`・`reviews.json`・`reading_research.json` 等は正本へ移行済みです。旧ファイルを併置すると通常生成は拒否します。過去の構造はGit履歴で確認できます。

共通索引の`metadata`に残る旧件数・旧hash・旧パスは調査当時の記録です。現在の件数は `python3 -m njd report`、調査進捗は `python3 -m njd.canonical summary` で正本から計算します。

施設と登録、同名別施設、原文と採用判断を区別します。47都道府県を対象としたことと、取得・検証済みの範囲は異なります。ページ本文・画像・HTTPキャッシュは含めません。コードのMITとは別に、データには出典ごとの利用条件が適用されます。

[データ仕様](../docs/DATA.md) · [更新手順](../docs/DEVELOPMENT.md) · [情報源と利用条件](../docs/SOURCES.md)
