# 市の土地台帳に基づく所在地補完 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 原住所空欄を保持し、原由緒の地名・市の台帳・独立登記で貴船神社1登録の所在地を補完する。

**Architecture:** `njd/hyogo_asset_location.py`で市の公開リンク/同一行・原詳細地名・一意登記を検証する。既存の住所空欄登録ガードを共有し、apply_locations/validateの単一原登録条件にも接続する。

**Tech Stack:** Python 3.15.2、標準ライブラリ、既存JSONオーバーレイ。

**Spec:** `docs/superpowers/specs/2026-11-13-hyogo-asset-location-design.md`

## Global Constraints

原正本・原空欄・原かな・ID/hashと旧判断を保持。推定読み・別施設流用・アクセス制限回避なし。取得本文/画像/キャッシュ/個人情報をコミットしない。日本語の機能単位コミット。実IME取り込みは未実施と明示。

## Review Focus

- 参照・入れ子のNone/list/異型で例外終了せず保留（Task 1）。
- 隣の地番・枝番・字名の差、資産種別や公開リンクの取り違えを拒否（Task 1）。
- 原由緒と別地域の地名、郵便番号・同名競合・変更イベントを拒否（Task 1）。
- 適用後に登録が追加/変更/削除された場合も施設全体を止める（Task 1）。
- 実資料と人工テストを区別し、全旧履歴/基準10868 IDと最新mainを保持（Task 2）。

### Task 1: 台帳の所在地補完

**Files:** Create `njd/hyogo_asset_location.py`, `tests/test_hyogo_asset_location.py`; Modify `njd/locations.py`, `njd/validation.py`, `docs/DATA.md`。

**Interfaces:** `asset_location_problems(s,f,source=None)->list[str]`、`asset_entry_problems(s,f,e)->list[str]`（既存住所空欄の原登録ガードと同契約）。`hyogo_municipal_asset_location`だけを既存適用・検証に接続する。

- [x] 人工施設の原空欄/全文かな保存・正しい所在地採用・冪等性と、不正地番/参照/公開リンク/既存判断/適用後登録数のテストを書き、REDを確認。
- [x] 新検証関数と適用/検証接続を実装しGREEN、全テスト・validate・diff-check後に日本語コミット。

### Task 2: 実資料の採用と残課題の保持

**Files:** `data/locations.json`, `data/manifest.json`, `data/source_catalog.json`, `data/reading_research.json`, `docs/SOURCES.md`, `docs/REVIEW.md`。

**Interfaces:** Task 1の検証済み所在地補正を原施設/登録IDへ保存。私有資料 `/tmp/njd-hyogo-municipal-followup`。

- [x] 原詳細・原XML・市公開リンク/政策/実PDF p.3の同一行を照合し、月次206383/8日次19178を再走査。
- [x] 貴船神社の適格+1/-0、他の実効施設/登録の完全一致、全旧研究行/旧試行/基準10868 ID/hash保持を確認。二子/西濱の保留根拠と未取得範囲も保存。
- [x] 6形式各1行、全テスト・validateで確認しデータコミット。
- [ ] 全体の独立審査1回、C/I指摘は1修正パス、最新main保持で統合・検証、私有台帳を保存して専用ツリーを整理。
