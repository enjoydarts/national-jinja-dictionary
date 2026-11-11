# リリース

リリースは[Release Workflow](https://github.com/enjoydarts/national-jinja-dictionary/actions/workflows/release.yml)の手動実行で開始します。タグを事前に作る必要はありません。

## 公開する

1. 正本の更新と検証を済ませ、対象ブランチへコミットする。
2. Actionsで「Generate dictionaries and publish release」→「Run workflow」を開く。
3. ブランチと版番号を指定する。`0.1.0`・`v0.1.0`のどちらでもよく、タグ名は`v0.1.0`になる。
4. 実行が成功したことと、Releaseの添付ファイルを確認する。

Workflowは実行時のコミットを固定し、テスト・正本検証・全形式の辞書生成・CHANGELOG生成を行います。その後タグを作成し、ドラフトReleaseへ添付をアップロードします。SHA-256の照合がすべて成功すると公開します。

| 添付 | 内容 |
| --- | --- |
| `national-jinja-dictionary-vX.Y.Z.zip` | 全国版・県別版・サンプル・出典・検証レポート |
| `SHA256SUMS` | 添付ファイルのSHA-256 |
| `SOURCE.json` | 正本コミット・入力ファイルのhash・生成情報 |
| `CHANGELOG.md` | コミット履歴から生成した変更履歴 |

収集・正本更新とリリースは別工程です。リリース中に再クロールせず、そのコミットの正本からオフラインで生成します。同じ環境・正本・版番号から同じ内容を再生成できます。

## 公開せずに確認する

`dry_run`をオンにすると、タグやReleaseを作らず生成・検証します。成果物はWorkflowのArtifactsから14日間取得できます。通常実行でもArtifactsを保存します。

GitHub CLIからの実行例：

```sh
gh workflow run release.yml --ref main -f version=0.1.0 -F dry_run=true
gh workflow run release.yml --ref main -f version=0.1.0
```

## 失敗時の再実行

同じコミットから再開するには、元のWorkflow実行で「Re-run jobs」を使います。同一の添付は再利用し、不足分だけアップロードします。公開済みReleaseの全添付が一致する場合は変更しません。

別コミットを指す同名タグや、内容を照合できない添付がある場合は停止します。既存タグ・添付は上書きしません。変更したコミットで新しく公開する場合は、新しい版番号を指定してください。

## CHANGELOG

対象コミットから到達できる公開済みリリースタグのうち、最も近いものとの差分をコミット件名から生成します。初回は対象コミットまでの全履歴です。件名に明示されたPR番号をリンク化します。

全文をZIP内とRelease添付へ保存します。Release本文にも掲載し、長い場合は添付へのリンクに切り替えます。リポジトリへのCHANGELOG自動コミットは行いません。

## 辞書だけを生成する

```sh
python3 -m njd.release --version v0.1.0
```

このコマンドは`dist/`へ辞書ZIPを生成します。CHANGELOG・タグ・GitHub Releaseは作成しません。
