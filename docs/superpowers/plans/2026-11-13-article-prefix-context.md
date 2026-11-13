# 記事省略接頭辞 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans inline。一度の最終独立レビュー。

**Goal:** 同記事の省略宣言と隣接社名/住所を検証し、対馬3読みを実資料で補完する。
**Architecture:** 専用 `article_context_address(ref, facility) -> str | None` と既存補正/出力再検証へ接続。原文は変更しない。
**Tech Stack:** Python 3.15標準ライブラリ。
**Spec:** `docs/superpowers/specs/2026-11-13-article-prefix-context-design.md`

## Global Constraints

推定読み・別施設流用・制限回避なし。既存除外/同一性保留を解除しない。全原正本・旧判断・全履歴・10868ID/hash保持。実IME取り込み未実施。日本語の機能単位コミット、並行作業を上書きしない。

## Review Focus

- 省略宣言の位置/県市/同一URL/hash/日時が異なる場合に拒否。
- 目次・別記事カード・別施設段落・非隣接要素から組み立てない。
- 住所注記は印刷された1個の括弧ひらがなだけを区間拘束し、町字/枝番を削除しない。
- 混合参照で不正contextや用途制限を回避しない。
- 除外保持の反復性・保存根拠破損時の出力抑止。

### Task 1: 検証機能

**Files:** 新 `njd/article_context.py`, 新 `tests/test_article_context.py`, `njd/corrections.py`, `docs/DATA.md`
**Interfaces:** `article_context_address(ref, facility) -> str | None`。
- [ ] 人工資料の受理/非破壊/反復、明記省略と注記区間、間違い/異型/欠損/混合参照/既存保留/除外/出力破損のテストを先に作る。
- [ ] `python3 -m unittest discover -s tests -p test_article_context.py -v` の未実装失敗を観測。
- [ ] 検証関数と全context早期拒否/読み限定/除外保持を実装し、対象及び全テスト成功を確認してコミット。

### Task 2: 39記事の採否と履歴統合

**Files:** `data/corrections.json`, `data/reading_research.json`, `data/manifest.json`, `data/source_catalog.json`, `docs/REVIEW.md`, `docs/SOURCES.md`
**Interfaces:** 1件は既存普通参照、2件はTask1根拠型。
- [ ] 39実記事/保留70登録の到達範囲を記録、津和原/富浦天神多久頭魂/屋利止加3件採用、他67保留。目次を見出しや住所を実リンク先と混同しない。
- [ ] 基準ID/hash/旧補正/全履歴/原正本不変、適格+3/-0、対象外全実効データ不変、6形式、全テスト/正本検証を実行。
- [ ] 一度の独立最終レビューを受けて必要修正を検証、最新main履歴を保存して統合、作業領域を削除する。

## 実行台帳

私有資料 `/tmp/njd-tsushima-blog-followup/`。39記事取得/エラー0、転載禁止マーカー0。同名出現25記事、TOCを含む機械的なfullname-kana候補70組は施設同定・採用件数ではない。
