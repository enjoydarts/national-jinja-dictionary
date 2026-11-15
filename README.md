# 全国神社辞書

National Jinja Dictionary は、神社名を日本語入力で変換するための辞書です。神社庁の公式掲載情報を中心に、名称・読み・所在地・出典を確認して収録しています。

**全国47都道府県を対象としていますが、全神社を網羅した辞書ではありません。** 神社庁資料を利用できない地域の参考資料は、別の出典区分で管理しています。[収録範囲と情報源](docs/SOURCES.md)を確認してください。

## ダウンロードと取り込み

[GitHub Releases](https://github.com/enjoydarts/national-jinja-dictionary/releases)からZIPをダウンロードし、解凍してください。

- `national/`：全国版
- `prefectures/NN/`：都道府県別（`NN`は01〜47の都道府県コード）
- `samples/`：取り込み確認用の少量サンプル

| 日本語入力 | ファイル | 対象 |
| --- | --- | --- |
| ATOK | `atok.txt` / `atok_unicode.txt` | ATOK for Mac 36.0.2 |
| Google日本語入力 | `google.txt` | macOS版3.34.6260.1 |
| Mozc | `mozc.txt` | [参照実装](docs/FORMATS.md#mozc)に基づく形式 |
| Microsoft IME | `msime.txt` | 辞書ツール10.0.26100.9818（x64） |
| macOS標準日本語入力 | `macos.txt` | macOS 27の追加辞書 |

まずサンプルを使い、[取り込み手順](docs/FORMAT_REVIEW.md)に従って確認してください。全形式で生成・自動形式検査に対応していますが、**実際のIMEへの取り込み・変換は未確認**です。対象外の版との互換性は保証していません。

macOSは「追加辞書」用です。テキスト置換、iPhoneへの直接取り込み、デバイス間同期は対象外です。

## 収録方針

- 名称・全文読みの根拠を保存し、未確認の登録は辞書へ出力しません。
- 同名でも所在地が異なる施設は分け、辞書出力時だけ同じ読み・表記・品詞を重複除去します。
- 旧字体・異体字を保持します。形式の制限で出力できない登録は、理由をレポートに残します。
- 通称・略称・途中までの読みや、漢字から推定した読みは追加しません。

[正本データ](data/)には未確認・除外を含む施設情報を保存しています。施設数と辞書行数は異なります。県別件数は`python3 -m njd report`の生成レポート、形式別の出力件数はRelease本文を参照してください。編集元は[共通正本](data/sources/)に統一し、原文・採用値・補正根拠・判断履歴を同じ情報源ファイルに保存します。

## 正本から生成する

Python **3.15.2以上**が必要です。実行時の外部依存はありません。

```sh
git clone https://github.com/enjoydarts/national-jinja-dictionary.git
cd national-jinja-dictionary
python3 -m njd validate
python3 -m njd build --formats all
```

辞書は`dist/dictionaries/`へ生成されます。検証・生成はオフラインで実行できます。

```sh
# 形式・都道府県を指定
python3 -m njd build --formats google,mozc --prefecture 10

# 少量の取り込みサンプルだけを生成
python3 -m njd --output-dir dist/samples build --samples-only --formats all
```

`build`は出力先を指定した形式・地域の生成結果へ置き換えます。詳細は`python3 -m njd --help`と各サブコマンドの`--help`を参照してください。

## 開発・資料

- [開発とデータ更新](docs/DEVELOPMENT.md)
- [リリース手順・CHANGELOG生成](docs/RELEASING.md)
- [データ仕様](docs/DATA.md)
- [情報源・収録範囲・利用条件](docs/SOURCES.md)
- [IME仕様・品詞対応](docs/FORMATS.md)
- [取り込み確認手順](docs/FORMAT_REVIEW.md)
- [未確認データ](docs/REVIEW.md)

## ライセンス

ソースコードとプロジェクト文書は[MIT License](LICENSE)です。収集元データには出典ごとの利用条件が適用されます。データの再配布許諾が未確認の情報源もあり、コードのMITライセンスをデータ全体へ適用するものではありません。詳細は[情報源一覧](docs/SOURCES.md)とRelease本文の出典・利用条件を参照してください。
