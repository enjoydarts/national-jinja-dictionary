# 兵庫の原地図名登記による施設同定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 原詳細の名称と全文かなを保持し、同code/同全地番の原地図名と登記で施設対応を確認する。
**Architecture:** 既存hyogo_profile_reviewのname selectionにmap登記名基準を追加する。新map基準は登記カナ空欄・原詳細/原地図の全住所同一の場合だけとし、通常型/所在地型へ広げない。
**Tech Stack:** Python3.15/標準ライブラリ/unittest。
**Spec:** docs/superpowers/specs/2026-11-13-hyogo-map-name-basis.md

## Global Constraints

原欄/ID/hash/旧判断不変。推定読み・名称補作・施設統合なし。登記は施設同定だけ、全文かなは原詳細のみ。既存型出力を変えず日本語コミット。

## Review Focus

- 原地図名/登記名が完全一致せず第三名称の場合は解除しない。
- map名基準と所在地差の同時承認、非空登記カナの流用を拒否する。
- 全枝番・実code・原hash・公開JS・日次状態を独立に改変して拒否する。
- 旧default profile基準と全既存適格ID/countsを保持する。
- 14調査対象と実採用1を分け、10868 ID/全研究履歴を保持する。

### Task 1: 原地図の登記名基準

**Files:** Modify njd/hyogo_profile_review.py, tests/test_hyogo_profile_review.py, docs/DATA.md.
**Interfaces:** Existing hyogo_profile_problems(review,facility,entry); optional profile_selection_proof.registered_name_basis defaults to profile, new allowed map only for name selection and empty registered kana, with map_subject_name_observation bound to the same profile body.

- [x] Step 1: map名登録で原詳細1出力・全原観測保持・再適用のテスト、第三名/非空カナ/住所差/他条件/未知basis拒否テストを書く。
- [x] Step 2: python3 -m unittest discover -s tests -p test_hyogo_profile_review.py -v。Expected: 新map正常例FAIL。
- [x] Step 3: name選択に限り登録名を原map名へ束縛。既存default/所在地型は維持。
- [x] Step 4: 全unittest/njd validateと採用前の全既存適格ID/counts比較。Expected: 全成功/errors0/出力同一。
- [x] Step 5: 日本語機能コミット。

### Task 2: 14登録の限定調査記録と駒宇佐1登録の反映

**Files:** Modify data/reviews.json, data/reading_research.json, data/manifest.json, data/source_catalog.json, docs/REVIEW.md, docs/SOURCES.md.
**Interfaces:** Consumes Task1 map basis; produces review1 and bounded source study14 with history.

- [x] Step 1: 元14登録の全原観測と全月次/8日次を再点検し、対象6306046の実詳細/XML/JSと名/全文かな/全地番/hashを確認。Expected: 候補のscopeを分離、同原map名/全地番の存続法人一意、対象イベント0。
- [x] Step 2: 限定調査14の結果を保存し、駒宇佐1だけ採用。Expected: 適格+1/-0、全国313解消/10555保留、全原正本/10868 ID/旧判断不変。
- [x] Step 3: 全unittest/njd validate/diffcheck。Expected: 全成功/errors0。
- [x] Step 4: 日本語採用コミット。

## 最終統合

- [ ] Fresh whole-branch reviewで実資料と選択根拠を審査、指摘を処理。最新main保持で統合しmain検証、専用worktreeを片付ける。
