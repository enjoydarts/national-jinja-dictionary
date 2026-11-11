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

## ATOK：標準Shift JISの一括登録テキスト

対象は **ATOK for Mac 36.0.2（245128.3.0）**、辞書ユーティリティのShift JIS読み書き設定が **日本語（Shift JIS）** の場合です。[公式単語ファイル仕様](https://www.atok.com/other/support/howtouse/mac/dc/pgs/dc_word_file.htm)、[読み書きの設定](https://www.atok.com/other/support/howtouse/mac/mn/pgs/mn_tool_d_com_encoding.htm)、[品詞表](https://www.atok.com/other/support/howtouse/mac/shrd/shrd_hinsi_meisi.htm)と同版付属ヘルプを確認しました。

| 項目 | 採用した出力 |
| --- | --- |
| ヘッダー | `!!ATOK_TANGO_TEXT_HEADER_1` を先頭1行に出力 |
| 列・区切り | 読み・単語・品詞の3列、TAB。コメント等は省略 |
| 品詞 | 固有地名（品詞番号5）。場所としての特定施設名に対応 |
| 文字コード | Pythonの`shift_jis`で厳密に表現でき、復号後のUnicodeが一致する標準Shift JISの部分集合 |
| BOM・改行 | BOMなし、CRLF、最終行にもCRLF。プロジェクトが選んだ標準テキストの出力方針 |
| 長さ | 公式は読み32・単語100文字。実装は保守的にUTF-16コード単位で計数 |
| エスケープ | 引用形式なし。制御文字・不可視書式文字・行／段落区切り文字を拒否 |
| 行数上限 | 確認した資料に記載なし。無制限とは断定しない |

公式の[単語出力手順](https://www.atok.com/other/support/howtouse/mac/mn/pgs/mn_tool_ut_out_word_out_d.htm)は、Shift JISのテキストを単語一括処理に再利用できると説明しています。Unicode出力の厳密なバイト形式を推定せず、まずこの明記された入力経路に対応します。BOMなし・CRLFは実製品が書き出したファイルとの一致を確認した値ではありません。自動検査はこのプロジェクトの出力方針への適合を検査し、製品の受理を証明するものではありません。

`cp932`の拡張文字を無条件にShift JISとして出力しません。同じバイト列を`shift_jis`と`cp932`で復号しても原文のUnicodeに一致する行だけを採用し、符号化できない文字やマッピング差がある文字は理由付きで除外します。「𠮷」「髙」「神」等を「吉」「高」「神」へ置換しません。例えば「國」「驗」のようにこの部分集合で保持できる旧字体は、そのまま出力できます。正本は変更せず、ほかの形式へは各形式の条件で直接出力します。

実際のATOKへの取り込み・変換は**未実施**です。Windows版の確認も含みません。Unicode版は次節の別プロファイルを使います。[確認用手順](FORMAT_REVIEW.md)と、生成したサンプルの`report.json`で行数・除外理由を照合してください。

## ATOK：Unicodeの一括登録テキスト

出力名は **`atok_unicode.txt`**、形式キーは`atok_unicode`です。既存の`atok.txt`（標準Shift JIS版）と分けます。対象はATOK for Mac 36.0.2（245128.3.0）に同梱された **DicUtility 36.0.0（245010.75.0）のarm64実装**です。

| 項目 | 採用した出力 |
| --- | --- |
| 文字コード・BOM | UTF-16BE、先頭に`FE FF`を1回 |
| 改行 | CRLF。UTF-16BEでは`00 0D 00 0A` |
| ヘッダー・列・品詞 | 標準Shift JIS版と同じATOKヘッダー、TAB3列、固有地名 |
| 長さ・エスケープ | 読み32・単語100 UTF-16コード単位。制御文字等を拒否 |
| 字体 | 原文のUnicodeを保持。補助平面文字は2単位として数える。置換・切り詰めはしない |

公式ヘルプの「Unicode」は厳密なバイト形式を示さないため、指定版の公式プログラムの入出力処理を静的に照合しました。`CUTTangoFile`の`addUnicodeHeader`がBEのBOMを書き、`writeString:`がNSStringのUTF-16単位をBEへ変換してCRLFを書きます。`isUnicodeText`と`readString:maxLen:`で両方のBOMの認識とBE入力時の処理も確認しました。[実装確認情報](ATOK_UNICODE_EVIDENCE.json)に、版・SHA-256・確認した処理・確認範囲を保存しています。

これは実装の静的確認です。**製品パーサーへサンプルを実行投入した結果、実際の辞書登録結果、変換確認ではありません。** Unicode文字をファイル内に保持できることと、各IMEがすべての文字を登録・表示できることを区別します。

## Google日本語入力

対象は **Google日本語入力 for macOS 3.34.6260.1、同梱DictionaryToolのarm64実装**です。[公式配布ページ](https://www.google.co.jp/ime/)から得たパッケージの[製品識別情報](GOOGLE_PRODUCT_EVIDENCE.json)と、[辞書形式の実装確認情報](GOOGLE_FORMAT_EVIDENCE.json)を保存しています。

出力はMozc節と同じ**読み・表記・固有名詞の3列、TAB区切り、UTF-8、BOMなし、LF、各フィールド300 UTF-8バイト以下、100万行以下**です。名称の品詞として固有名詞を使います。Google製品内の品詞表でも「固有名詞」（enum値4）を確認しました。

Google製品の`TextInputIterator::Next`は先頭3列を読み・単語・品詞として扱い、4列目のコメントを任意に受け付けます。`MultiByteTextLineIterator`はUTF-8の行を処理し、`ValidateEntry`はUTF-8の妥当性と300バイト上限を検査します。`UserDictionaryStorage::IsDictionaryFull`の100万行境界も確認しました。**製品の書き出しはコメントを含む4列**ですが、このプロジェクトは、受け付けられる部分集合であるコメントなし3列を出力します。

この確認に基づき、3列TSVの整形・重複除去・バイト上限・形式検査をMozcと共通化しました。製品版がMozcに由来するという理由だけでは共通化していません。異なる版・Windows版・製品全体の互換性や、実際の取り込み・変換の確認は含みません。

## 公式実装の読み取り専用再照合

macOSとCommand Line Toolsがある環境で、レビュー対象と同じ実体を照合できます。Googleは公式パッケージをインストールせず展開したDictionaryToolのパスを指定します。

```sh
python3 tools/check_ime_implementations.py --atok
python3 tools/check_ime_implementations.py --google-binary "/path/to/DictionaryTool.app/Contents/MacOS/DictionaryTool"
```

このチェックは製品を起動せず、辞書・設定を開きません。SHA-256とレビュー済みの関数・定数等の構造、Googleの品詞表を再照合します。違う実体なら停止します。任意の新バージョンのプログラムを自動的に正しいと判定する機能ではなく、プログラムの意味の自動証明でもありません。通常の辞書生成はこの環境や製品のインストールに依存せず、Pythonだけでオフライン実行できます。製品本体や逆アセンブル本文を公開リポジトリに含めません。

## Microsoft IME

対象は **Microsoft IMEユーザー辞書ツール IMJPDCT.EXE 10.0.26100.9818（x64）** の一括登録テキストです。これはコンポーネント自身のファイルバージョンで、起動したWindowsのOSビルド番号ではありません。実機のOSビルドや新旧IMEモードは未確認です。

[Microsoft公式の公開シンボルサーバー](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/microsoft-public-symbols)から、指定版EXEと対応する公開PDBを取得し、GUID・DBI age・SHA-256を照合しました。[確認情報](MSIME_FORMAT_EVIDENCE.json)に、Microsoftの直接取得URL・製品版・実体hash・確認した処理を保存しています。配布先を発見するために用いた第三者索引を、形式仕様の根拠にはしません。

| 項目 | 採用した出力 |
| --- | --- |
| 文字コード・BOM | UTF-16LE、先頭に`FF FE`を1回 |
| 改行 | CRLF。UTF-16LEでは`0D 00 0A 00` |
| ヘッダー | 下記の3行。`!Version:`の値は空 |
| 列・区切り | 読み・単語・品詞の3列、TAB。任意コメントは省略 |
| 品詞 | 固有名詞。入力可能な公式品詞表のID `0x76` |
| 長さ | 読み・単語それぞれ60 UTF-16コード単位以下 |
| エスケープ | 引用形式なし。制御文字・不可視書式文字・行／段落区切り文字を拒否 |
| 総容量 | 確認範囲では未確定。既存ユーザー辞書の空き容量も測定していないため、無制限とは主張しない |

```text
!Microsoft IME Dictionary Tool
!Version:
!Format:WORDLIST
```

`CVdrMS::WriteHeader`のヘッダー表にある先頭3項目を採用します。製品のネイティブ出力は、辞書名・出力ファイル名・日時等を含む計7項目で、上の3行は`GetFormatW`が受け付ける最小構成です。ネイティブ出力全体とのバイト一致を主張しません。`!Version:`は製品内でも値のないリテラルであり、`!Version:1`やOSビルド等を推測で付けません。

`CText::IsUnicodeText`のBOM判別、`CVdrMS::WriteHeader`のUnicode出力、`WriteLineWord`のTAB3列と任意コメント、`SetDataW`の3／4項目の入力を確認しました。`SetWordW`は読みと単語のUTF-16単位数をそれぞれ60と比較して検査します。神社という特定施設名を、入力が有効な「固有名詞」へ対応づけます。補助平面文字は2単位として計数し、切り詰めず理由付きで除外します。

これは公式実装の**静的なファイル形式照合**です。Windows上での製品パーサー実行、ユーザー辞書への登録成功、登録エンジンがすべてのUnicode文字や読みを受理すること、変換候補への反映を確認したものではありません。[取り込み確認手順](FORMAT_REVIEW.md)に従い、生成レポートと実機の受理・拒否件数を照合してください。

LLVM objdumpがある環境で、同じEXE/PDBを読み取り専用で再照合できます。スクリプト自身はダウンロードせず、製品も起動しません。違う実体は停止し、新しい版を自動的に認定しません。

```sh
python3 tools/check_msime_implementation.py --exe "/path/to/imjpdct.exe" --pdb "/path/to/imjpdct.pdb"
```

[Microsoftの利用条件](https://learn.microsoft.com/en-us/legal/windows-sdk/microsoft-symbol-server-license-terms)に従い、自作の辞書出力とMicrosoft IMEの互換性検証のために確認しました。製品・PDB・逆アセンブル本文は配布しません。通常の辞書生成にWindowsやEXE/PDB、objdumpは不要です。

ATOKの一括処理画面のUnicode指定は未登録語ファイルの出力用であり、入力形式の指定だと読み替えません。旧版の単語64文字制限も現行版へ流用しません。

Microsoftの[IFEDictionary](https://learn.microsoft.com/en-us/windows/win32/api/msime/nn-msime-ifedictionary)は単語登録のCOM APIであり、辞書ツールのテキスト形式を定義していません。[スペルチェック辞書登録API](https://learn.microsoft.com/en-us/windows/win32/api/spellcheck/nf-spellcheck-iuserdictionariesregistrar-registeruserdictionary)のUTF-16LE仕様もMSIMEの一括登録仕様として流用しません。

初版対象の全IME形式に生成処理があります。各形式の自動検査・実装照合と、実際のIMEへの取り込み確認は引き続き区別します。

## 管理用JSON・CSV

いずれもUTF-8、BOMなし、LFです。JSONはキー順を固定したオブジェクトで施設配列と登録配列を保持します。CSVは登録1件を1行とし、施設・登録のフィールドをそれぞれ `facility_`・`entry_` で区別して結合します。配列・オブジェクト値はJSON文字列にしてCSV引用規則で保存します。

CSVは `csv.DictWriter` によるカンマ・二重引用符・埋め込み改行の引用処理を使います。管理情報を含むため、これらをIMEへそのままインポートしません。要確認・除外レコードも保持し、IME用辞書の出力件数とは区別します。
