# 番号付き冊子住所 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. 一度の最終独立レビューを行う。

**Goal:** 同PDF番号と明示接頭辞を検証し、対馬8読みを採用、4保留を記録する。
**Architecture:** 専用コンテキスト検証関数と既存補正/出力再検証へ接続。共通正本から6形式へ直接出力。
**Tech Stack:** Python 3.15標準ライブラリ、PDFKit（取得済み資料の個別画像点検のみ）。
**Spec:** `docs/superpowers/specs/2026-11-13-numbered-booklet-context-design.md`

## Global Constraints

推定読み・別施設流用・原住所改変・制限回避を行わない。全原正本・旧判断・10868ID/hashを保存。実IME取り込みは未実施と区別。日本語で機能単位のコミット。並行編集を上書きしない。

## Review Focus

- 不正コンテキスト+普通の有効参照で根拠不備を回避しない。
- 除外済み登録の繰返し適用で除外を失わない。
- 同名別地番・異体字・別町を認めない。
- ページ/番号/hash/日時/抜粋の欠損や異型を例外なく拒否する。
- 出力時の保存根拠破損でも止める。

### Task 1: 検証実装

**Files:** `njd/booklet_context.py`（新規）、`njd/corrections.py`、`tests/test_booklet_context.py`（新規）、`docs/DATA.md`
**Interfaces:** `booklet_context_address(ref, facility) -> str | None`。原住所を変更せず比較住所だけ返す。
- [ ] 人工施設の受理/非破壊/冪等性、欠損/不正/同名別住所/括弧注記/混合参照/除外保持/出力時破損のテストを先に作る。
- [ ] `python3 -m unittest discover -s tests -p test_booklet_context.py -v` の未実装による失敗を記録。
- [ ] 専用検証と補正全体の読み限定/不正早期拒否、除外保持を実装。
- [ ] 対象テストと全テストを実行、緑を確認、機能コミット。

### Task 2: 実資料の採否と統合

**Files:** `data/corrections.json`、`data/reading_research.json`、`data/manifest.json`、`data/source_catalog.json`
**Interfaces:** Task1の根拠型。原画像/全文かな/番号/表行/明示接頭辞を各採用へ保存。
- [ ] 12原画像照合の採用8/保留4を記録、原文hash/旧補正/調査履歴を保存。
- [ ] 全10868ID/hash保存、他施設/登録不変、適格出力+8/-0、各6形式と `python3 -m njd validate` を確認。
- [ ] 日本語データコミット、全差分の最終独立レビューを1回実施。不備があれば再現テストから修正。
- [ ] 最新mainと履歴を保持して統合、必要検証を完了、作業領域を削除。

## 実行台帳

原画像点検: /tmp/njd-tsushima-guide-followup/private-page{2,3,4,6,7,9,11,15,16}.png。画像/全本文はコミットしない。
