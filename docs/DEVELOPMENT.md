# 開発とデータ更新

## セットアップと検証

Pythonの対象版は[.python-version](../.python-version)と[pyproject.toml](../pyproject.toml)に定義しています。HTTP収集のプロセス間ロックはmacOS/Linuxを対象とします。

```sh
python3 -m unittest discover -s tests -v
python3 -m njd validate
```

任意で`python3 -m pip install -e .`を実行すると、`national-jinja-dictionary`コマンドを利用できます。

## 構成

| 場所 | 役割 |
| --- | --- |
| `njd/` | 収集、正規化、検証、保存、辞書出力、レポート生成 |
| `data/sources/` | 原文・採用値・根拠・判断・調査を統合した唯一の正本 |
| `data/sources/research_index.json` | 共通の調査試行・固定対象・全体履歴。現在件数は生成 |
| `tests/` | 自動テスト。人工データは実施設の根拠には使用しない |
| `tools/` | 指定版の公式IME実装を再照合する任意の開発ツール |
| `.github/workflows/` | CIとリリース処理 |

各IMEへは共通データから直接出力します。IME固有の品詞・符号化・長さ制限は出力側で管理します。[データ仕様](DATA.md)と[形式仕様](FORMATS.md)を参照してください。

## 正本の修正

編集する場所は`data/sources/<情報源>.json`です。施設と登録はIDで参照し、同名の別施設を所在地で区別します。

1. `entries[]`から登録IDを探し、`source_record`の原文、現在の`surface`・`reading`・`status`と、`judgments`・`research`の根拠を確認する。
2. 実資料で確認した変更は、同じ登録内の採用値と`judgments`の該当判断へ反映する。補正なら`judgments.corrections`に原文hash・原値・変更・参照・同定根拠を保持する。根拠のない採用値だけの変更は検証で拒否する。
3. 旧判断を上書きで捨てず、同じ判断内の履歴へ残す。取得原文の`source_record`・ID・原文hashは編集判断で書き換えない。
4. `python3 -m njd validate`を実行し、`git diff -- data/sources/`で変更を確認する。件数やhashの集計を手修正しない。

読み不足への補完は、下記の`njd.proposals`も同じ正本を更新します。既存判断の保護、公式資料優先、根拠検証は維持します。生成時の`correction`等の詳細表示は正本内の判断から作られ、別の編集元ではありません。

```sh
python3 -m njd report
python3 -m njd.canonical summary
```

調査進捗は正本から計算します。共通索引の旧件数・旧hash・旧パスは過去の調査記録として保持し、現在値と区別します。

## 旧構造からの明示的な移行

現在のリポジトリは移行済みです。以下は古いチェックアウトや既存データを扱う場合の手順で、通常の辞書生成時に自動変換しません。

```sh
# 存在しない別ディレクトリに変換。元の正本は変更しない。
python3 -m njd.canonical migrate --data-dir data --destination /tmp/njd-migrated
# 原文・判断・履歴の損失検査後、6形式の本体を移行前と比較する。
# 切替時にも移行元が変わっていないことを再検査する。
python3 -m njd.canonical install --data-dir data --migrated /tmp/njd-migrated
python3 -m njd validate
```

移行・更新はロック下で世代を切り替えます。通常の書込失敗は元へ復元します。プロセスの強制終了で取引記録が残った場合は生成を止めるので、`python3 -m njd.canonical recover --data-dir data`で旧世代へ戻してから再実行してください。ロック・取引記録・一時ファイルはコミットしません。

## 神社庁資料の収集

実行前に[情報源一覧](SOURCES.md)で規約・robots・取得状態を確認してください。自動収集は実装済みの情報源に限ります。京都・福岡の既存正本は`collect all`の更新対象ではありません。兵庫は指定した地図検索範囲、岐阜は取得済み索引の範囲であり、県内全件の取得を保証しません。

```sh
# 既存の正本とは別の場所で抽出を確認
python3 -m njd --data-dir /tmp/njd-pilot collect gunma --limit 100

# 指定した情報源を収集（0は上限なし）
python3 -m njd collect gunma --limit 0

# 実装済みの情報源を収集
python3 -m njd collect all --limit 0

# 必要な場合だけ再取得。キャッシュのみでの再開も可能
python3 -m njd collect gunma --limit 0 --refresh
python3 -m njd collect gunma --limit 0 --offline

python3 -m njd validate
git diff -- data/
```

キャッシュは既定で`~/.cache/national-jinja-dictionary/http`に保存します。`--cache-dir`で変更できます。同一ホストへのアクセス間隔は最低2秒です。タイムアウト・再試行・途中再開・robots再確認に対応し、アクセス拒否や取得方針が判定できない場合は停止します。

部分取得で既存施設が欠ける場合や検証に失敗した場合は、前回の正本を保持します。取得原文と編集判断は同じ正本内の別フィールドに保存し、再取得で既存判断を消しません。変更は原文hashとGit差分で確認してください。

## 読みの補完

読みは資料に明示された全文を使い、同名の別施設から流用しません。神社庁詳細を優先し、施設公式・Wikipedia・行政資料を使う場合は名称と所在地を照合します。調査入口の`jinja-net.jp`は辞書の出典に使いません。

```sh
# 神社庁詳細の補完候補
python3 -m njd.agency_details --source shimane --state-dir /tmp/njd-details --limit 100

# Wikipediaのカテゴリと記事を照合
python3 -m njd.wikipedia --prefecture all --state-dir /tmp/njd-wikipedia --inventory-only
python3 -m njd.wikipedia --prefecture all --state-dir /tmp/njd-wikipedia --limit 100

# 国税庁の公開データとの照合
python3 -m njd.corporate --prefecture all --state-dir /tmp/njd-corporate --limit 3

# 候補を検証し、差分の確認後に適用
python3 -m njd.proposals --input /tmp/njd-details/proposals.json
python3 -m njd.proposals --input /tmp/njd-details/proposals.json --prefer-agency --apply
python3 -m njd validate
git diff -- data/
```

調査状態と取得キャッシュはリポジトリ外へ保存します。採用する根拠・原文・補正は正本へ保存してコミットします。`--offline`・`--refresh`などの対応は各コマンドの`--help`を参照してください。

参考資料単独枠の候補は`python3 -m njd.reference_sources`、宮崎県神道青年会資料の候補は`python3 -m njd.association_sources`で作成します。候補の出典・抽出結果・既存データとの差分を照合してから保存してください。これらは神社庁掲載確認済みへ分類しません。

## 貢献時の確認

- 新規・修正データには施設の同定根拠、原文、出典、確認日を付ける。
- 推定読み、根拠のない名称変更、未確認データの出力を追加しない。
- 収集先の規約とアクセス制限を守る。取得本文・画像・認証情報をコミットしない。
- 変更に応じたテストと正本検証を実行する。
- 生成辞書は[リリース処理](RELEASING.md)で配布する。
