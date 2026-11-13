# 同一正式名の全文読み2登録 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 資料に併記された2全文読みを原名と原登録を保持して出力する。
**Architecture:** 専用の純粋validatorと専用派生ID関数をreviewsへ接続する。元登録を除外し、同一施設へ読みごとの2登録を再構築する。
**Tech Stack:** Python3.15/標準ライブラリ/unittest。
**Spec:** docs/superpowers/specs/2026-11-13-same-name-full-reading-variants.md

## Global Constraints

原正本・名前・住所・原かな・hash不変。推定読み/別名分割へ流用しない。既存split ID不変。元目標ID集合10868は派生IDで増やさない。変更は日本語の機能単位コミット。

## Review Focus

- 同じ表記の異なる読みがID衝突せず、再適用で重複しない。
- 元の別の除外・同一性保留・異体字問題を解除しない。
- token/区間/括弧・実コード・全地番・市名条例を一つずつ独立して改変しても拒否する。
- 派生の親ID/読み/証拠改変をoffline validationでも拒否する。
- 解消元登録1と出力2を混同せず、既存全研究・別県採用・10868 IDを保持する。

### Task 1: 専用validationと2派生の適用

**Files:** Create njd/reading_variants.py, tests/test_reading_variants.py; Modify njd/reviews.py, njd/validation.py, njd/report.py, docs/DATA.md.
**Interfaces:** Consumes immutable Hyogo profile/map/city comparison; Produces variant_problems(review,facility,entry,source=None)->list[str], variant_id(parent,surface,reading)->str.

- [x] Step 1: 人工資料の2全文読みでeligible2・原登録保持・安定した異なるchild ID・再適用同一のテストを書く。区間/出典/住所/除外/親ID等を独立改変する拒否テストを付ける。
- [x] Step 2: python3 -m unittest discover -s tests -p test_reading_variants.py -v。Expected: 新型未対応で正常例FAIL。
- [x] Step 3: 専用checkerと派生再構築を実装。helperは原登録と派生の証拠を同じ規則で検証し、既存型へフォールバックしない。
- [x] Step 4: 全unittest/njd validate、採用前の全既存適格ID/countsをmainと比較。Expected: 全成功/errors0、既存出力完全同一。
- [x] Step 5: 日本語機能コミット。

### Task 2: 実資料の再点検と味淵神社1元登録の反映

**Files:** Modify data/reviews.json, data/reading_research.json, data/manifest.json, data/source_catalog.json, docs/REVIEW.md, docs/SOURCES.md, original design state.
**Interfaces:** Consumes Task1 dedicated kind; Produces 1 review, 2 derived entries, retained original research.

- [x] Step 1: 保存済み実詳細HTML・単一XML・条例本文を再解析しコード/全文かな2区間/全地番/hashを確認。Expected: profile1・kana欄1・明示全文2、条例は接頭市名のみ対応。
- [x] Step 2: reviews1を追加し旧研究を履歴へ保存、元登録を除外・派生出力2。Expected: 適格+2/-0、元登録解消+1、全国311解消/10557保留、全10868 ID・全原正本不変。
- [x] Step 3: 全unittest/njd validate/diff check。Expected: 全成功/errors0。
- [x] Step 4: 日本語採用コミット。

## 最終統合

- [x] Fresh whole-branch reviewで根拠/ID/拒否条件を確認し指摘を処理。最新main保持で統合しmain再検証、専用worktreeを片付ける。
