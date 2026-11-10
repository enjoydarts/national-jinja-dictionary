# 全国神社辞書

National Jinja Dictionary — 神社庁の公式掲載情報と、利用できない掲載情報を補う参考資料から、出典付きの神社辞書を生成するPythonプロジェクトです。旅行先の神社名や難読名の入力を助けるため、件数より名称・読みの正確さを優先します。

## 正本と配布物

**辞書の正本はこのリポジトリの [`data/sources/`](data/sources/) に保存します。** 名称・読みの原文、所在地、出典、取得日、検証状態を持つ施設・登録レコードです。クローリングのたびにしか辞書を作れない構成ではありません。

神社庁原文にない所在地の根拠は[`data/locations.json`](data/locations.json)、読み・表記の補正は[`data/corrections.json`](data/corrections.json)へ分けて保存します。所在地を補完した場合も、神社庁の空欄と施設公式の所在地を区別して保持します。これらも正本の一部として、検証・辞書生成・リリースへ自動適用します。

```text
収集・資料照合 → data/の正本を更新・レビュー・コミット
                              ↓
              リリース対象のコミットをチェックアウト
                              ↓
             正本を検証 → オフラインで各辞書を新規生成
                              ↓
                GitHub ReleaseへZIP・SHA-256・出典情報を添付
```

生成辞書はReleaseの配布物とし、古い生成ファイルをリポジトリへ常備して配布する方法は使いません。リリース中に再クロールして未確認データへ置き換える処理もありません。最新の掲載情報を反映するときは、先に正本を更新してコミットします。

Obsidianに残すのは作業記録・判断経緯などのノートだけです。取得HTML・画像・HTTPキャッシュはGit対象外のキャッシュ領域に置き、正本と分離します。

## 対応範囲

47都道府県を対象に収集を進めています。47県すべてに施設正本があります。神社庁資料を収集した41県と、Wikipedia参考資料枠の6県376施設（和歌山93・広島58・山口42・徳島99・大分53・宮崎31）を区別しています。宮崎県では神道青年会の独自紹介590施設も別区分で保持します。全体では、同一施設の重複掲載を整理した54,646施設レコードのうち43,419施設が辞書への出力条件を満たし、重複除去後は13,433行です。元掲載の管理レコード56,751件は別に保持し、確認できた重複掲載観測2,105件を施設数へ二重計上しません。47県すべてに読み確認済みの施設がありますが、県内全施設の網羅とは異なります。参考資料枠を神社庁掲載確認済みとは扱いません。[47都道府県の情報源・利用条件](docs/SOURCES.md)と、地域ごとの取得状態・掲載範囲・件数・停止理由は [`data/manifest.json`](data/manifest.json)、施設の出典と検証状態は各正本を参照してください。全国版というファイル名は全国の全神社を網羅したことを意味しません。

| 出力 | 状態 | 実機への取り込み |
| --- | --- | --- |
| Mozc | 固定コミットの公式実装に基づくTSV生成・自動検証 | 未実施 |
| JSON・CSV | 出典・所在地・原文・検証状態を含む管理データ | IME用ではない |
| ATOK | 現行版・符号化・BOM等の確認不足で保留 | 未実施 |
| Google日本語入力 | 製品側の一括形式・対象版未確定で保留 | 未実施 |
| Microsoft IME | 公式一括形式・対象ビルド未確定で保留 | 未実施 |
| macOS追加辞書 | macOS 27の公式仕様・指定版の公式解析処理に基づくCSV生成 | インストール・変換確認は未実施 |

macOSは公式解析処理との全フィールド照合を行っています。追加辞書のインストール・変換確認とは区別します。保留形式のファイルは推測で生成しません。Google日本語入力とMozcの完全互換は未確認です。macOS追加辞書はユーザ辞書・テキスト置換とは区別し、iPhone直接取り込みやデバイス間同期は対象外です。[出力仕様と品詞対応](docs/FORMATS.md)に根拠と不足情報を記載しています。

判断が必要な外字・読みの食い違いは **[判断待ち一覧](docs/REVIEW.md)** に原文・候補・根拠・選択肢をまとめています。保留中のIME形式に必要な実製品資料は **[形式確認の依頼一覧](docs/FORMAT_REVIEW.md)** に分けています。

## セットアップ

Python **3.15.2以上**を使います。`.python-version`は3.15.2、実行時の外部依存はありません。HTTP収集のプロセス間ロックはmacOS/Linuxを対象とします。

```sh
git clone https://github.com/enjoydarts/national-jinja-dictionary.git
cd national-jinja-dictionary
python3 --version
python3 -m unittest discover -s tests -v
python3 -m njd --help
```

パッケージとして利用する場合は `python3 -m pip install -e .` でコマンドを追加できます。

## 正本からのオフライン生成

クローンしたリポジトリの正本だけで生成できます。`validate`と`build`はネット接続しません。

```sh
python3 -m njd validate
python3 -m njd build --formats mozc,macos,json,csv
python3 -m njd build --formats mozc --prefecture 10
```

既定の出力先は `dist/dictionaries/` です。全国版は `national/`、県別は `prefectures/NN/`、取り込み確認用サンプルは `samples/` に生成します。指定形式だけの生成にも対応します。`build`は出力先を今回指定した形式・地域だけへ置き換えるため、保管する配布物はReleaseを利用してください。

`--data-dir`で正本の場所、`--output-dir`で出力先を指定できます。旧`--workspace`は移行用の互換オプションです。

`build --formats all`は保留形式も評価し、実装済み形式だけを書き出します。保留内容を`report.json`へ残して終了コード2を返します。通常成功は0、データ検証・取得エラー等は1です。保留と不正データを区別します。

## 正本の最新化

```sh
# 正本を置き換えず、別ディレクトリーで少量の抽出を確認
python3 -m njd --data-dir /tmp/njd-pilot collect gunma --limit 100

# 指定神社庁の全掲載範囲を収集（0は上限なし）
python3 -m njd collect gunma --limit 0

# 実装済みの全神社庁。失敗した地域の前回正本は消さない
python3 -m njd collect all --limit 0

# 必要なときだけページを更新。通常はキャッシュを再利用
python3 -m njd collect gunma --limit 0 --refresh
python3 -m njd collect gunma --limit 0 --offline

python3 -m njd validate
git diff -- data/
```

取得先の規約・robots・制限を確認してから実行してください。`--cache-dir`の既定値はリポジトリ外の `~/.cache/national-jinja-dictionary/http` です。同一ホストの間隔は最低2秒とし、異なるホストは独立して取得できます。キャッシュ、タイムアウト、再試行、途中再開、24時間ごとのオンラインrobots再確認を備えます。アクセス拒否や規則の判定不能を回避しません。

岐阜は取得・照合した1,815施設、兵庫は選択した地図検索の応答3,834施設を収録し、京都は公開31地域一覧の1,581施設を保存しています。京都は237施設の全文読みを補完しています。福岡は公開4地域一覧280施設の掲載範囲を保存しています。各地域の自動収集範囲と未実装範囲は情報源一覧を参照してください。岐阜の828表示は一覧の名称・読みの登録行数で、異なる名称の数・県内施設総数とは区別します。

`collect all`による京都・福岡の更新には対応していません。兵庫は公式地図検索が返した施設コードの詳細取得に対応し、`collect hyogo --limit 100` で試作できます。選択した矩形の応答範囲であり、県全体や掲載全件の保証はありません。岐阜も自動収集に対応し、`collect gifu --limit 0` で保存済みキャッシュから再開できます。更新時は正本の`listing_url`を開き、名称・全文カナ・所在地・施設IDを照合し、原文・ページhash・確認日と変更差分をレビューします。辞書生成は、この個別確認データも他県と同じ正本として使用します。

新潟のrobotsは公式トップへの転送後にHTMLを返します。[RFC 9309の解析方針](https://www.rfc-editor.org/rfc/rfc9309.html#section-2.3.1.5)と[GoogleのHTML応答の説明](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec)を確認し、レジストリの`reviewed_html_robots`へ記録した接続元だけで有効な指示を行単位で解析します。禁止指示、解釈できない指示、認証・challenge・HTTP失敗では停止します。取得条件と再配布条件は情報源一覧に別々に記録します。

限定・途中取得で前回の施設が含まれなくなった場合は、前回の正本を保持して状態と理由を記録します。保存済みの範囲を含む部分収集の拡張は保存できます。

再収集時の件数は、所在地補完・読み補正・資料確認・人手判断・重複掲載整理を、辞書生成と同じ順序で適用して計算します。補正ファイルの検証や集計に失敗した場合は、新しい取得結果で正本を置き換えません。施設数・適格施設数・重複除去後の辞書行数・保留登録数を区別し、元の取得行は補正済みの値で上書きしません。

取得結果だけで名称・読みを確定できない登録は`pending`に残し、辞書には出しません。読みの推定や通称・略称追加はしません。壊れた読み・名称欄や外字は、行政資料・Wikipedia等で所在地と全文表記・読みを照合できた場合に限り、`data/corrections.json`へ根拠付きの補正を保存します。原文と旧字体・異体字は保持し、資料の矛盾が解決しない候補は出力しません。人手判断は`data/decisions.json`、ID対応は`data/identities.json`で保持します。[データ仕様](docs/DATA.md)を参照してください。

## 独立資料による読みの補完

神社庁に読みがない施設は、施設公式サイトやWikipedia等の実資料と名称・所在地・全文読みを照合します。調査入口のjinja-net.jpを辞書の出典として使いません。

```sh
# 保存先はリポジトリ外。カテゴリ一覧を取得してから記事を調査
python3 -m njd.wikipedia --prefecture all --state-dir /tmp/njd-reference-research --inventory-only
python3 -m njd.wikipedia --prefecture all --state-dir /tmp/njd-reference-research --limit 100

# 神社庁の一覧が直接リンクする詳細ページの読みを優先して収集
python3 -m njd.agency_details --source shimane --state-dir /tmp/njd-shimane-details --limit 100
python3 -m njd.agency_details --source nagano --state-dir /tmp/njd-nagano-details --limit 100
# 滋賀：保存した一覧の実リンクから県単位で調査。上限0で全対象、同じstateで再開
python3 -m njd.agency_details --source shiga --state-dir /tmp/njd-shiga-details --limit 0

# 国税庁の無償公開データ。既存の神社庁掲載名・所在地との一致だけを候補化
python3 -m njd.corporate --prefecture all --state-dir /tmp/njd-corporate-research --limit 3

# キャッシュを使った抽出の再確認
python3 -m njd.wikipedia --prefecture 32 --state-dir /tmp/njd-reference-research --offline --recheck

# 案の全件検証と差分確認後、正本へ適用（既存判断を上書きしない）
python3 -m njd.proposals --input /tmp/njd-reference-research/proposals.json
python3 -m njd.proposals --input /tmp/njd-reference-research/proposals.json --apply
# 神社庁の詳細で新しく確認した読みを二次資料より優先（従来の根拠は保持）
python3 -m njd.proposals --input /tmp/njd-shimane-details/proposals.json --prefer-agency --apply
python3 -m njd validate
git diff -- data/corrections.json
```

国税庁のフリガナは未掲載・大書きカナ・閉鎖法人などを含むため、そのまま全件を採用しません。読みを推定せず、存続する一意な法人の正式名称・所在地・明示カナを照合します。出典・加工表示・公共データ利用規約は補完レコードへ保存し、コードのMITと区別します。

調査状態の`complete`は指定カテゴリの候補調査の完了で、読みの全国網羅を意味しません。未発見・取得失敗・所在地不一致・読みの衝突は外部の`state/progress.json`に残ります。仕様と確認範囲は[データ仕様](docs/DATA.md)を参照してください。

滋賀の詳細調査は、一覧の同じ掲載行から取得したhref・施設番号・名称・所在地を照合します。詳細の別称をカナと分離し、全文カナだけを採用候補にします。語幹だけのカナは補完せず、外部の調査状態に原文と保留理由を残します。取得に失敗した場合は県の処理を止め、確認前に正本や既存判断を書き換えません。候補には既存補正と重なるものもあるため、差分を確認して採用対象を選びます。

## リリース時の最新生成

通常のpush・PRのCIは自動テストと正本検証を行います。全国版・県別版の一括生成はリリース処理で行い、通常CIでは全国版ZIPを毎回生成しません。出力形式とリリース処理の回帰確認は、小さな人工データの自動テストで継続します。

正本とコードをコミットした後、リリース対象コミットの`v*`タグをpushすると[Release workflow](.github/workflows/release.yml)が実行されます。手動実行では既存タグを指定します。

1. タグの正本とコードをチェックアウト。
2. 自動テストと正本検証を実行。
3. 正本から新しく辞書・サンプル・件数レポートを生成。
4. ZIP、`SHA256SUMS`、`SOURCE.json`をGitHub Releaseへ添付。

`SOURCE.json`に正本コミット、各入力ファイルのSHA-256、検証済みデータのhashを含めます。情報源一覧・補正ファイルも同梱します。ZIP内のファイル順・時刻を固定し、同じ実行環境・正本・版から同じ内容を再生成できます。

ローカルでの同じ生成処理：

```sh
python3 -m njd.release --version v0.2.0
```

これはローカル生成だけで、Releaseの作成やタグのpushは行いません。GitHub側のworkflow実行と実際のIME取り込みは、ローカルの生成テストとは別に確認します。

## 件数と取り込み確認

レポートは施設レコード数、確認済み施設数、重複除去後辞書行数、形式ごとの行数を分けます。JSON・CSVの件数は未確認・除外を含む管理レコード数で、IME用語数とは異なります。取得数、神社庁の掲載総数、地域の全神社数を同一視しません。

Mozcでは先に `samples/national/mozc.txt` を試験用ユーザー辞書へインポートし、同フォルダーのmanifestと読み・表記・異体字を照合してください。同名施設が同じ候補になる場合も、manifestには各施設が残ります。難読名を含めるには `build --sample-name 倭文神社` のように実在する収録名を指定できます。

macOS 27では `samples/national/macos.txt` を先に試してください。日本語入力ソースの設定を開き、「追加辞書」ボックスへドラッグします。ユーザ辞書のテキスト置換とは別の機能です。対応するmanifestと読み・表記・異体字を照合してから全国版を使用してください。対象版と制限は[出力仕様](docs/FORMATS.md)にあります。

全形式の実機取り込みは未確認です。自動形式チェック・資料照合の成功を動作確認済みとは表示しません。テスト内の神社・住所は架空で、実施設の出典には使用しません。

## ライセンス

ソースコード・プロジェクト文書は[MIT License](LICENSE)です。収集元の資料・データの利用条件は出典別に管理し、コードのMIT表示で上書きしません。利用条件未確認のものを許諾済みとは表示しません。取得ページ本文や画像は配布しません。有料APIの契約・課金は行いません。

## 神社庁資料を利用できない地域の参考資料枠

神社庁資料を利用できない6県（和歌山・広島・山口・徳島・大分・宮崎）では、Wikipediaの記事を直接確認した施設を別の根拠区分で収録します。各県の神社庁資料の収集停止・閉鎖案内・公式本文やURLの未確認状態は維持します。施設の `listing_basis=wikipedia_reference`、`source_publisher`、`source_reference` に名称・全文カナ・所在地・記事ID・版ID・出典・CC BY-SA 4.0を保存します。旧字体や異体字は記事の掲載名を保持し、略称や別名は追加しません。神社以外の記事や全文読みを確定できない記事は収録せず、`collection.article_reviews` にURLと理由を残します。

```sh
# 参考資料の取得と照合候補の作成。正本を直接上書きしません。
python3 -m njd.reference_sources --prefecture 34 --state-dir /tmp/njd-reference-34
python3 -m njd.reference_sources --prefecture 35 --state-dir /tmp/njd-reference-35
# 30（和歌山）・36（徳島）・44（大分）・45（宮崎）も同じ方法で実行
# 保存済みキャッシュだけで再開する場合は --offline、更新取得は --refresh
# 抽出処理の変更後は、新しいstate-dirを指定し --offline で全記事を再検査
```

`candidate.json` の出典・未収録記事・既存正本との差分を確認してから、共通保存処理 `njd.nationwide.save_collection` で `data/sources/` へ保存し、県別件数と情報源一覧を更新してコミットします。取得失敗は確認済みに数えず、次の再開対象として残します。既存の補正・人手判断は別ファイルで保持します。記事由来の帰属・版・ライセンス情報はリリースの `ATTRIBUTION.json` にも含めます。Wikipedia由来データへソースコードのMITライセンスを無断適用しません。


## 情報表以外の個別資料照合

自動抽出できない記事も、本文の主名称・全文カナ・所在地・神社である記述を個別に照合し、出典付きで正本へ保存します。1記事が複数施設を説明するときは、実際の各施設の名称と住所を分離します。例として日田市の八坂神社2施設は元本では別レコード、同じ読み・表記のIME行は1行です。日前神宮と國懸神宮もそれぞれの名称・読みを登録し、総称や略称は加えていません。

これらの参照は `acquisition_method=individual_source_review`、施設は `curated_source_record=true` を持ちます。新しい自動収集案に当該施設がない場合、`save_collection` は完全取得表示でも前回正本の置き換えを拒否します。差分を実資料で照合し、既存の個別参照を含む案を作成してください。個別参照の更新は照合後に `save_collection(..., reviewed_curated=True)` を使用し、旧参照は `curated_reference_history` に保持します。欠落はこの指定でも自動削除しません。読みの判断や原文の変更を、取得処理だけで上書きしないための保存規則です。

## 宮崎県神道青年会の独自神社紹介

宮崎県では[宮崎県神道青年会の紹介一覧](https://www.m-shinsei.jp/shrine/)も、`association_reference`として区別します。団体自身の紹介ページで発行者を照合しています。神社庁からの委託・神社庁掲載は確認しておらず、Wikipediaの出典・ライセンスとも別です。再利用条件は未確認です。本文や画像を配布せず、名称・全文読み・所在地・短い照合記録を正本へ保持します。

```sh
# 外部作業ディレクトリーへ一覧を取得。公開リポジトリを直接更新しません。
python3 -m njd.association_sources --state-dir /tmp/njd-miyazaki-youth --limit 60
# 続きから全一覧を取得し、実リンク先の詳細50件と対照
python3 -m njd.association_sources --state-dir /tmp/njd-miyazaki-youth --audit-profiles 50
# 保存済みキャッシュで候補作成。既存施設との重複候補を保留
python3 -m njd.association_sources --state-dir /tmp/njd-miyazaki-youth --offline --prepare-with-data-dir data
```

`--limit`はページ終了時の停止目安です。キャッシュ・調査状態は再利用し、更新取得には`--refresh`を指定します。抽出規則を変えた後は、新しい`state-dir`と`--offline`で保存済みページを再検査してください。`--cache-dir`で既存の外部キャッシュを指定できます。

`candidate.json`の原文・出典・差分を照合してから、`save_collection(data_dir, 'miyazaki_youth', candidate)`で保存し、manifestと情報源一覧を更新します。再生成時には既存の同じ情報源を重複候補扱いにしません。別情報源と名称が一致する場合、または番地の表記差を除いて所在地が一致する場合は、自動統合・重複追加せず`identity_reviews`へ回します。所在地注記は同じ掲載枠の住所との文字列照合時のみ分離し、別称は自動追加しません。郵便番号は空欄・表記差を含む原文の管理情報で、読みの補完には使いません。

リリースの`source-reviews.json`に、施設レコードを作る前の未確定な掲載枠・記事・施設同一性の候補も含めます。`pending.json`の施設数とは区別してください。現在の一覧649掲載枠は、発行者が説明する「650社掲載を目指す」という目標や宮崎県内の全神社数と同じ意味ではありません。


## 同一施設の重複掲載と人手の保留

高知の同じ名称・全地番を持つ2種類の掲載行2,105組は、出典・原ID・原文hashを`data/source_aliases.json`で束縛して整理します。元の全レコードと人手判断を削除しません。複数掲載行による曖昧一致が理由だった9施設の読みは、実記事と同一性証拠を再確認し、以前の保留履歴を残して採用しています。未解決の人手保留・読みの矛盾・出典項目の変化があれば両方を保留する規則は維持します。

件数レポートの`facilities`は整理後の施設レコード数、`facility_records`は元の全管理レコード数、`source_alias_records`は適用した重複掲載観測数です。JSON/CSVは重複観測も管理情報として保持し、IMEの語数と区別します。未解決の同一性まで確定した件数とは扱いません。


## 登録画像のある政府資料の個別照合

国税庁のUnicode CSVで名称と全地番が一致し、一意な存続法人と全文カナを確認できた場合も、登録画像IDがある行を自動採用しません。公式画像を個別に開いて名称・住所との対応を確認した41施設は、`image_reviews`へ画像ID・URL・元バイトhash・取得日/確認日・同じCSVの法人番号/snapshot/ZIP hash/行番号を残しています。画像の字形やUnicode版との対応を保存し、出力名は神社庁掲載名のままにします。読みはCSVに明示された全文カナだけで、画像や漢字から生成しません。

通常の`njd.corporate`収集は未検査の画像行を引き続き保留します。個別照合の登録は`corporate._proposal(..., image_reviews=packet)`と共通の`correction_problems`検証を通し、採用後は`data/corrections.json`から再生成します。取得HTML・CSV全体・画像は配布しません。画像の存在は、文字コード変換や読み補完の許可を意味しません。
