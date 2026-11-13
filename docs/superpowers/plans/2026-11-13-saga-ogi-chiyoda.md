# 小城町・千代田町の照合拡張計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 実資料に束縛する2接頭辞を追加し、高志神社・牛尾神社の読み候補を独立審査して採否を正本へ記録する。
**Architecture:** 既存municipal_comparison_addressの規則追加。参照と全住所の検証は既存経路を使う。
**Tech Stack:** Python 3.15.2以上、標準ライブラリ、unittest。
**Spec:** `docs/superpowers/specs/2026-11-13-saga-ogi-chiyoda-design.md`

## Global Constraints

- 原住所・原字形・施設ID・原文hashを保持し、読みだけを補完する。
- 推定読み・別施設からの読み流用・アクセス制限回避は行わない。
- 本文・画像・キャッシュはコミットしない。

## Review Focus

- 新規2接頭辞での証拠欠落・ページ・日付・表示例の誤りを拒否する。
- 新規接頭辞でも異なる字名・枝番を許さない。
- 小城の漢字変更・有田の地番再編へ適用範囲を広げない。
- 既存7規則と既採用登録を維持する。
- 機械検証と実施設の同定を区別し、同名競合と画像を審査する。

### Task 1: 規則とテスト

**Files:** `njd/municipalities.py`, `tests/test_municipal_address_proof.py`, `docs/DATA.md`。

- [x] 人工名で2規則の読み補完・原文保持・証拠改変と地番差の拒否をテストする。
- [x] 対象テストの不合格を見てから2規則を追加し、対象と全テスト・正本検証を通す。
- [x] 独立レビュー後、日本語でコミットする。

### Task 2: 個別候補

**Files:** `data/corrections.json`, `data/reading_research.json`, `data/source_catalog.json`, `data/manifest.json`。

- [ ] 実掲載・県PDF・同名全存続行・全文カナ・名称画像を独立審査する。
- [ ] 採否と旧履歴を保持して記録し、出力対象差分と集計・hashを検証する。
- [ ] 全テスト・正本検証を通し、日本語でコミットする。
