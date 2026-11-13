# 兵庫の市文化財による所在地補完 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans.

**Goal:** 鳥飼八幡宮の原所在地欠落を市の本殿資料で審査し、根拠が成立する1登録を採用する。
**Architecture:** 専用証拠validatorをlocation supplementへ追加し、原住所/全かなを保持する。
**Tech Stack:** Python3.15、標準ライブラリ、unittest。
**Spec:** docs/superpowers/specs/2026-11-13-hyogo-building-location.md

## Global Constraints
原正本/ID/hash/旧判断/全研究履歴を保持。原詳細と地図の住所は空欄を保存。市の本殿かなを切り出さない。博物館の転用禁止資料不採用。追加字を補作しない。実資料は別に審査し人工テストを根拠にしない。

### Task 1: 専用所在地補完型

**Files:** new njd/hyogo_building_location.py, tests/test_hyogo_building_location.py; modify njd/locations.py,njd/validation.py,docs/DATA.md.
**Interfaces:** building_location_problems(supplement,facility,source), building_entry_problems(supplement,facility,entry); new supplement_kind hyogo_cultural_building_location.

- [x] 原空欄/全かな/構造3年/同名同郵便番号/登録全地番と追加字を拘束した正常例、独立改変拒否、再適用/失敗時原空欄復元のテストを書く。
- [x] 新正常例がFAILすることを確認。Expected: 未実装の型で保留。
- [x] 専用validatorと適用/検証の分岐を実装する。Expected: 原文不変で正常例のみ適格1。
- [x] 全unittest/正本validate/採用前全適格ID比較。Expected: 全成功、正本出力不変。
- [x] 日本語機能コミット。

### Task 2: 実1登録の照合・採用

**Files:** data/locations.json,data/reading_research.json,data/manifest.json,data/source_catalog.json,docs/SOURCES.md.
**Interfaces:** Task1補完型で実案件6328164を検証。原詳細/hash/XML/市本殿欄/登記全月次と8日次を再点検する。

- [ ] 原実code/印字/hash/郵便番号、同じ本殿の1603/1724/1845年と構造を市資料と照合。全月次206383/日次19178を再照合。Expected: 同名同郵便番号と登録全地番の存続法人一意、関連イベント0。
- [ ] 個別所在地補完と原全文かなだけ採用し旧研究行を履歴へ保存。Expected: 最新main適格+1/-0、全10868 ID/全旧判断保持。
- [ ] 全unittest/validate/6形式対象行自動検査、diffcheck。Expected: 全成功、errors0。実IME取込は未確認。
- [ ] 日本語採用コミット。

## 最終統合

- [ ] Fresh whole-branch review、Critical/Importantは一度の修正。最新main保持で統合し検証、専用worktree片付け。
