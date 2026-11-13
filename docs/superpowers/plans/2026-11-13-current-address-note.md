# 現在住所注記審査 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 原住所と全文かなを保持し、実資料で確認した現在住所の注記を個別審査する。
**Architecture:** 専用の純粋validatorを新設し、reviewsの既存例外経路で呼ぶ。既存改行規則とは独立。正本は最後に別コミットで適用。
**Tech Stack:** Python標準ライブラリ・unittest。
**Spec:** docs/superpowers/specs/2026-11-13-current-address-note.md

## Global Constraints

- 原住所・注記・名称・読み・ID・source_hashを変更しない。
- 推定読み・別住所の合成・制限回避をしない。
- 依存追加なし。コードと採用データは日本語の別コミット。

## Review Focus

- 別住所や変更前住所を注記として通さない。
- 紛らわしい地番・字名を同一視しない。
- 元掲載リンクとは異なる施設やhostの詳細を採用しない。
- 不正な型・重複rolesで例外や誤採用を起こさない。
- 他保留条件と再適用時の原文変更を見落とさない。

### Task 1: 専用検証と呼出し

**Files:** Create njd/current_address_note.py; modify njd/reviews.py; create tests/test_current_address_note_review.py; update docs/DATA.md.
**Interfaces:** current_address_note_problems(review,facility,entry)->list[str]、既存review_problems/apply_reviews。

- [x] 人工資料のLF/CRLF注記付き住所が原文を変えずeligibleになる試験を作る。各Review Focusと参照・原文・出力の変異を拒否する試験を作る。
- [x] `python3 -m unittest discover -s tests -p test_current_address_note_review.py`で成功ケースがFAIL、他ケースは保留であることを確認。
- [x] 専用validatorとreviews分岐を実装し、上記試験PASS。原文・型・リンク・registryの全拘束を検査。
- [x] DATAに個別審査条件を記録。`python3 -m unittest discover -s tests`と`python3 -m njd validate`で失敗0。日本語コミット。

### Task 2: 実登録の採用

**Files:** data/reviews.json, data/reading_research.json, data/source_catalog.json, data/manifest.json; docs/REVIEW.md if count summary requires.
**Interfaces:** Task1のreview schemaを消費。raw sourceは不変。

- [x] 実資料のhash・日時・locatorから熱田1登録のreviewを組立て、review_problems=[]を確認。
- [x] 共通データへ適用して追加eligibleが対象1件のみ、削除0、全原字段・ID・hash不変を検証し集計を更新。過去調査をadopted historyに保持。
- [x] 全試験とvalidateとdiff check成功後、日本語コミット。
- [x] fresh reviewerで全差分の根拠と境界条件を確認し、指摘があればRED→GREENで修正してmainへ統合。
