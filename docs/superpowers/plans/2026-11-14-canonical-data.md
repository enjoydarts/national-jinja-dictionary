# 共通正本への統合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 各登録の原観測・採用値・判断・調査を情報源別正本に集約し、全辞書をこの正本だけから生成する。

**Architecture:** schema_version=2の情報源別JSONに原観測と採用値を保持し、判断・根拠・調査を対象レコードへ格納する。共通管理情報はresearch_index.jsonへ移す。旧検証器へは新正本だけから検証用の原観測・判断を投影し、採用値との一致を確認する。

**Tech Stack:** Python 3.15.2、標準ライブラリ、unittest。

**Spec:** docs/superpowers/specs/2026-11-14-canonical-data-design.md

## Global Constraints

- 共通正本はdata/sources/。原文・ID/hash・旧字形・既存判断・履歴を保持する。
- 追加の読み調査・採用判断はしない。外部依存を追加しない。
- 辞書生成はオフライン。6形式の辞書本体は移行前とバイト単位で一致させる。
- 日本語で機能単位の署名付きコミットを作成する。共有先へのpushは今回の実装完了後の扱いを明示する。

## Review Focus

- 原文が変わった再取得で古い採用値を継続しない。
- 同名別施設・派生登録・別掲載対応を欠落や二重適用から守る。
- 正本と旧入力が同時に存在した場合に二重の編集元を認めない。
- 書込・移行失敗時は元の正本を復元し、不完全な世代から生成させない。
- 原文・採用値・根拠の食い違いや未参照の編集判断を検証で拒否する。

### Task 1: 正本形式・投影・移行

**Files:** Create njd/canonical.py, tests/test_canonical.py; Modify njd/nationwide.py（読込境界）

**Interfaces:** migrate(data_dir, destination), load_effective(data_dir), raw_collection(document), read_judgments(data_dir, kind), load_management(data_dir)。移行の入力は旧形式に明示的に限定する。

- [ ] 原文・補正・旧判断・保留調査の保持、派生・別掲載、採用値改変拒否、移行失敗時無変更のテストを書く。
- [ ] `python3 -m unittest discover -s tests -p test_canonical.py` で未実装による失敗を確認する。
- [ ] schema v2、レコード内判断、共通研究索引、損失検査付きオフライン移行、排他と復元を実装する。
- [ ] 上記テストを成功させ、既存の検証器で採用値を照合する。
- [ ] 機能単位で署名付きコミットする。

### Task 2: 生成・検証・リリースの統一

**Files:** Modify njd/__main__.py, njd/release.py, njd/overlays.py, njd/source_aliases.py, njd/publishing.py; Test tests/test_canonical.py, tests/test_release.py, tests/test_cli.py

**Interfaces:** load_effective(data_dir)の返す既存共通データ構造を使う。旧形式の処理は明示した移行・歴史的入力用の関数に分離し、v2へ二重適用しない。

- [ ] 新正本だけでCLIのvalidate/buildとreleaseが成功するテスト、旧ファイル併存拒否のテストを書く。
- [ ] 対象テストで失敗を確認する。
- [ ] 共通ローダーへ生成経路を切替え、リリースの入力hash・出典・配布用レポートを更新する。
- [ ] 対象テストと既存CLI・リリーステストを成功させる。
- [ ] 機能単位で署名付きコミットする。

### Task 3: 収集・補正の更新先統一

**Files:** Modify njd/nationwide.py, njd/proposals.py, njd/agency_details.py; Test tests/test_canonical.py, tests/test_proposals.py, tests/test_nationwide.py

**Interfaces:** save_collection、run_collections、import_proposalsの公開引数は維持する。v2の更新は排他下で原観測と旧判断を照合し、採用値を更新する。

- [ ] 補正適用が旧ファイルを作らない、既存除外保持、再取得の原文変更・部分欠落・失敗復元のテストを書く。
- [ ] テストの失敗を確認する。
- [ ] 読み補完、収集、再取得、公式詳細候補の参照を新正本に対応させる。
- [ ] 対象テストと全テストを成功させる。
- [ ] 機能単位で署名付きコミットする。

### Task 4: 実データ移行・文書・総合検証

**Files:** Modify data/sources/*.json, data/README.md, docs/DATA.md, docs/DEVELOPMENT.md, docs/RELEASING.md, docs/SOURCES.md, docs/REVIEW.md, AGENTS.md, README.md; Delete旧入力9ファイル

**Interfaces:** 移行前スナップショットはリポジトリ外に保管する。移行後のdata/sources/だけを現役入力とする。

- [ ] 実データを別ディレクトリへ移行し、全原観測と編集判断・研究記録が移行元へ損失なく投影できることを検査する。
- [ ] 6形式の本体hashと施設件数、解決660・保留10,208を移行前と比較する。
- [ ] 移行済み正本へ切替え、旧入力を削除し、文書・更新手順と履歴上の旧パス表記を区別する。
- [ ] `python3 -m unittest discover -s tests` と `python3 -m njd validate` を成功させ、6形式の一致、オフラインリリース、git diff --checkを確認する。
- [ ] fresh reviewerに全体を確認してもらい、重大な指摘を再現テスト付きで修正する。
- [ ] 正本移行と文書を日本語の署名付きコミットにまとめ、完了状況を報告する。
