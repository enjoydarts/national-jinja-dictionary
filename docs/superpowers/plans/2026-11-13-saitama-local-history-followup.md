# 埼玉の郷土資料による全文読み補完 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 越谷の日枝神社の全文読みを同名/全地番の実PDFで補完し、他2登録の未確認範囲を保持する。

**Architecture:** 既存reading-only補正を利用するデータ変更。非公式NPO資料の明示全文かなと同頁住所を個別照合し、自治体本文に全文かながない場合は合成しない。

**Tech Stack:** Python3.15.2、既存JSONオーバーレイ。

**Spec:** docs/DATA.md

## Global Constraints
原名/原空かな/全所在地/ID/hash・全旧調査/補正/除外を保持。推定読み/別施設流用/アクセス制限回避なし。PDF/全記事/画像/個人名/キャッシュをコミットしない。最小事実と出典位置を記録し、一般再配布許諾や行政公認とは扱わない。日本語機能単位コミット。実IME未確認。

## Review Focus
- NPOの引用記事で原正式名・独立全文かな・全地番が同じ主対象を指すか。
- 表紙・16頁・実更新情報リンク・hashが同一PDFへ対応するか。
- 第六天神社では祭神ルビを社名に流用せず、春日神社では流鏑馬や春日様の読みを社名へ合成しないか。
- 全旧研究行/試行/補正/原正本/10868 IDsと他の実効登録・全施設が保持されるか。

### Task 1: 実資料照合と正本反映

**Files:** data/corrections.json, data/reading_research.json, data/manifest.json, data/source_catalog.json, docs/REVIEW.md, docs/SOURCES.md。

**Interfaces:** 既存correction_problems/apply_corrections/eligible。日枝神社8b1a75d6-2a82-5ca5-a99f-ef37d97fccbd、第六天神社0d43be06-a707-5774-aa6b-22c79afb3fbd、春日神社8d230762-1c07-54d1-ae08-64370bace74a。

- [x] 団体トップ/実更新情報リンク/第523回PDF表紙・16頁・末頁、自治体本文・マップ原画像を照合。Expected: 日枝は全文かなと全地番一致、他2件は読み未確認。
- [x] 日枝のreadingのみ補正し旧判断を追記保存。Expected: +1/-0、他実効登録/全施設不変、全旧履歴と10868 ID/hash保持。
- [x] 全テスト/validate/6形式、データコミット。Expected: errors0、各形式対象1行、実IME未実施。
- [x] 独立審査1回、C/Iは1修正パス、最新main保持で統合/検証、資料と台帳を保存して専用ツリー整理。

統合記録: 11da1b8で最新main aad2315の補完・全調査履歴を保持して反映。コミット時点377解消/10,491保留、埼玉16保留。審査C0/I0/M0、対象変更の実効+1/-0・他実効登録/全施設不変・10868 ID/hashと旧判断を保持。統合ツリーで684テスト成功、validate errors0/reviews133。原案内板真正性/行政公認/包括的再配布許諾や実IME取り込みは認定しない。資料/台帳を私有領域へ保存し専用ツリーのみ整理する。
