# 旧市名地図の所在地選択 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 原住所を保持して同コード地図・条例・登記で波々伯部神社の所在地相違を解決する。

**Architecture:** `njd/hyogo_map_location.py`に根拠検証と単一原登録のガードをまとめ、既存のlocation supplement適用とvalidationに接続する。住所の削除正規化は行わず、検証済み独立登記列だけを実効住所に使う。

**Tech Stack:** Python 3.15.2、標準ライブラリ、既存のJSON正本/オーバーレイ。

**Spec:** `docs/superpowers/specs/2026-11-13-hyogo-map-city-location-design.md`

## Global Constraints

推定読み・別施設からの流用・取得制限回避なし。原正本・旧判断・ID/hashを保持。リリースはオフライン生成。機能単位の日本語コミット。実IME取り込みは未実施と明示。

## Review Focus

- 不正なNone/list/文字列参照で例外終了せず保留する（Task 1）。
- 5と50、5-1等の枝番相違を一致扱いしない（Task 1）。
- 地図/条例/登記の別ID・別code・同名競合を解除しない（Task 1）。
- 適用済み証拠破損をvalidateで検出し、再適用で原住所に戻す（Task 1）。
- 実資料と人工テストを区別し、旧地域調査と全10,868IDを保持（Task 2）。

### Task 1: 根拠付き所在地オーバーレイ

**Files:** Create `njd/hyogo_map_location.py`, `tests/test_hyogo_map_location.py`; Modify `njd/locations.py`, `njd/validation.py`, `docs/DATA.md`.

**Interfaces:** `map_location_problems(supplement,facility,source=None)->list[str]`、`map_entry_problems(supplement,facility,entry)->list[str]`。`hyogo_documented_map_location`だけを既存apply_locations/validateへ接続する。

- [x] 人工施設で住所相違→同コード旧地図/条例/一意登記に基づく新住所/原全文かな1登録の適格化と原欄保存・冪等性のテストを書き、失敗を確認。
- [x] 枝番・郵便番号・かな・code・日時・hash・競合・除外/別理由、参照型不正、破損再適用の出力停止テストを書く。
- [x] 新検証関数と既存2接続箇所を実装し、限定テストを成功させる。
- [x] 全テスト/正本validate/diff-checkを実行し、日本語で機能コミット。

### Task 2: 実資料の個別採用と追跡

**Files:** `data/locations.json`, `data/manifest.json`, `data/source_catalog.json`, `data/reading_research.json`, `docs/SOURCES.md`, `docs/REVIEW.md`。

**Interfaces:** Task 1の検証済みlocation supplementを原施設IDへ束縛して保存する。私有証拠は`/tmp/njd-hyogo-map-city-location`へ保存。

- [x] 原詳細/原XML/公開JS/実条例をhashと明示値で照合し、月次206383行/8日次19178行をオフライン再走査する。
- [x] 正本と補正の旧値・研究履歴を保持して候補を適用。適格+1/-0、他施設/登録は完全一致、全10,868 ID/hashをassert。
- [x] 6形式各1行と全テスト/validateを確認し、日本語でデータコミット。
- [ ] 全体の独立審査1回、重大/重要指摘があれば1修正パス。最新mainの別調査を保持して統合、mainで検証、専用作業ツリーを整理。
