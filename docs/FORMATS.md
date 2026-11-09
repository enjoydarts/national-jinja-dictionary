# 出力仕様と品詞対応

公式資料・公式実装で確認できた範囲だけを出力します。全形式の実際のIME取り込みは未確認です。作業時の調査経緯・台帳はObsidianで管理し、この文書には利用者向けの仕様と根拠を記載します。

## Mozc

対象は公式リポジトリのcommit `d918f30063999d4ca250f76ced8b92169a0e0b25`（2026-09-07）です。インストール済み各ビルドでの動作を保証するものではありません。

| 項目 | このプロジェクトの出力 |
| --- | --- |
| 列 | 読み、表記、品詞の3列。任意コメントは省略 |
| ヘッダー | なし |
| 区切り | TAB |
| 品詞 | 固有名詞 |
| 文字コード・BOM | UTF-8、BOMなし |
| 改行 | LF、最終行にもLF |
| エスケープ | 引用形式を使わず、TAB・CR・LFを含むフィールドを除外 |
| 長さ | 読み・表記それぞれ300 UTF-8バイト以下 |
| 辞書の行数 | 重複除去後100万行以下。超える場合は出力を保留 |

神社という特定施設の名称として `固有名詞` を採用します。神社一般を意味する普通名詞や、祭神の人名としては扱いません。この対応はプロジェクトの設計判断で、公式資料が神社の品詞を指定したという意味ではありません。

根拠となる公式実装：

- [インポーター](https://github.com/google/mozc/blob/d918f30063999d4ca250f76ced8b92169a0e0b25/src/dictionary/user_dictionary_importer.cc)：TAB分割、先頭3フィールドと任意コメント、改行の受付。
- [文字列の検証](https://github.com/google/mozc/blob/d918f30063999d4ca250f76ced8b92169a0e0b25/src/dictionary/user_dictionary_util.cc)：`kMaxStringSize = 300` とバイト数の `size()`、不正文字検証。
- [GUI辞書ツール](https://github.com/google/mozc/blob/d918f30063999d4ca250f76ced8b92169a0e0b25/src/gui/dictionary_tool/dictionary_tool.cc)：UTF-8等の入力処理。
- [品詞定義](https://github.com/google/mozc/blob/d918f30063999d4ca250f76ced8b92169a0e0b25/src/data/rules/user_pos.def)：`固有名詞` と `PROPER_NOUN` の対応。
- [書き出しと保存上限](https://github.com/google/mozc/blob/d918f30063999d4ca250f76ced8b92169a0e0b25/src/dictionary/user_dictionary_storage.cc)：書き出すフィールド、登録上限。

BOMなし・LF・コメント省略は、確認した入力実装が受け付ける選択肢から採用しました。公式インポーターのコンパイル実行や、インストール済みIMEでの取り込みは未実施です。

## macOS標準日本語入力の追加辞書

対象は **macOS 27.0.1（26A434）、日本語入力設定1.1（261）** です。版を固定した[追加辞書ガイド](https://support.apple.com/ja-jp/guide/japanese-input-method/jpim10226/6.3/mac/27)と[品詞表](https://support.apple.com/ja-jp/guide/japanese-input-method/jpim10211/6.3/mac/27)を確認しました。

| 項目 | 採用した出力 |
| --- | --- |
| 列・区切り | 読み・単語・品詞の3列、ASCIIカンマ |
| ヘッダー・メモ | どちらも省略 |
| 品詞 | その他の固有名詞 |
| 文字コード・BOM・改行 | UTF-8、BOMなし、LF（最終行にもLF） |
| エスケープ | 全フィールドをASCII二重引用符で囲み、内部の二重引用符を二重化。制御文字を拒否 |
| 公式文書の長さ | 読み32文字、単語64文字、行127文字以下 |
| プロジェクトの制限 | 保守的にUTF-16コード単位で計数。行は引用符・カンマ・末尾LFも含め127単位以内 |
| 全体の語数上限 | 公式ガイドに記載なし。無制限と断定しない |

施設の固有名を表す品詞として、公式品詞表に実例がある `その他の固有名詞` を採ります。共通データの中立な `proper_noun` から出力時に対応づけます。

文字数の内部計数方法は断定しません。UTF-16コード単位はUnicodeコードポイントや通常の表示文字数以上になるため、上の制限は公式の文字数上限を超えないよう狭めるプロジェクトの判断です。特に補助平面の文字を含む長い名称は、IME自体が受理する可能性があっても、この保守的な境界で理由付き除外になる場合があります。原文は保持し、切り詰めや文字置換はしません。

文字コード・引用・改行は、指定版の公式プログラムに含まれる `TextFile` 解析クラスへ一時ファイルを渡して実測しました。UTF-8、空白、カンマ、引用符、補助平面文字「𠮷」、異体字「神」、32文字の読み・64文字の単語が、そのまま解析結果に残ることを確認しています。Appleのプログラムや本文はリポジトリへ複製していません。[確認情報](MACOS_FORMAT_EVIDENCE.json)に版・実体hash・人工入力のhashと確認範囲を保存しています。

この試験は**公式解析処理の入力照合**です。追加辞書としてのインストール、実際の変換候補、個人のユーザ辞書、テキスト置換、iPhoneや同期の確認はしていません。

指定版macOS上で再実行する任意の開発用チェック（Command Line Toolsが必要）：

```sh
python3 tools/check_macos_parser.py
python3 tools/check_macos_parser.py --input dist/dictionaries/national/macos.txt --report dist/macos-parser-check.json
```

チェックは入力の一時コピーだけを開き、全フィールドと行数を比較します。辞書のインストールや設定変更は行いません。通常のPython生成・検証はこのmacOS専用チェックに依存しません。

## 保留しているIME形式

| 形式 | 確認した資料・対象 | 品詞の候補と理由 | 出力を保留する不足情報 |
| --- | --- | --- | --- |
| ATOK | [現行公式単語ファイル仕様](https://www.atok.com/other/support/howtouse/mac/dc/pgs/dc_word_file.htm)とATOK for Mac 36.0.2（245128.3.0）の付属ヘルプ | 固有地名（5）：場所としての特定施設名 | 実際の書き出しバイト列、BOM・改行、厳密な文字計数 |
| Google日本語入力 | [公式辞書ヘルプ](https://support.google.com/ime/japanese/answer/166765?hl=ja)、[Mozcのブランド説明](https://github.com/google/mozc/blob/d918f30063999d4ca250f76ced8b92169a0e0b25/docs/about_branding.md) | 固有名詞を検討。製品の品詞表と照合待ち | 製品版の一括形式・対象バージョン・インポートサンプル |
| Microsoft IME | [公式サポート](https://support.microsoft.com/ja-jp/windows/hardware/input-devices/microsoft-japanese-ime)（Windows 10/11） | 地名・固有名詞等の正式な対応名を確認して決定 | 一括形式、品詞、文字コード、BOM、改行、制限、対象ビルド |

ATOK現行資料はヘッダー `!!ATOK_TANGO_TEXT_HEADER_1`、TAB区切り、読み32・単語100文字を明記します。旧版の単語64文字制限を現行版へ流用しません。[公式の単語出力手順](https://www.atok.com/other/support/howtouse/mac/mn/pgs/mn_tool_ut_out_word_out_d.htm)と指定版の付属ヘルプで、「Unicodeで出力する」の選択と、選択しない場合のShift JIS出力を確認しました。Unicode出力への対応自体は確認済みです。具体的なUTF形式・バイト順・BOM・改行バイト列・厳密な文字計数は未確認であり、実際の書き出しサンプルが必要です。

付属ヘルプは「日本語（Mac OS）」と「日本語（Shift JIS）」で一部の文字対応が異なることも説明しています。「Shift JIS」という名称だけでPythonの`cp932`と同一とは決めません。また、一括処理画面のUnicode指定は未登録語ファイルの出力用であり、入力形式の指定だと読み替えません。

Microsoftの[IFEDictionary](https://learn.microsoft.com/en-us/windows/win32/api/msime/nn-msime-ifedictionary)は単語登録のCOM APIであり、辞書ツールのテキスト形式を定義していません。[スペルチェック辞書登録API](https://learn.microsoft.com/en-us/windows/win32/api/spellcheck/nf-spellcheck-iuserdictionariesregistrar-registeruserdictionary)のUTF-16LE仕様もMSIMEの一括登録仕様として流用しません。

Google製品とMozcは由来が共通ですが、それだけでは現在の製品版のインポーターが同一とは確認できません。製品仕様または実際の書き出しサンプルで確認後、互換性が確認できた処理だけを共通化します。

保留解消には、対象版の公式仕様または利用者自身のIMEから書き出した小規模サンプルとの比較が必要です。保留中のファイルや取り込み用サンプルは作りません。

## 管理用JSON・CSV

いずれもUTF-8、BOMなし、LFです。JSONはキー順を固定したオブジェクトで施設配列と登録配列を保持します。CSVは登録1件を1行とし、施設・登録のフィールドをそれぞれ `facility_`・`entry_` で区別して結合します。配列・オブジェクト値はJSON文字列にしてCSV引用規則で保存します。

CSVは `csv.DictWriter` によるカンマ・二重引用符・埋め込み改行の引用処理を使います。管理情報を含むため、これらをIMEへそのままインポートしません。要確認・除外レコードも保持し、IME用辞書の出力件数とは区別します。
