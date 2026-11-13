# 改行住所の個別審査計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 原住所を保持して茨城2登録のレイアウト保留を根拠付きで審査する。
**Architecture:** `address_layout.py` が審査証拠を検査し、既存`reviews.py`のsource_reviewへ限定統合する。
**Tech Stack:** Python 3.15.2以上、標準ライブラリ、unittest。
**Spec:** `docs/superpowers/specs/2026-11-13-ibaraki-address-linewrap-design.md`

## Global Constraints

- 原住所・原名称・原読み・ID・原文hashを変更しない。
- 読みは神社庁の独立全文かなに限り、空の登録フリガナから生成しない。
- 実際の複数住所や注記付き住所の保留を維持する。
- 本文全体・画像・キャッシュ・個人情報をコミットしない。

## Review Focus

- 別施設・別原文・別URL/hashへの証拠流用を拒否する。
- 空欄や2所在地・枝番差・字名差から地番を補わない。
- 審査の再適用と原文変更後の保留を確認する。
- 独立参照の登録名称・全住所・存続状態・一意性・画像有無を確認する。
- 既存のsource_review分割やユーザー判断を壊さない。

### Task 1: 検証とテスト

**Files:** 新規`njd/address_layout.py`, `tests/test_address_layout_review.py`。変更`njd/reviews.py`, `docs/DATA.md`。

- [x] 人工施設で原値保持の成功例・証拠改変・複数住所・原文変更の拒否をテストし、失敗を確認する。
- [x] 限定検証を実装し、対象/全テスト・正本検証を通す。
- [x] 独立レビューを受け、日本語でコミットする。

### Task 2: 実資料の採否

**Files:** `data/reviews.json`, `data/reading_research.json`, `data/manifest.json`, `data/source_catalog.json`。

- [x] 原4ページと月次/差分の全同名競合を独立点検する。
- [x] 採否と旧調査履歴を保存し、原値/全ID/hash保持と適格差分を検証する。
- [x] 全検証と最終独立審査後、日本語でコミットして作業ブランチへ取り込む。
