# CSV Locality Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline, task by task.

**Goal:** 同一CSV行に明示された所在地と小字で原全住所を照合し、根拠がそろう全文読みのみ補完する。
**Architecture:** 専用の純粋関数で構造化証拠を束縛し、既存の補正・検証経路へ接続する。原文・一般住所比較は保持する。
**Tech Stack:** Python 3.15、標準ライブラリ、unittest。
**Spec:** `docs/superpowers/specs/2026-11-13-csv-locality-context-design.md`

## Global Constraints

実資料の明示全文かなのみ採用。原正本・全旧履歴・基準10,868 ID/hashを保持。推定小字・枝番・別名の切り出しをしない。日本語で機能単位コミット。

## Review Focus

- 別行の小字/カナ混入: URL/hash/行番号/No/原列値の不一致は保留。
- 枝番/字形/数字差: 同一性を緩めない。
- 不正コンテキスト: 完全住所があっても通常照合へ後退しない。
- 永続除外: 正常/破損補正の反復適用でも状態と理由を保持。
- 検証時の証拠改変: 既適用レコードでも出力が止まる。

### Task 1: 同一CSV行の比較用住所と補正経路

Create `njd/csv_context.py`, `tests/test_csv_context.py`; modify `njd/corrections.py`.
Consumes: `ref`, `facility` の辞書。Produces: `csv_context_address(ref, facility) -> str | None`。原値は変更しない。
- [x] テストで明示小字の採用、旧値不変、破損行の拒否、別地番/別小字の拒否、除外と他保留の維持を記述する。
- [x] `python3 -m unittest discover -s tests -p test_csv_context.py -v` が機能欠落によるFAILになることを確認する。
- [x] 純粋関数と補正経路の最小接続を実装する。
- [x] 対象テストと `python3 -m unittest discover -s tests` を成功させ、日本語でコミットする。

### Task 2: 実CSVの候補再照合と根拠保存

Modify `data/corrections.json`, `data/reading_research.json`, `data/manifest.json`, `data/source_catalog.json`, `docs/DATA.md`, `docs/SOURCES.md`, `docs/REVIEW.md`.
- [ ] 取得済み20候補を原全住所と同一CSV行の原列値で再点検し、対応行のみ採用する。
- [ ] 全旧履歴/ID/hash/原正本、対象+N/-0、対象外実効不変、6形式、CLI validate、全テストを検証してコミットする。
- [ ] 全範囲を独立レビュアー1名で審査し、C/Iは1回修正する。再審査はしない。
- [ ] 最新mainの採用・履歴を保持して再検証し、クリーンな時点でff-only統合する。保留がある間は全件完了としない。
