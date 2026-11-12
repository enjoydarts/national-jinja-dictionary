# 佐賀県の旧新住所根拠の実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 実資料と対象登録に束縛した旧新住所の比較を可能にし、海童神社の候補を独立審査する。
**Architecture:** 新規 `njd/municipalities.py` が比較用住所を返し、`njd/corrections.py` の既存全住所比較に渡す。取得原文は変更しない。
**Tech Stack:** Python 3.15.2以上、標準ライブラリ、unittest。
**Spec:** `docs/superpowers/specs/2026-11-13-saga-municipal-address-design.md`

## Global Constraints

- 推定読み・別施設からの読み流用・アクセス制限回避で保留を解除しない。
- 取得本文・画像・キャッシュ・個人情報をコミットしない。
- 原住所・ID・原文hashを保持する。資料の1・2ページにある佐賀市の7旧自治体だけを対象にする。

## Review Focus

- 枝番・字名の異なる候補が受理されないこと。
- 別登録・別施設・変更後の原文への証拠流用が受理されないこと。
- 偽URL・異なる資料hash・ページ・施行日の証拠が受理されないこと。
- 無地番・別県・対象外自治体の対応が受理されないこと。
- 証拠を省略した既存の住所相違が引き続き保留になること。

### Task 1: 資料に束縛した照合とテスト

**Files:** 新規 `njd/municipalities.py`、`tests/test_municipal_address_proof.py`。変更 `njd/corrections.py`、`docs/DATA.md`。
**Interfaces:** `municipal_comparison_address(ref, facility, entry) -> str | None`。補正参照の `address_identity_proof` を検査し、比較専用の住所を返す。`_reference_matches` の既存住所正規化後の完全一致だけを許す。

- [x] 人工名の読み補正が根拠ありでのみ適用され、原住所が保持されるテストを書く。
- [x] `python3 -m unittest discover -s tests -p test_municipal_address_proof.py -v` で追加前の不合格を確認する。
- [x] 上記Review Focusの拒否例をテストし、照合ヘルパーと既存比較の呼び出しを実装する。
- [x] 同じ対象テストと全テスト、`python3 -m njd validate` を実行し、コードを日本語でコミットする。

### Task 2: 実資料の採否

**Files:** `data/corrections.json`、`data/reading_research.json`、`data/source_catalog.json`、必要に応じて `data/manifest.json`。
**Interfaces:** Task 1の補正形式、既存の補正適用・件数再集計。

- [x] 海童神社の原掲載・県PDF・月次全件と取得済み日次を照合して候補を作り、独立レビューへ渡す。
- [x] 採否に応じた正本・調査記録・出典・集計を更新する。採用した場合は実際の出力対象差分も検証する。
- [x] 検証コマンドと結果を確認し、日本語の機能単位コミットを作る。
