# 市名コンテキストを保持する全文読み補完 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 印刷町域/地番と資料の明示市名を別保存し、東松山市3登録の全文読みを実資料から採用する。

**Architecture:** 同一PDF内の明示市名と表行の関係を検証し、reading-only補正の住所比較へ限定接続する。既存補正・正本は保持する。

**Tech Stack:** Python3.15.2、標準ライブラリ、既存JSON補正。

**Spec:** docs/superpowers/specs/2026-11-13-document-municipality-context-design.md

## Global Constraints
原名・原かな・印刷住所・ID/hash・全既存判断を保持。推定読み/別施設流用/アクセス回避なし。本文/画像/個人情報をコミットしない。日本語機能単位コミット。実IME取り込みは未確認。

## Review Focus
- 異型コンテキストと数値のbool/範囲外で例外終了しない（Task1）。
- 同名別市、異なる字名・枝番、別表のカード・部分かなを承認しない（Task1）。
- URL/hashと実原画像の市名scope・全ルビ・地番の対応（Task2）。
- 適用後の破損と再適用、他保留条件/除外の維持（Task1）。
- 他の実効登録・原正本・全履歴/10868 ID保持（Task2）。

### Task 1: 同一資料コンテキストの検証

**Files:** Create njd/document_context.py, tests/test_document_context.py; Modify njd/corrections.py, docs/DATA.md。

**Interfaces:** document_context_address(ref,facility)->str|None、reading-onlyの_reference_matches接続。

- [x] 人工参照の実適用・全負例・再適用/破損・保留維持を書きREDを実行。Expected: 有効コンテキストで出力できず失敗、import例外なし。
- [x] 最小実装と仕様追記、全テスト/validate/diff-check。Expected: 全成功・errors0。日本語コミット。

### Task 2: 実3登録の正本反映

**Files:** data/corrections.json, data/reading_research.json, data/manifest.json, data/source_catalog.json, docs/REVIEW.md, docs/SOURCES.md。

**Interfaces:** Task1へ同一資料の市名コンテキスト・印刷住所の別欄を渡す。

- [x] PDFindex1/2/3/4の原画像・hash・3原施設全住所を照合。Expected: 同一市/全地番/正式名全文かな、他保留なし。
- [x] 旧判断を保存し補正/調査履歴へ反映、全10868ID/hash・他実効データ一致。Expected: +3/-0、旧履歴保持。
- [x] 全テスト/正本検証/6形式、データコミット。Expected: errors0、各形式対象3行、実IME未確認。
- [x] 一度の全体独立審査、C/Iは1修正パス、最新main保持で統合/検証、台帳を保存して専用ツリー整理。

統合記録: c146fb7で最新main98cc026の調査追記を保持し、既審査の4登録をmainへ反映。累計347解消/10,521保留、埼玉17保留。統合コミットと同一内容の専用ツリーで684テスト成功、validate errors0/reviews133。全体審査C0/I1/M0、除外反復適用のI1はac6d807で回帰修正。東松山市3登録の実原文・全履歴を保持。実IME取り込み未実施。PDF真正性の自動認証・資料全体の再配布許諾の認定は対象外。神社の実資料の全名/全所在地は目視と独立審査で確認。私有資料・台帳を保存し、専用作業ツリーのみ整理する。mainの他作業による未コミット差分は触れない。
