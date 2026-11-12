# リリース

リリースは[Release Workflow](https://github.com/enjoydarts/national-jinja-dictionary/actions/workflows/release.yml)の手動実行で開始します。タグを事前に作る必要はありません。

## 公開する

1. 正本の更新と検証を済ませ、対象ブランチへコミットする。
2. Actionsで「Generate dictionaries and publish release」→「Run workflow」を開く。
3. ブランチと版番号を指定する。`0.1.0`・`v0.1.0`のどちらでもよく、タグ名は`v0.1.0`になる。
4. 実行が成功したことと、Releaseの添付ファイルを確認する。

Workflowは実行時のコミットを固定し、テスト・正本検証・全形式の辞書生成・CHANGELOG生成を行います。その後タグを作成し、ドラフトReleaseへ添付をアップロードします。SHA-256の照合がすべて成功すると公開します。

添付は`national-jinja-dictionary-vX.Y.Z.zip`だけです。ZIPには全国版・県別版・確認用サンプルのIME辞書を収録し、管理用JSON・CSVやレポートは含めません。出力行数・ZIPのSHA-256・対象コミットの正本と利用条件へのリンクはRelease本文に掲載します。

収集・正本更新とリリースは別工程です。リリース中に再クロールせず、そのコミットの正本からオフラインで生成します。同じ環境・正本・版番号から同じ内容を再生成できます。

## 公開せずに確認する

`dry_run`をオンにすると、タグやReleaseを作らず生成・検証します。辞書ZIPはWorkflowの`release-…` Artifactsから14日間取得できます。正本hash・検証レポート・出典一覧・CHANGELOGなどは別の`release-audit-…` Artifactsに保存します。通常実行でも同じ構成で保存します。

GitHub CLIからの実行例：

```sh
gh workflow run release.yml --ref main -f version=0.1.0 -F dry_run=true
gh workflow run release.yml --ref main -f version=0.1.0
```

## 失敗時の再実行

同じコミットから再開するには、元のWorkflow実行で「Re-run jobs」を使います。同一の添付は再利用し、不足分だけアップロードします。公開済みReleaseの全添付が一致する場合は変更しません。

タグ作成直後などにGitHub APIが一時的にタグ未検出を返す場合は、合計最大60秒待って再確認します。別コミットを指すタグは直ちに停止し、未検出が続く場合も公開しません。`release tag is not visible`で停止した場合は、実タグが対象コミットを指すことを確認してから同じ実行を再開してください。

別コミットを指す同名タグや、内容を照合できない添付がある場合は停止します。既存タグ・添付は上書きしません。変更したコミットで新しく公開する場合は、新しい版番号を指定してください。

## CHANGELOG

対象コミットから到達できる公開済みリリースタグのうち、最も近いものとの差分をコミット件名から生成します。初回は対象コミットまでの全履歴です。件名に明示されたPR番号をリンク化します。

CHANGELOGはRelease本文に掲載します。本文の上限を超える場合は一部を掲載し、GitHubの全変更履歴へのリンクを付けます。全文はWorkflowの検証用Artifactsに保存し、Releaseには添付しません。リポジトリへのCHANGELOG自動コミットは行いません。

## 辞書だけを生成する

```sh
python3 -m njd.release --version v0.1.0
```

このコマンドは`dist/release-assets/`へ配布用の辞書ZIPを生成し、`dist/`へ検証用の管理データ・ZIPも保存します。CHANGELOG・タグ・GitHub Releaseは作成しません。
