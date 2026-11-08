# 共通データと人手判断

## 正本

`common.json`はIMEに依存しない正本で、`schema_version`、`facilities`、`entries`、`collection`を持ちます。品詞のIME固有文字列、符号化、BOMは正本に置きません。`entries.semantic_type`は中立な`proper_noun`です。

| 区分 | 主なフィールド |
| --- | --- |
| 施設 | `id`, `agency`, `listed_name`, `name_raw`, `prefecture_code`, `prefecture`, `municipality`, `address` |
| 施設の出典 | `listing_url`, `source_locator`, `source_hash`, `page_hash`, `official_site_url`, `fetched_at`, `checked_at` |
| 登録 | `id`, `facility_id`, `surface`, `reading`, `semantic_type` |
| 登録の出典 | `name_raw`, `reading_raw`, `listing_url`, `reading_url`, `evidence`, `reading_source_kind`, `normalization`, `source_hash`, `page_hash`, `fetched_at`, `checked_at` |
| 状態 | 両レコードの`status`（`verified`・`pending`・`excluded`）と`reason` |
| 取得範囲 | `collection.source_rows_observed`, `selected_rows`, `limit`, `non_facility_rows`, `coverage`, `redistribution_status` |

`source_hash`は掲載名・カナ原文・所在地の組み合わせ、`page_hash`は取得したページ全体のSHA-256です。`source_locator`は掲載箇所の識別用で、施設の同一性は行番号だけで決定しません。

`reading_raw`は神社庁表のカナ欄を保持します。読みのNFKC・カタカナからひらがなへの変換は機械的操作です。空白・制御文字・漢字・英字などを含み、変換後も許容文字にならないものは推定せず要確認にします。表記・旧字体・異体字をこの正規化で変更しません。

施設の`verified`は名称・所在地の掲載確認、登録の`verified`は読みの根拠確認です。読みがない施設でも掲載自体は確認できるため状態を分離しています。辞書へ出せる確認済み施設数は、検証を通る登録と施設の両方が`verified`である施設IDの数です。

## IDと再取得

群馬の一覧には恒久的な施設コードがないため、初回の施設IDは神社庁識別子・掲載名・住所からUUIDを生成します。同名・別所在地は別IDです。同じ資料からの再生成では同じIDになります。

掲載名や住所の変更は単純な名称一致で統合しません。再取得で削除・追加が発生した場合、新規行を`pending`へ隔離し、人手で同一施設か確認します。隔離は再取得しても維持します。`collection.identity_history`と過去snapshotに旧ID・名称・所在地・出典根拠を保持します。

`identities.json`は、新しく観測した施設IDをキーとし、次の対応を保持します。

```json
{
  "NEW_FACILITY_ID": {
    "facility_id": "EXISTING_FACILITY_ID",
    "expected_source_hash": "CURRENT_SOURCE_ROW_SHA256",
    "reason": "実資料で改称・住所表記変更と同一施設を照合した具体的理由"
  }
}
```

これは入力構造の例で、実施設データではありません。対応先は永続履歴にあるIDに限り、複数の掲載行を同じIDへ統合する対応は拒否します。ID対応後も、人手判断の対象行hashが変わっていれば再確認が必要です。

## 修正・除外判断

`decisions.json`は登録IDをキーにする別ファイルです。収集処理は既存ファイルを上書きしません。

```json
{
  "ENTRY_ID": {
    "expected_source_hash": "SOURCE_ROW_SHA256",
    "status": "excluded",
    "reason": "除外と判断した具体的理由"
  }
}
```

元の掲載行が変わった場合は、判断を消さず適用結果を`pending`に戻します。取得済みの`reading_raw`・`name_raw`・表記・hashは判断ファイルから書き換えられません。神社庁由来の読みは元のrawとの正規化一致と行hashを検証します。

読みの補完は、**神社庁カナ欄が空の場合だけ**許可します。判断には`reading`、`supplemental_reading_raw`、`supplemental_name`、`supplemental_address`、`reading_url`、`reading_source_kind: shrine_official`、根拠`evidence`、確認日`checked_at`を含めます。名称・所在地は神社庁掲載値との一致が必要です。表記が食い違うものをこの実装で自動採用せず、要確認にします。

公式サイトが神社庁からリンクされている場合は、そのホストと読み確認先を照合します。リンクがない場合は、判断に`supplemental_official_verification`として、公式URL`url`、運営・施設同一性の根拠URL`evidence_url`、掲載された名称原文`name_raw`・所在地原文`address_raw`、短い確認根拠`evidence`、確認日`checked_at`、確認状態`status: verified`を保存します。これらは実際にページを閲覧して照合した人手判断であり、LLMの自信度を根拠にしてはいけません。

補完情報を足しても神社庁取得時の読み原文を変更しません。補完資料と神社庁資料が矛盾する場合は`pending`とし、推測で解決しないでください。

## 検証と原文照合

`validate`は必須項目・URL・状態・日時・文字種・IDの一意性・施設参照・原文との正規化一致・行hash等を検証します。辞書出力はこの検証を通った`verified`登録だけを対象にします。

`audit`はキャッシュ内の取得資料について、アダプターとは別の行抽出処理で名称・カナ原文・所在地を全件照合します。人手判断を重ねる前の取得原本を対象にします。補完先のウェブページの意味や発音の正しさを自動で判断する処理ではありません。補完先は人手で実資料との照合を行い、根拠を残す必要があります。

## データ利用条件

取得可能なこと、robots.txtで拒否されないこと、名称・読みが明示されていること、公開再配布が許されることは別の判断です。`redistribution_status: unconfirmed`のデータを、MIT許諾済みのデータセットとして扱いません。ローカルの取得資料・台帳を公開リポジトリへ持ち込まないでください。
