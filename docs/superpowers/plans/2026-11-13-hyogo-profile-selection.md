# 兵庫の詳細名称選択 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 詳細名・全文かなと独立登記で名称選択を審査する。
**Architecture:** 専用の純粋validatorをreviewsへ追加し、元map観測と独立登記へ拘束する。採用は別コミット。
**Tech Stack:** Python標準ライブラリ・unittest。
**Spec:** docs/superpowers/specs/2026-11-13-hyogo-profile-selection.md

## Global Constraints

- 全正本bytesと原名/住所/かな/ID/hash、過去判断を保持。
- 推定読み・別称認定・字名/地番差の自動解決なし。
- Python対象版維持・標準ライブラリのみ。

## Review Focus

- 別code・別地番・複数XML観測や複数存続法人を誤承認しない。
- malformedな参照・出力・URL・日付は保留へ戻す。
- map名・別名へprofileかなを転用しない。
- 他の同一性問題・除外・原文変更を上書きしない。
- 再適用とoffline検証でも証拠を再照合する。

### Task 1: 専用validatorと呼出し

**Files:** Create njd/hyogo_profile_review.py, njd/hyogo_registry_window.py and tests/test_hyogo_profile_review.py; modify njd/reviews.py, docs/DATA.md.
**Interfaces:** hyogo_profile_problems(review,facility,entry)->list[str]; review_problems/apply_reviewsの既存API。

- [x] 人工資料で原値不変の採用・再適用・offline検証を試験する。Review Focus全項と各参照・出力の変異を拒否する試験を作る。
- [x] `python3 -m unittest discover -s tests -p test_hyogo_profile_review.py`で成功ケースがFAILすることを確認。
- [x] 専用proofを実装し、reviewsで有効な場合だけ名称差を審査済みとする。上記試験PASS。
- [x] DATAへ条件を記録。`python3 -m unittest discover -s tests`と`python3 -m njd validate`が失敗0、diff検査成功後に日本語コミット。

### Task 2: 実登録3件の採用

**Files:** data/reviews.json, data/reading_research.json, data/manifest.json, data/source_catalog.json, docs/REVIEW.md。
**Interfaces:** Task1のreview schemaを使い、実hash/locator/コード/登録行で拘束。

- [x] 調査済み実本文・月次/日次から3reviewを組立て、review_problems=[]を確認。駒宇佐八幡宮は不採用。
- [x] 全過去調査をadopted historyへ保持。適格+3/減0、全原字段・全正本hash・全10868 ID・集計を検証して更新。
- [x] 全試験・validate・diff検査成功後、日本語の別コミット。
- [x] fresh reviewerで根拠・コード・全採用差分をレビュー。重要指摘はRED→GREENで修正し、検証してmainへ統合。
