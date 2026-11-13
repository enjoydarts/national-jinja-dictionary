# 市町村名の市境界修正計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 町域先頭の市の取り込みを修正し、診断済み115施設の導出市町村名を原文・読みを保持して補正する。
**Architecture:** records.pyの市名正規表現を限定修正。資料・旧値は正本collectionへ保存し、調査管理のsource hashを同期する。
**Tech Stack:** Python 3.15.2以上、標準ライブラリ、unittest。
**Spec:** `docs/superpowers/specs/2026-11-13-city-boundary-design.md`

## Global Constraints

- 原住所・原名称・ID・原文hash・読み・既存判断を保持する。
- 新規の読み採用はせず、17保留登録を解決済みにしない。
- J-LISのrobots不明を回避しない。本文・画像・キャッシュをコミットしない。

## Review Focus

- 四日市市・廿日市市・野々市市と旧今市市・八日市市の原名を切り詰めない。
- 京都市左京区の町域にある市市を市名と解釈しない。
- 原住所の市市を削除・置換せず、導出municipalityだけを修正する。
- 診断済み115施設以外、特に明示的な市町村欄を無断で再計算しない。
- sourceファイルhash変更の同期漏れや既存出力の減少を検出する。

### Task 1: 抽出の修正

**Files:** `njd/records.py`, `tests/test_records.py`, `njd/nationwide.py`, `tests/test_nationwide.py`, `docs/DATA.md`。

- [x] 市の直後の町域・区以後の町域と5市名の人工地番テストを書く。
- [x] 追加テストの期待不合格を確認し、最小の正規表現変更を行う。
- [x] 再取得で履歴を重複なく保持し、古い補正値を新原文へ適用しないテストと保存処理を追加する。
- [x] 対象・全テストと正本検証を実施し、日本語でコミットする。

### Task 2: 導出値の補正

**Files:** 診断対象を含む `data/sources/*.json`, `data/reading_research.json`, `data/source_catalog.json`。

- [x] 原値・旧抽出・対象hashを再照合し、独立担当が補正案を審査する。
- [x] 承認した導出値のみ変更し、旧値・資料・判断を保存してhashを同期する。
- [x] ID/原値/読み/既存判断/適格集合/辞書行の不変と全検証を確認する。
- [x] 日本語でコミットし、独立最終審査後に作業ブランチへ取り込む。
