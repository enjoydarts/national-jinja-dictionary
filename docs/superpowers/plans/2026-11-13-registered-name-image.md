# 登記名称画像の全文読み補正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 同じ法人行の公式名称画像と実全所在地で代理文字を個別に対応させ、明示全文カナを採用する。
**Architecture:** 新しい純粋validatorをcorrectionsへ専用分岐として接続する。通常の名前比較を緩めず、専用型だけが画像転写名と厳密な実ID/全住所を検証する。
**Tech Stack:** Python3.15/標準ライブラリ/unittest。
**Spec:** docs/superpowers/specs/2026-11-13-registered-name-image.md

## Global Constraints

原名/原住所/原かな/CSV名/原文hash/ID不変。画像は発音の根拠にしない。通常型・既存採用の出力は不変。取得本文/画像/私的環境をコミットしない。日本語の機能単位コミット。

## Review Focus

- 転写の差は代理文字の1位置だけに限定し、他の字・社号・順序を変えない。
- 同名町域だけで同定せず、元indexの実href/IDと詳細全枝番へ拘束する。
- 法人番号/画像ID/hash/CSV行/住所画像・別行の不一致を拒否する。
- 画像又は部分かなから語尾を作らず、同法人行の全文kanaだけを用いる。
- 再適用/失効時/オフライン/既存除外/旧研究及び10868 IDの保持を検証する。

### Task 1: 個別画像と登録全文の補正検証

**Files:** Create njd/registered_name_image.py, tests/test_registered_name_image.py; Modify njd/corrections.py, docs/DATA.md.
**Interfaces:** Consumes source snapshot/native index-detail/image_reviews/pinned month and global8dailies; Produces image_correction_problems(correction,facility,entry,source=None)->list[str].

- [x] Step 1: 人工のCSV代理文字1字・個別画像全文・実リンク/全地番・全文かなでeligible1、全原欄不変、reapply成功のテストを書く。別字/枝番/法人/画像/CSV行/日次/原hash/除外を独立改変して拒否する。
- [x] Step 2: python3 -m unittest discover -s tests -p test_registered_name_image.py -v。Expected: 新型未対応のため正常例FAIL。
- [x] Step 3: 専用helperとcorrections分岐/reading_url設定を実装。通常の_reference_matchesは変更しない。
- [x] Step 4: 全unittest/njd validateと採用前の全適格ID/counts比較。Expected: 全成功/errors0、既存出力完全同一。
- [x] Step 5: 日本語コミット。

### Task 2: 実資料の再点検と1登録の反映

**Files:** Modify data/corrections.json, data/reading_research.json, data/manifest.json, data/source_catalog.json, docs/REVIEW.md, docs/SOURCES.md, original design state.
**Interfaces:** Consumes Task1 dedicated kind; Produces 1 correction and preserved old pending research.

- [x] Step 1: 公式PNGを目視し原hashを確認、原index/detail本文を実再解析、滋賀全44347行/8日次19178行を再走査。Expected: 全名/実code/全地番一致、対象イベント0、存続全地番一意。
- [x] Step 2: 補正1を追加し旧研究を採用履歴へ保存、全hash/集計更新。Expected: 適格+1/-0、全国312解消/10556保留、10868 ID・原正本不変。
- [x] Step 3: 全unittest/njd validate/diffcheck。Expected: 全成功/errors0。
- [x] Step 4: 日本語採用コミット。

## 最終統合

- [x] Fresh whole-branch reviewで根拠と拒否条件を確認し指摘を処理。最新mainを保持して統合しmain再検証、専用worktreeを片付ける。
