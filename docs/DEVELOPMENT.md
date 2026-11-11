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
| `data/sources/` | 出典・原文・状態を含む施設と登録の正本 |
| `data/*.json` | 情報源一覧、件数、補正、施設ID対応、編集判断 |
| `tests/` | 自動テスト。人工データは実施設の根拠には使用しない |
| `tools/` | 指定版の公式IME実装を再照合する任意の開発ツール |
| `.github/workflows/` | CIとリリース処理 |

各IMEへは共通データから直接出力します。IME固有の品詞・符号化・長さ制限は出力側で管理します。[データ仕様](DATA.md)と[形式仕様](FORMATS.md)を参照してください。

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

部分取得で既存施設が欠ける場合や検証に失敗した場合は、前回の正本を保持します。取得原文と編集判断は分離し、再取得で既存判断を消しません。変更は原文hashとGit差分で確認してください。

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
