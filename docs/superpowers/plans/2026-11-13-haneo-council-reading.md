# 羽尾神社の町議会資料による全文読み補完 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 羽尾神社の全文ルビと全地番を同頁実資料で照合し、原文を保持して補完する。

**Architecture:** 既存のreading-only補正を使用するデータ変更。東松山市3登録の審査・修正済みブランチe5c986cから分離し、新たなコードや補正方式は追加しない。

**Tech Stack:** Python3.15.2、既存JSONオーバーレイ。

**Spec:** docs/DATA.md

## Global Constraints
原名/住所/空かな/ID/hash・旧調査/判断を保持。推定読み・別施設流用・アクセス制限回避なし。本文/全号/画像/個人名をコミットしない。日本語機能単位コミット。一般著作権条件と再配布許諾を区別。実IME取り込みは未確認。

## Review Focus
- 表題の羽/尾/神/社に付いた全ルビと全地番が同じ主対象か。
- 神社庁の原正式名/全所在地/原hash・施設同一性が対応するか。
- 引用長文/個人名/画像を含まず最小事実欄と出典を保存するか。
- 他の実効登録/施設と原正本・全旧補正/研究履歴/10868 IDを保持するか。

### Task 1: 原画像確認とデータ反映

**Files:** data/corrections.json, data/reading_research.json, data/manifest.json, data/source_catalog.json, docs/SOURCES.md, docs/REVIEW.md。

**Interfaces:** 既存correction_problems/apply_corrections/eligible。対象c82e8762-8514-52c3-afba-a93e36909918。

- [x] 町議会第161号18頁（index17）の全文ルビ・全所在地、原施設を照合。Expected: 羽尾神社/はねおじんじゃ/滑川町羽尾4806が一致。
- [x] 全旧判断を保持してreadingのみ補正し、実効差分+1/-0、全履歴/ID/hash検証。Expected: 他実効登録と全施設が不変。
- [x] 全テスト/validate/6形式を確認してデータコミット。Expected: errors0、各形式1行、実IME未実施。
- [x] 一度の独立審査、指摘C/Iは1修正パス、最新mainと未反映3登録を保持して統合/検証、台帳と私有証拠を保存。

統合記録: c146fb7で最新main98cc026の調査追記を保持し、既審査の4登録をmainへ反映。累計347解消/10,521保留、埼玉17保留。統合コミットと同一内容の専用ツリーで684テスト成功、validate errors0/reviews133。審査e5c986c..1b4b8a3でC0/I0/M0。羽尾神社の同頁全文ルビ/全住所と全旧履歴を独立照合。実IME取り込み未実施。PDF真正性の自動認証・資料全体の再配布許諾の認定は対象外。神社の実資料の全名/全所在地は目視と独立審査で確認。私有資料・台帳を保存し、専用作業ツリーのみ整理する。mainの他作業による未コミット差分は触れない。
