# 同一正式名の明示全文読み2件を別登録にする

継続指示に基づき、既存のexplicit-reading-variants-and-name-image-designのうち同一名の全文読みだけを実装する。名称画像は独立した後続範囲とする。原文へ派生登録を直書きする案ではなく、reviews overlayの専用型を使う。既存の複数正式名splitへ流用しない。

新型same_name_parenthesized_full_readingsは兵庫の単一正式名見出し・唯一のかな欄の2全文読みを対象とする。Unicode code point区間の2つのraw tokenと間の全角丸括弧だけで元かな全体を尽くす。各tokenに明示された完成した社号を確認し、読みは各tokenの正規化そのもの。語尾・綴り・地名・異体字を補作しない。表記は元正式名1つのままとする。

原施設/原登録/原名/原全文かな/原全住所/実7桁code/印字code/URL/page hash/原文hash/locatorを束縛する。単一原XMLの同名同code同地番を照合し、市名差は既存の篠山市→丹波篠山市条例比較と完全一致の場合に限る。記録された旧比較根拠を保存し、再点検した条例本文と日時/hashも残す。資料の公式性とかな欄の単一性は本文を実点検する。

施設同一性、glyph、別住所、source_conflicts、他の保留・除外、権威未確認、複数正式名・途中かなは解除しない。原施設はverified/理由空、原登録はmissing or nonliteral full agency readingだけを許容する。再適用時のみ同型により除外した元登録を許容する。生source hashはname/whole kana/raw addressから再計算して照合する。

元登録は削除せず除外し、同じfacilityへ2派生登録を追加する。派生IDはuuid5(NAMESPACE_URL, parent entry ID + |same-name-full-reading-variant| + surface + | + reading)。parent_entry_idとderivation_kindを保持し、原かな/原hash/原IDは変えない。再適用は同じ2派生だけを再構築して重複を作らず、根拠が無効なら同型派生を出力しない。オフラインvalidationも各派生ID/親子関係/証拠を再検証する。既存split IDと既存型は変えない。

実採用は味淵神社6307065の1元登録だけ。原かなはミジブチジンジャ（アジブチジンジャ）、区間[0,8)と[9,17)、括弧は[8,9)と[17,18)。元10868 ID集合では解消1件と数え、派生出力2件を混同しない。既存の登記不一致・保留研究は採用履歴へ保存し、全国の残保留を未完了として記録する。
