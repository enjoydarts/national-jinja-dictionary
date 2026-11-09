# 登録判断と未確認範囲

個別に提示したR001–R009は回答済みです。採用値と根拠は正本の [`reviews.json`](../data/reviews.json) に保存し、取得原文は変更していません。選択肢の記号ではなく、最終的に確認した登録内容を適用します。

| 番号 | 採用内容 |
| --- | --- |
| R001 | 所在地の又／ヌの差を記録したうえで同一施設とするユーザー判断。名称のみ磤玖娜社へ補正し、神社庁の「おくだしゃ」を採用 |
| R002 | 鳴海杻神社の神社庁掲載読み「なるみてがしじんしゃ」を維持 |
| R003 | 越中白山総社は神社庁の複数掲載のうち「えっちゅうはくさんそうしゃ」を採用。相違する原文は保持 |
| R004 | 埼玉・静岡の3掲載に併記された正式名を8登録に分離。掲載施設IDは3件のまま保持 |
| R005 | 清常神社・小松神社・保木本神社を各全文読みで登録。合併による法人閉鎖の注記は保持 |
| R006 | 政府原文「コンピラジンジヤ」を保持し、ユーザー確認による小書き補正「こんぴらじんじゃ」を採用 |
| R007 | 福岡／福岡原の所在地差を記録した同一施設のユーザー判断により、一ノ貝神社「いちのかいじんじゃ」を採用 |
| R008 | 賀茂神社・天満宮を一語のまま「かもじんじゃてんまんぐう」で登録。分割しない |
| R009 | 伊弉原神社「いざはらじんじゃ」、上山神社「うえやまじんじゃ」をユーザー確認の全文読みとして登録。ウェブ資料での全文確認とは区別 |

R004の正式名は、物部天神社・国渭地祇神社・天満天神社、神部神社・浅間神社・大歳御祖神社、丸子神社・浅間神社です。埼玉の北野天神社は三社の総称であり、別称としては追加しません。元の複合登録は理由付きで除外し、個別登録から元登録へ参照を残します。

## 資料から追加で解決した登録

神社庁の実ページと照合し、別称などが混入していた宮城の11施設の正式読みを補正しました。[Wikipedia 天祖・諏訪神社](https://ja.wikipedia.org/wiki/天祖・諏訪神社)では同一所在地と全文読みを確認し、出典と版を保存しています。

正式名と各全文読みが神社庁に明示される併記8掲載は、16登録へ分離しました。対象は両谷神社・神明宮、磐上神社・雨宮神社、月夜見神社・八幡神社、諏訪神社・駒形神社、神明神社・諏訪神社、大渡神社・佐久地神社、日枝神社・水天宮、冨吉建速神社・八劔社です。ユーザーの個別回答とは区別した`source_review`として根拠を保存しています。

## 追加調査で見つかった読みの衝突

次の2登録は、名称・所在地が一致する実資料で全文読みが異なったため、補正を`needs_review`へ戻して辞書出力を保留しています。各原文・確認日時・版・所在地は`data/corrections.json`に保持しています。既存のR001–R009の回答は変更していません。

| 番号 | 施設・所在地 | 確認済みの資料と候補 | 現在の状態 |
| --- | --- | --- | --- |
| R010 | 菅田天神社／山梨県甲州市塩山上於曽1054 | [神社庁詳細](https://www.yamanashi-jinjacho.or.jp/intro/search/detail/2012)は全文読みなし。国税庁法人番号9090005003832と[甲州市公式観光情報](https://www.koshu-kankou.jp/map/m5097.html)は「かんだてんじんじゃ」、[Wikipedia](https://ja.wikipedia.org/wiki/菅田天神社)の版103658801は「かんだてんじんしゃ」 | 名称・所在地一致。A:自治体・国税庁の読み／B:Wikipediaの読み／C:保留。神社自身の読みは未確認。回答待ち |
| R011 | 天神社／埼玉県所沢市坂之下64 | [神社庁詳細](https://www.saitama-jinjacho.or.jp/shrine/8909/)は全文読みなし。国税庁法人番号6030005003411は「テンジンジャ」、[Wikipedia](https://ja.wikipedia.org/wiki/天神社_(所沢市))の版108317039は「てんじんしゃ」 | 所在地一致。追加の一次資料またはユーザー判断が必要 |

同名の別施設の読みで補わず、「じんじゃ／じんしゃ」のどちらかを一般的な読みから選ぶこともしません。

## 全文読みの追加監査による保留

公式の読み欄の原文に、途中読みや誤記等の疑いがある54登録を出力から一時退避しました。誤りと断定した一覧ではなく、原文のまま全文読みとして採用できるかを独立した資料で確認する対象です。原文に接尾語を付け足したり、小書きへ変更したりしていません。既存のR001–R009の回答とは重複しません。

名称の語尾だけで一律に変更せず、「山神社／やまがみしゃ」などは今回の退避対象に含めていません。「八幡神社／はちまんぐう」「白髭大明神社／しらひげだいみょうじん」も語尾だけで誤りと断定せず、元の掲載読みを維持しています。

| 都道府県・掲載名 | 掲載読み原文 | 所在地 | 要確認の理由 |
| --- | --- | --- | --- |
| 千葉県 [八幡神社](https://hiroba.jinja.ne.jp/ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html?mode%3Asearch=1&s%3Aj_ADDR_1%3Alike%3A1%3AADDR%3Aand=&s%3Aj_ADDR_PREF%3Afb%3A1%3AADDR%3Aand=%90%E7%97t%8C%A7&search%3Ahits=3145&search%3Amethod=group&search%3Apage=33&search%3Areverse=&search%3Aterm=30&sys%3Apid=2734&sys%3Arandom=1794149488-2734&view%3Areload=&view%3Asort=jinja_id&view%3Aterm=30&view%3Atotal=3177&view%3Apage=34) | ハチマンジジャ | 千葉県 船橋市 前貝塚町534番地 | 語末の表記に疑義 |
| 千葉県 [大宮八幡神社](https://hiroba.jinja.ne.jp/ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html?mode%3Asearch=1&s%3Aj_ADDR_1%3Alike%3A1%3AADDR%3Aand=&s%3Aj_ADDR_PREF%3Afb%3A1%3AADDR%3Aand=%90%E7%97t%8C%A7&search%3Ahits=3145&search%3Amethod=group&search%3Apage=16&search%3Areverse=&search%3Aterm=30&sys%3Apid=2311&sys%3Arandom=1794149420-2311&view%3Areload=&view%3Asort=jinja_id&view%3Aterm=30&view%3Atotal=3177&view%3Apage=17) | オオミヤハチマンジンジヤ | 千葉県 南房総市富浦町 豊岡1-1 | 大書きカナの確認が必要 |
| 千葉県 [日枝神社](https://hiroba.jinja.ne.jp/ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html?mode%3Asearch=1&s%3Aj_ADDR_1%3Alike%3A1%3AADDR%3Aand=&s%3Aj_ADDR_PREF%3Afb%3A1%3AADDR%3Aand=%90%E7%97t%8C%A7&search%3Ahits=3145&search%3Amethod=group&search%3Apage=13&search%3Areverse=&search%3Aterm=30&sys%3Apid=2268&sys%3Arandom=1794149408-2268&view%3Areload=&view%3Asort=jinja_id&view%3Aterm=30&view%3Atotal=3177&view%3Apage=14) | ヒエジンッジャ | 千葉県 鴨川市 江見西真門57番地 | 重複・挿入文字に疑義 |
| 千葉県 [熊野神社](https://hiroba.jinja.ne.jp/ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html?mode%3Asearch=1&search%3Amethod=group&view%3Asort=jinja_id&s%3Aj_ADDR_PREF%3Afb%3A1%3AADDR%3Aand=%90%E7%97t%8C%A7&s%3Aj_ADDR_1%3Alike%3A1%3AADDR%3Aand=) | クマノジジャ | 千葉県 勝浦市 赤羽根143 | 語末の表記に疑義 |
| 千葉県 [熊野神社](https://hiroba.jinja.ne.jp/ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html?mode%3Asearch=1&s%3Aj_ADDR_1%3Alike%3A1%3AADDR%3Aand=&s%3Aj_ADDR_PREF%3Afb%3A1%3AADDR%3Aand=%90%E7%97t%8C%A7&search%3Ahits=3145&search%3Amethod=group&search%3Apage=25&search%3Areverse=&search%3Aterm=30&sys%3Apid=2524&sys%3Arandom=1794149456-2524&view%3Areload=&view%3Asort=jinja_id&view%3Aterm=30&view%3Atotal=3177&view%3Apage=26) | クマノジンマンチ | 千葉県 市原市 西野238番地 | 語末の表記に疑義 |
| 千葉県 [白山神社](https://hiroba.jinja.ne.jp/ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html?mode%3Asearch=1&s%3Aj_ADDR_1%3Alike%3A1%3AADDR%3Aand=&s%3Aj_ADDR_PREF%3Afb%3A1%3AADDR%3Aand=%90%E7%97t%8C%A7&search%3Ahits=3145&search%3Amethod=group&search%3Apage=27&search%3Areverse=&search%3Aterm=30&sys%3Apid=2532&sys%3Arandom=1794149464-2532&view%3Areload=&view%3Asort=jinja_id&view%3Aterm=30&view%3Atotal=3177&view%3Apage=28) | ハクサンジジャ | 千葉県 市原市 上高根989番地 | 語末の表記に疑義 |
| 千葉県 [鳥見神社](https://hiroba.jinja.ne.jp/ycDB/Board.cgi/001/db/ycDB-pc-jinja_list.html?mode%3Asearch=1&s%3Aj_ADDR_1%3Alike%3A1%3AADDR%3Aand=&s%3Aj_ADDR_PREF%3Afb%3A1%3AADDR%3Aand=%90%E7%97t%8C%A7&search%3Ahits=3145&search%3Amethod=group&search%3Apage=52&search%3Areverse=&search%3Aterm=30&sys%3Apid=2904&sys%3Arandom=1794149563-2904&view%3Areload=&view%3Asort=jinja_id&view%3Aterm=30&view%3Atotal=3177&view%3Apage=53) | トミジジャ | 千葉県 印西市 大森1943番地 | 語末の表記に疑義 |
| 埼玉県 [久伊豆神社](https://www.saitama-jinjacho.or.jp/shrine/11678/) | ひさいずじじゃ | 蓮田市藤ノ木4-223 | 語末の表記に疑義 |
| 埼玉県 [横見神社](https://www.saitama-jinjacho.or.jp/shrine/11481/) | よこみじじゃ | 吉見町久保田117 | 語末の表記に疑義 |
| 埼玉県 [白山太神社](https://www.saitama-jinjacho.or.jp/shrine/11520/) | はくさんだいじじゃ | 川島町出丸中郷331 | 語末の表記に疑義 |
| 埼玉県 [白髭神社](https://www.saitama-jinjacho.or.jp/shrine/10084/) | しらひげじじゃ | 深谷市上原214 | 語末の表記に疑義 |
| 埼玉県 [香取神社](https://www.saitama-jinjacho.or.jp/shrine/11841/) | かとりじじゃ | 吉川市会野谷2-18 | 語末の表記に疑義 |
| 埼玉県 [香取神社](https://www.saitama-jinjacho.or.jp/shrine/11854/) | かとりじじゃ | 松伏町築比地2254 | 語末の表記に疑義 |
| 大阪府 [稲荷神社](https://www.osaka-jinjacho.jp/funai_jinja/dai2shibu/takatsuki-city/takatsuki.html) | いなりじんや | 高槻市奈佐原元町 | 語末の表記に疑義 |
| 宮城県 [羽黒神社](https://miyagi-jinjacho.or.jp/jinja-search/list.php?per_page=15&page=41) | はぐろじじゃ | 宮城県栗原市一迫柳の目字曽根除下50 | 語末の表記に疑義 |
| 岡山県 [素盞嗚神社](https://www.okayama-jinjacho.or.jp/search/list/page/20/) | スサノヲンジャ | 岡山市南区灘崎町片岡1677･1678 | 語末の表記に疑義 |
| 愛媛県 [萩岡神社](https://ehime-jinjacho.jp/jinja/?p=474) | はぎおかじんじや | 新居浜市萩生1163 | 大書きカナの確認が必要 |
| 愛知県 [久多神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | くだ | 愛知県稲沢市東畑６丁目１０番 | 全文読み未確認（短い名称部分） |
| 愛知県 [伊久波神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | いくは | 愛知県稲沢市平和町下三宅郷内四一九番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [八幡神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | はちまんんじゃ | 愛知県豊田市伊保町宮本２０番地 | 重複・挿入文字に疑義 |
| 愛知県 [八柱神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | やはしらじんんじゃ | 愛知県豊田市八草町森下９９番地 | 重複・挿入文字に疑義 |
| 愛知県 [八柱神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | やはしらじんんじゃ | 愛知県豊田市寺下町宮前２０番地 | 重複・挿入文字に疑義 |
| 愛知県 [八柱神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | やはしらじんんじゃ | 愛知県豊田市成合町下成合１８１番地 | 重複・挿入文字に疑義 |
| 愛知県 [内荒神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | ないこう | 愛知県稲沢市平和町法立国道東一三七番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [千代神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | ちしろ | 愛知県稲沢市千代町御堂先14番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [古天神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | こてん | 愛知県稲沢市井堀中郷町113番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [嚴島神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | いつくしま | 愛知県稲沢市祖父江町大字四貫字弁才天1287番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [尾張大國靈神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | おわりおおくにたま | 愛知県稲沢市国府宮1丁目1番1号 | 全文読み未確認（短い名称部分） |
| 愛知県 [川曲神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | こうわ | 愛知県稲沢市子生和町北屋敷1406番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [布智神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | ふち | 愛知県稲沢市祖父江町本甲宮東4番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [正明神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | しょうみょう | 愛知県稲沢市正明寺一丁目四番一六号 | 全文読み未確認（短い名称部分） |
| 愛知県 [清水神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | しみず | 愛知県稲沢市清水町鎮守871番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [白髭神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | しらひげ | 愛知県稲沢市祖父江町大字四貫字宮屋敷一八七番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [皇大明神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | こうたいみょう | 愛知県稲沢市祖父江町大字中牧字宮原464番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [神明神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | しんめいじんんじゃ | 愛知県豊田市小呂町森下112番地 | 重複・挿入文字に疑義 |
| 愛知県 [稻葉神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | いなば | 愛知県稲沢市稲沢町北山2丁目53番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [裳咋神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | もくい | 愛知県稲沢市目比町字天神東1244番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [西山神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | にしやまじんんじゃ | 愛知県豊田市若草町２丁目２６番地３ | 重複・挿入文字に疑義 |
| 愛知県 [豊藤稲荷神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | とよふじいなり | 愛知県名古屋市緑区作の山町180番地 | 全文読み未確認（短い名称部分） |
| 愛知県 [金神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | こがね | 愛知県稲沢市西町一丁目一四番二〇二号 | 全文読み未確認（短い名称部分） |
| 愛知県 [鹽江神社](https://aichi-jinjacho.or.jp/index.php/search/shrine) | しおえ | 愛知県稲沢市中野宮町85番地 | 全文読み未確認（短い名称部分） |
| 石川県 [白山神社](https://www.ishikawa-jinjacho.or.jp/page/52/?s) | はくさんじじゃ | 鳳珠郡穴水町東中谷ヘ1 | 語末の表記に疑義 |
| 福井県 [国中神社](https://www.jinja-fukui.jp/result/?SearchType=1&Chiku=01) | くになかちょう | 福井県越前市国中町５８－２７ | 地名など別項目の疑い |
| 福井県 [坂門一言神社](https://www.jinja-fukui.jp/result/?SearchType=1&Chiku=01) | さかとひとことじじゃ | 福井県大野市牛ヶ原７５－５６ | 語末の表記に疑義 |
| 福井県 [岡太神社](https://www.jinja-fukui.jp/result/?SearchType=1&Chiku=01) | おかもとちょう | 福井県越前市岡本町２１－１８ | 地名など別項目の疑い |
| 福井県 [神明神社](https://www.jinja-fukui.jp/result/?SearchType=1&Chiku=01) | ひがしやま | 福井県あわら市東山３９－４ | 地名など別項目の疑い |
| 静岡県 [和光明神社](http://www.shizuoka-jinjacho.or.jp/shokai/search.php?mode=city&search=&city=19&p=4) | わこう | 富士市久沢1262-2 | 全文読み未確認（短い名称部分） |
| 静岡県 [熊野八坂神社](http://www.shizuoka-jinjacho.or.jp/shokai/search.php?mode=city&city=4) | くまのやさか | 伊豆の国市南江間186 | 全文読み未確認（短い名称部分） |
| 鳥取県 [大野見宿禰命神社](https://tottori-jinjacho.jp/pages/185/) | おおのみのすくねのみことじんじや | 鳥取市徳尾80 | 大書きカナの確認が必要 |
| 鳥取県 [寳宮神社](https://tottori-jinjacho.jp/pages/539/) | ほうきゅうじんじや | 大山町倉谷1110－1 | 大書きカナの確認が必要 |
| 鳥取県 [武郷神社](https://tottori-jinjacho.jp/pages/540/) | たけさとじんじや | 大山町小竹1048 | 大書きカナの確認が必要 |
| 鳥取県 [葭津神社](https://tottori-jinjacho.jp/pages/339/) | よしづじんじや | 米子市葭津1736 | 大書きカナの確認が必要 |
| 鳥取県 [逢坂八幡神社](https://tottori-jinjacho.jp/pages/541/) | おおさかはちまんじんじや | 大山町松河原233 | 大書きカナの確認が必要 |
| 鹿児島県 [二本神社](https://www.kagojinjacho.or.jp/category/shrine-search/area-oosumi/page/14/) | ニホンジジャ | 肝属郡錦江町田代川原919 | 語末の表記に疑義 |

同名・同所在地に照合する施設レコードが複数ある22件は、Wikipediaの全文読みを保存したうえで、施設の対応が一意に確認できるまで別途保留しています。名称だけで施設を統合していません。

## 全保留データ

上記は全保留データの一覧ではありません。神社庁に読みがないもの、所在地不足、読み欄の別称・注記混入、複数社併記、一覧と詳細の不一致などが別に残ります。未調査のものを「Wikipediaでも見つからなかった」とは扱いません。参考資料で解決できるものを照合し、それでも不明なものを個別判断の対象とします。

全件の状態・件数は毎回正本から再生成します。

```sh
python3 -m njd validate
python3 -m njd build --formats mozc,macos,json,csv
```

`dist/dictionaries/pending.json` と `excluded.json` が全件リストです。`national/json.json`・`national/csv.csv`には施設の所在地・掲載URL・原文・根拠・状態を含みます。`report.json`は県別件数、`reviews.json`は人手による登録判断です。技術的なIME仕様確認待ちは [FORMATS.md](FORMATS.md)、地域の収集範囲は [SOURCES.md](SOURCES.md)を参照してください。

## 新潟の掲載全文読みを個別照合した登録

専用のふりがな欄に全文が明記されている次の5件は、名称・所在地と同じ行であることを個別に照合し、掲載読みをそのまま採用しました。一般的な語尾チェックと異なるための保留を解除する判断で、綴り修正や接尾辞補完は行っていません。取得原文は変更せず、URL・ページhash・原文・判断根拠を `data/corrections.json` の `literal_agency_reading_confirmation` に保存しています。

| 掲載名 | 掲載全文読み | 所在地 |
| --- | --- | --- |
| 大神社 | おおみわのやしろ | 糸魚川市大字平1345番地 |
| 甲埜神社諏訪神社合殿 | きのえのじんじゃすわじんじゃごうでん | 上越市名立区森57番地 |
| 熊野三社 | くまのさんじゃ | 上越市吉川区川谷2278番地甲 |
| 八幡宮 | やはたぐう | 上越市西本町3丁目5番15号 |
| 羽黒三社 | はぐろさんじゃ | 胎内市羽黒775番地 |

南魚沼市姥沢新田358番地の「十二神社・巻機神社」は、掲載全文「じゅうにじんじゃ・まきはたじんじゃ」の区切りと照合し、2つの正式名を個別登録しました。施設IDは1件のまま、判断は `data/reviews.json` の `source_review` に保存しています。ユーザーの追加回答とは区別します。
