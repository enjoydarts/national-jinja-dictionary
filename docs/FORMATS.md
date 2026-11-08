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

## 保留しているIME形式

| 形式 | 確認した資料・対象 | 品詞の候補と理由 | 出力を保留する不足情報 |
| --- | --- | --- | --- |
| ATOK | [テキスト形式FAQ 025489](https://support.justsystems.com/faq/1032/app/servlet/qadoc?QID=025489)（ATOK 2005/18）、[品詞FAQ 040814](https://support.justsystems.com/faq/1032/app/servlet/qadoc?QID=040814)（ATOK 2008） | 固有地名：場所としての特定施設名。現行版では未確定 | 現行対象版、Unicodeの符号化・BOM、改行・エスケープ等 |
| Google日本語入力 | [公式辞書ヘルプ](https://support.google.com/ime/japanese/answer/166765?hl=ja)、[Mozcのブランド説明](https://github.com/google/mozc/blob/d918f30063999d4ca250f76ced8b92169a0e0b25/docs/about_branding.md) | 固有名詞を検討。製品の品詞表と照合待ち | 製品版の一括形式・対象バージョン・インポートサンプル |
| Microsoft IME | [公式サポート](https://support.microsoft.com/ja-jp/windows/hardware/input-devices/microsoft-japanese-ime)（Windows 10/11） | 地名・固有名詞等の正式な対応名を確認して決定 | 一括形式、品詞、文字コード、BOM、改行、制限、対象ビルド |
| macOS追加辞書 | [日本語入力の追加辞書ガイド](https://support.apple.com/ja-jp/guide/japanese-input-method/-jpim10226/mac) | 地名：施設の場所の名称としての設計候補 | 固定したmacOS版、文字コード・BOM・改行バイト列・文字数の厳密な計数 |

ATOKの上記旧版資料には `!!ATOK_TANGO_TEXT_HEADER_1`、TAB区切りの読み・単語・品詞、読み32・単語64の制約があります。濁点・半濁点の計数にも注意が必要であり、これをそのまま現行版プロファイルとしては採用していません。

Appleガイドには読み・単語・品詞のCSV、読み32文字・単語64文字・1行127文字の制限などがあります。追加辞書をテキスト置換のplist等と混同しません。詳細が不明な符号化・文字計数を推測で補って出力することはしません。

Google製品とMozcは由来が共通ですが、それだけでは現在の製品版のインポーターが同一とは確認できません。製品仕様または実際の書き出しサンプルで確認後、互換性が確認できた処理だけを共通化します。

保留解消には、対象版の公式仕様または利用者自身のIMEから書き出した小規模サンプルとの比較が必要です。保留中のファイルや取り込み用サンプルは作りません。

## 管理用JSON・CSV

いずれもUTF-8、BOMなし、LFです。JSONはキー順を固定したオブジェクトで施設配列と登録配列を保持します。CSVは登録1件を1行とし、施設・登録のフィールドをそれぞれ `facility_`・`entry_` で区別して結合します。配列・オブジェクト値はJSON文字列にしてCSV引用規則で保存します。

CSVは `csv.DictWriter` によるカンマ・二重引用符・埋め込み改行の引用処理を使います。管理情報を含むため、これらをIMEへそのままインポートしません。要確認・除外レコードも保持し、IME用辞書の出力件数とは区別します。
