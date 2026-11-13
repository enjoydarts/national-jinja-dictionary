# 兵庫の原所在地選択 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 原所在地を保持し、実コード/独立登記で3登録の同定を審査する。
**Architecture:** 既存hyogo_profile_problemsに別proof kindと2つの登録住所basisを追加。名称選択の条件は維持し、実採用は別コミット。
**Tech Stack:** Python標準ライブラリ・unittest。
**Spec:** docs/superpowers/specs/2026-11-13-hyogo-location-selection.md

## Global Constraints

- 原正本bytes・原名/住所/かな/ID/hash・旧観測・過去判断を保持。
- 推定読み・字名の一般削除・地番訂正・町の挿入なし。
- 依存追加なし・Python対象版は既存通り。

## Review Focus

- 末尾地番の一部を字名の前へ切り出さない。
- 同時に名称と住所が異なるものや別codeを承認しない。
- 字名・非数字字形・全枝番を近似一致させない。
- 原観測・日次窓の欠落・破損をoffline時にも拒否する。
- 別の保留理由・除外・再取得原文変更を上書きしない。

### Task 1: 所在地選択proof

**Files:** Modify njd/hyogo_profile_review.py, njd/reviews.py, tests/test_hyogo_profile_review.py, docs/DATA.md。
**Interfaces:** hyogo_profile_problemsの既存API・新review_kind/basisをレビューへ接続。

- [ ] 人工fixtureでprofile一致/linked_map_additional_azaの成功・原値保持・再適用・offline検証を試験し、Review Focus全項と誤basis・型破損の否定試験を追加。
- [ ] `python3 -m unittest discover -s tests -p test_hyogo_profile_review.py`で新成功ケースのFAILを確認。
- [ ] 新kindの検証とreviews接続を実装して上記PASS。既存名称選択の制約は維持。
- [ ] DATAに条件を記録。全unittest・njd validate・diff検査が失敗0で日本語コミット。

### Task 2: 実3登録採用

**Files:** data/reviews.json, data/reading_research.json, data/manifest.json, data/source_catalog.json, docs/REVIEW.md。
**Interfaces:** Task1の新schemaに、実profile/XML/JS/CSV/日次のhash・日時・全原住所を拘束。

- [ ] 実資料の3reviewを組み、review_problems=[]を確認。
- [ ] 適格+3/-0、全原字段・全正本hash・10868 ID・全過去履歴保持を検証し集計と範囲を同期。
- [ ] 全試験・validate・diff検査成功後、日本語の別コミット。
- [ ] fresh reviewerで全差分と実根拠を審査。重要指摘はRED→GREENで修正・検証しmainへ統合。
