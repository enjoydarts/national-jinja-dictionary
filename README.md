# 全国神社辞書

National Jinja Dictionary — 調査した各都道府県神社庁の公式掲載情報に基づく辞書を、出典付き共通データから生成するPythonプロジェクトです。

旅行先の神社名や難読名の入力を助けるため、名称・読みの正確さと変換候補の使いやすさを優先します。

## 対応範囲

初版の実装対象は群馬県神社庁の[県内神社紹介](https://www.gunma-jinjacho.jp/jinja/)です。同じ表行の名称・カナ・所在地を根拠にします。47都道府県の初回情報源調査は実施しましたが、他46都道府県の収集アダプターは未実装です。県ごとの公式性・掲載範囲・利用条件等の調査台帳はObsidianで管理しています。

| 出力 | 実装状態 | 実際のIMEへの取り込み |
| --- | --- | --- |
| Mozc | 固定コミットの公式実装に基づくTSV生成・自動検証 | 未実施 |
| JSON・CSV | 出典・所在地・原文・検証状態を含む管理データ | IME取り込み用ではない |
| ATOK | 保留：現行版、符号化・BOM等の確認不足 | 未実施 |
| Google日本語入力 | 保留：製品側のインポート仕様・対象版未確定 | 未実施 |
| Microsoft IME | 保留：公式の一括取り込み仕様・対象版未確定 | 未実施 |
| macOS追加辞書 | 保留：CSV仕様の一部を確認、符号化等未確定 | 未実施 |

保留形式のファイルは生成しません。Google日本語入力とMozcの完全互換は確認できておらず、共通形式と決めつけません。macOSの追加辞書はユーザ辞書・テキスト置換とは別です。iPhoneへの直接取り込みやAppleデバイス間同期は対象外です。

収集データ・生成辞書の再配布条件は未確認のため、このリポジトリではコードと利用者向け文書を公開しています。ローカルの共通データと生成物はリポジトリ外に保存してください。全国版ファイルも**収集した地域のデータだけ**を含み、全国網羅を意味しません。

## 環境と実行

[Python公式](https://www.python.org/downloads/)で確認した最新安定版、Python **3.15.2以上**を使います。`.python-version`は3.15.2です。実行時の外部依存ライブラリはありません。HTTP収集のプロセス間ロックはmacOS/LinuxのPOSIX環境を対象とします。

```sh
git clone https://github.com/enjoydarts/national-jinja-dictionary.git
cd national-jinja-dictionary
python3 --version
python3 -m njd --help
python3 -m unittest discover -s tests -v
```

パッケージとして利用する場合は `python3 -m pip install -e .` で `national-jinja-dictionary` コマンドを追加できます。ビルドにはsetuptoolsを使用します。

## 収集・再生成

`NJD_WORKSPACE`は利用者自身のObsidianフォルダーなど、**このリポジトリの外**を指定します。以下の保存先は例です。

```sh
NJD_WORKSPACE="$HOME/Documents/Obsidian/全国神社辞書/artifacts"

# まず100施設まで試作
python3 -m njd --workspace "$NJD_WORKSPACE" collect gunma --limit 100
python3 -m njd --workspace "$NJD_WORKSPACE" validate
python3 -m njd --workspace "$NJD_WORKSPACE" audit

# 確認できた形式を一括生成
python3 -m njd --workspace "$NJD_WORKSPACE" build --formats mozc,json,csv \
  --sample-name 倭文神社 --sample-name 大國神社

# 指定形式・指定県のみ
python3 -m njd --workspace "$NJD_WORKSPACE" build --formats mozc --prefecture 10

# キャッシュから再開。0は観測できた全施設行を選択する指定
python3 -m njd --workspace "$NJD_WORKSPACE" collect gunma --limit 0 --offline
python3 -m njd --workspace "$NJD_WORKSPACE" validate
python3 -m njd --workspace "$NJD_WORKSPACE" audit
python3 -m njd --workspace "$NJD_WORKSPACE" build --formats mozc,json,csv
python3 -m njd --workspace "$NJD_WORKSPACE" report
```

`--refresh`はページとrobots.txtを再確認します。通常はキャッシュを使い、同じページを不要に取得しません。オンライン時のrobotsキャッシュは24時間で再確認します。ネットワークなしでの再取得再開には `--offline` を使います。キャッシュ破損、robotsの拒否や判定不能、アクセス拒否は停止理由として返します。404のrobots.txtをデータ再利用の許諾とは扱いません。

`build --formats all`（既定値）は全形式を評価し、確認済み形式だけを書き出します。保留形式と不足情報は `generated/report.json` に記録し、終了コード **2** を返します。正常生成は0、検証・取得などのエラーは1です。

`build`のたびに `generated/` はその実行で指定した形式・地域だけへ置き換わります。残したい出力は別の外部フォルダーへ保管してください。共通データ・判断ファイル・キャッシュは保持します。

## 保存物

すべて `NJD_WORKSPACE` 配下へ保存します。取得本文、作業ログ、台帳、個人の環境情報を公開リポジトリへコミットしないでください。

| パス | 内容 |
| --- | --- |
| `common.json` | IMEに依存しない正本。施設と登録を分離 |
| `decisions.json` | 人手の修正・除外判断。再取得時に上書きしない |
| `identities.json` | 改称・住所変更時の人手によるID対応 |
| `snapshots/`、`changes.json` | 前回データと追加・削除・変更の差分 |
| `cache/` | URL・取得日時・hash付き取得キャッシュ |
| `pending.json`、`excluded.json` | 要確認・除外の登録リスト |
| `validation.json` | データ検証結果 |
| `source-audit.json` | 取得資料との全件照合結果 |
| `generated/national/` | 収集済み範囲の全国版 |
| `generated/prefectures/10/` | 群馬県版 |
| `generated/samples/` | 取り込み確認用の小規模データと施設・出典manifest |
| `generated/report.json` | 47県の収集状態、件数、形式別出力と除外理由 |
| `generated/checksums.json` | 再生成した各ファイルのSHA-256 |

施設レコード数、辞書へ出せる確認済み施設数、重複除去した辞書行数、形式ごとの出力行数を分けて報告します。JSON・CSVの件数は要確認・除外も含む**管理レコード数**です。一覧から観測した行数は、神社庁の掲載総数や地域の全神社数とは限りません。

## データと確認

- 収録対象は神社庁が掲載した神社。表記は掲載名そのままとし、通称・略称・祭神名などは追加しません。
- 読みのNFKC・カタカナからひらがなへの変換だけを行います。異体字・旧字体を含む名称にはNFKCを適用しません。
- 読みの原文、名称原文、所在地、出典URL、短い確認根拠、取得・確認日時、ページ・行のhashを保存します。
- `verified`は資料の明示項目との一致を意味します。人が全施設の発音を独立に調べたという意味ではありません。詳細は[データ仕様](docs/DATA.md)を参照してください。
- 読みの不正文字、複数の住所を含む曖昧な行、出典の不備、未確認情報は出力しません。解釈や推定で修復しません。
- 神社庁掲載の読みが空の場合だけ、公式性と掲載名・所在地を照合した神社公式サイトの読みを、別フィールドで補完できます。
- 同名施設は別レコードのまま保持し、読み・表記・出力先品詞が同じ行だけを出力時に重複除去します。

テストの神社名・住所は架空データで、実在施設の出典としては使用していません。

## Mozc取り込み確認

1. `generated/samples/national/mozc.txt` を取り込み確認に使います。難読名を選ぶには `--sample-name` を指定します。
2. Mozcの辞書ツールで試験用の新しいユーザー辞書を作成し、テキストファイルからのインポートで選択します。UI文言は使用ビルドによって異なります。
3. 同フォルダーの `manifest.json` と読み・表記・異体字を照合し、実際に変換して確認します。同名施設が同じ候補になる場合も、manifestには各施設が残ります。
4. 問題がなければ必要な全国版または県別ファイルを取り込みます。

この手順の**実機検証は未実施**です。自動形式チェックや原文照合の成功を、IMEでの動作確認済みとは表示しません。ほかの形式の取り込み手順は、仕様とサンプルを確認してから追加します。

## 構成と拡張

取得クライアント `njd/http.py`、県別アダプター `njd/adapters/`、正規化 `njd/normalize.py`、検証 `njd/validation.py`、保存 `njd/storage.py`、出力 `njd/exporters.py`、集計 `njd/report.py`、原文照合 `njd/audit.py` を分離しています。

新しい県は公式性・一覧・項目・条件を調査したうえで専用アダプターを追加します。新しい形式は[出力仕様と品詞対応](docs/FORMATS.md)に根拠と対象版を記録し、出力プロファイル・直接出力処理・制限テストを追加します。ATOKなどを他形式の中間データとして使いません。

## ライセンス

ソースコードと本プロジェクトの文書は[MIT License](LICENSE)です。収集元の資料・データに関する権利・利用条件は別途管理し、MITライセンスで上書きしません。有料APIの契約・課金やアクセス制限の回避は行いません。
