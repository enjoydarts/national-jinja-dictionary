# 辞書の取り込みと確認

生成ファイルは各形式の自動検査を通していますが、**実際のIMEへの取り込み・変換は全形式で未確認**です。まず少量サンプルを試験用の新規辞書へ取り込んでください。対象版と仕様は[FORMATS.md](FORMATS.md)に記載しています。

## サンプルを用意する

ReleaseのZIPに含まれる`samples/`を使うか、正本から生成します。

```sh
python3 -m njd --output-dir dist/ime-samples build --samples-only --formats all --sample-name 倭文神社 --sample-name 大國神社
```

全国版は`samples/national/`、県指定時は`samples/prefectures/NN/`へ出力します。正本から生成した場合は、`manifest.json`に選択した登録と出典、`report.json`に形式別の行数・除外理由を保存します。Releaseの辞書ZIPにはこれらの管理ファイルは含みません。同じ読み・表記・品詞は1行になるため、施設数と取り込み行数は一致しない場合があります。

## 取り込む

| ファイル | 操作 |
| --- | --- |
| `atok.txt` | ATOK for Macの辞書ユーティリティでShift JIS読み書きを「日本語（Shift JIS）」に設定し、「ファイルから登録・削除」の単語一括処理でATOK形式として指定する。[設定](https://www.atok.com/other/support/howtouse/mac/mn/pgs/mn_tool_d_com_encoding.htm)・[一括処理](https://www.atok.com/other/support/howtouse/mac/mn/pgs/mn_tool_ut_syori_word_d.htm) |
| `atok_unicode.txt` | 同じ単語一括処理でATOK形式として指定する。BOM付きUTF-16BEのまま渡す |
| `google.txt` | 辞書ツールの管理メニューから「新規辞書にインポート」を選び、文字コードをUTF-8にする |
| `mozc.txt` | 辞書ツールから新規辞書へインポートする。UTF-8のTAB3列形式 |
| `msime.txt` | ユーザー辞書ツールで試験用辞書を開き、［ツール］→［テキスト ファイルからの登録］を選ぶ。BOM付きUTF-16LEのまま渡す |
| `macos.txt` | 日本語入力の設定の「追加辞書」へドラッグする。[Apple公式手順](https://support.apple.com/ja-jp/guide/japanese-input-method/jpim10226/6.3/mac/27)。テキスト置換には使わない |

## 結果を確認する

1. 受理・拒否件数を確認する。正本から生成した場合は`report.json`の出力行数と照合する。
2. 辞書に登録された読みを入力し、表記・旧字体・異体字が候補に残るか確認する。
3. 難読名、同名施設、長い名称、補助平面の文字を含む登録を確認する。
4. 書き戻しが可能な製品では元ファイルと読み・表記・品詞を比較する。

問題を報告する際はOS・IMEの版、生成元コミット、対象形式、該当登録ID、再現手順、期待結果と実際の結果を記載してください。個人の辞書全体や無関係な登録単語を添付する必要はありません。

自動形式検査、公式実装の静的照合、製品パーサーの実行、IME登録、実際の変換はそれぞれ別の確認です。自動検査の成功だけで実機確認済みとは扱いません。
