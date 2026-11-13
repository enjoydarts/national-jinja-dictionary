# 兵庫の派生市町村補完 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 原住所を保存し独立登記で確定できる市町村欄を補う。
**Architecture:** locations overlayへ専用型を追加し、専用モジュールで実プロフィール・XML・独立登記・自治体の根拠を検証する。読みは原神社庁の全文かなのみ。
**Tech Stack:** Python3.15/標準ライブラリ/unittest。
**Spec:** docs/superpowers/specs/2026-11-13-hyogo-derived-municipality.md

## Global Constraints

原住所・ID・原文hashは不変。町の自動挿入、字形の一般置換、推定読みは禁止。既存型と原正本は変えない。変更は日本語コミット、623既存テストに回帰させない。

## Review Focus

- 元住所に町が既にある場合・複合差は補完しない。
- 全地番の枝番・非数字字形・郵便番号差を拒否する。
- 原入力・原snapshotを保持し、再適用と失敗時の復元を確認する。
- 後続登記事件・他の保留条件・除外を解除しない。
- 既存研究・別県の採用・全10868 IDを保存する。

### Task 1: 専用市町村根拠と既存overlayの接続

**Files:** Create njd/hyogo_municipality.py, tests/test_hyogo_municipality.py; Modify njd/locations.py, njd/validation.py, docs/DATA.md.
**Interfaces:** Consumes locations snapshot and hyogo_registry_window; Produces municipality_problems(supplement,facility) -> list[str], selected changes only municipality.

- [x] Step 1: 町のみ欠ける人工原住所を独立登記/自治体本文で補完し、原住所・原かな・ID/hashを保持しeligible1になるテストを書く。改変した地番/郵便番号/名称/時刻/原hash/後続window、非数字glyph、他条件、既存型混同と再適用・失敗復元もテストする。
- [x] Step 2: python3 -m unittest discover -s tests -p test_hyogo_municipality.py -v。Expected: 正常例が未対応のためFAIL。
- [x] Step 3: 専用型をlocationsの共通保護条件へ接続し、原snapshotと全根拠を検証する。validationはchangesにないaddressを原住所と比較する。
- [x] Step 4: 全unittestとnjd validate。Expected: 全成功/errors0、採用前適格集合はmain同一。
- [x] Step 5: 機能単位の日本語コミット。

### Task 2: 実2件の再照合と反映

**Files:** Modify data/locations.json, data/reading_research.json, data/manifest.json, data/source_catalog.json, docs/REVIEW.md, docs/SOURCES.md.
**Interfaces:** Consumes Task1 checker; Produces evidence-bound supplements2 and retained prior research history.

- [x] Step 1: 保存済み実HTML・XMLと全月次/8日次の候補を再点検し、原名/全文かな/全住所/郵便番号/実codeを照合する。Expected: 独立登記一意2、後続イベント0。
- [x] Step 2: supplements2を追加し研究記録2を採用履歴へ保存、件数/hashを更新。Expected: 適格+2/-0、全国310解消/10558保留、10868 ID全集合と全原正本不変。
- [x] Step 3: 全unittest/njd validate/diff check。Expected: 全成功。
- [x] Step 4: 採用2件を日本語コミット。

## 最終統合

- [ ] Fresh whole-branch review後、指摘を修正又は根拠付き判断。最新mainを保持して統合しmain再検証、専用worktree片付け。
