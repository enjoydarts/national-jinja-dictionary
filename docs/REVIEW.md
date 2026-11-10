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

次の登録は実資料の読みが食い違うため、補正を`needs_review`として辞書出力を保留しています。各原文・確認日時・版・所在地は`data/corrections.json`に保持しています。既存のR001–R009の回答は変更していません。

| 番号 | 施設・所在地 | 確認済みの資料と候補 | 現在の状態 |
| --- | --- | --- | --- |
| R010 | 菅田天神社／山梨県甲州市塩山上於曽1054 | [神社庁詳細](https://www.yamanashi-jinjacho.or.jp/intro/search/detail/2012)は全文読みなし。国税庁法人番号9090005003832と[甲州市公式観光情報](https://www.koshu-kankou.jp/map/m5097.html)は「かんだてんじんじゃ」、[Wikipedia](https://ja.wikipedia.org/wiki/菅田天神社)の版103658801は「かんだてんじんしゃ」 | 名称・所在地一致。A:自治体・国税庁の読み／B:Wikipediaの読み／C:保留。神社自身の読みは未確認。回答待ち |
| R011 | 天神社／埼玉県所沢市坂之下64 | [神社庁詳細](https://www.saitama-jinjacho.or.jp/shrine/8909/)は全文読みなし。国税庁法人番号6030005003411は「テンジンジャ」、[Wikipedia](https://ja.wikipedia.org/wiki/天神社_(所沢市))の版108317039は「てんじんしゃ」 | 所在地一致。追加の一次資料またはユーザー判断が必要 |
| R012 | 石部神社／滋賀県愛知郡愛荘町沓掛147 | [神社庁詳細](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=898)のカナは「イソベ」。[愛荘町公式資料の画像](https://www.town.aisho.shiga.jp/material/files/group/5/K-05.jpg)は全文「いしべじんじゃ」と同一番地を明記 | A:町公式資料の「いしべじんじゃ」を採用／B:保留継続。回答待ち。神社庁の語幹に語尾を推定追加しない |

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

## 京都の個別資料で未解決の事項

右京区の39施設は掲載名・所在地を保存し、全文読みを確認できない登録は出力していません。部分的な「ちご」の注記だけで「兒(ちご）神社」の全文読みを補完しません。次の相違も原文を保ち、施設別の調査根拠を `data/sources/kyoto.json` の `reading_research` に保存しています。

| 掲載名 | 未解決事項 |
| --- | --- |
| 山國神社 | [神社庁一覧](http://www.kyoto-jinjacho.or.jp/shrine/01.html)は「山國」、[実リンク先詳細](http://www.kyoto-jinjacho.or.jp/shrine/27/210/)は「山国」。全文読みなし |
| 春日神社／西院 | 神社庁一覧は西院春日町4、[リンク先公式サイト](http://www.kasuga.or.jp/)は西院春日町61。住所の差と全文読みが未解決 |

別の同名施設の読みを流用せず、異体字・住所を自動修正しません。

## 京都・福岡の資料補完

神社庁の掲載名・所在地を収録条件にしたまま、同じ施設を特定できる資料で次の全文読みを補完しました。神社庁の空欄の読み原文は変更せず、取得日時・ページhash・Wikipediaの版と利用条件は `data/corrections.json` へ保存しています。

| 掲載名 | 採用する全文読み | 確認資料 |
| --- | --- | --- |
| 愛宕神社／京都市右京区嵯峨愛宕町1 | あたごじんじゃ | [Wikipedia](https://ja.wikipedia.org/wiki/愛宕神社)の掲載名直後の全文読み・所在地。神社公式フレームでは所在地のみ確認 |
| 住吉大伴神社／京都市右京区龍安寺住吉町1 | すみよしおおともじんじゃ | [Wikipedia](https://ja.wikipedia.org/wiki/住吉大伴神社)の掲載名直後の全文読み・所在地 |
| 香椎宮／福岡市東区香椎4-16-1 | かしいぐう | [公式記事](https://kashiigu.com/r4-goannai-tamagoichi-keisekigoshuin/)の香椎宮ウォークラリーとHTML図説明の全文カナ、同じページの施設名・所在地 |
| 筥崎宮／福岡市東区箱崎1-22-1 | はこざきぐう | [Wikipedia](https://ja.wikipedia.org/wiki/筥崎宮)の掲載名直後の全文読み・所在地 |
| 太宰府天満宮／太宰府市宰府4-7-1 | だざいふてんまんぐう | [Wikipedia](https://ja.wikipedia.org/wiki/太宰府天満宮)の太字名直後の全文読み・所在地。後続の「さいふ」は地名「宰府」の読みで、神社名の別読みではないことを個別確認 |

香椎宮の根拠は画像の文字推測やローマ字変換ではなく、実HTMLの `figcaption` です。記事題名にある鶏石神社を、香椎宮の読み対象へ混入させていません。

## 福岡4地域一覧の読み補完と資料間の相違

公開一覧280施設のうち、77施設の全文読みを出典付きで確認しました。今回追加した74施設は、国税庁の登録全文フリガナとWikipediaの実記事を施設ごとに照合したものです。同じ施設の両資料が同じ読みを示す7件は、両方の根拠を保存しています。国税庁の法人名・全文住所は神社庁掲載と照合し、閉鎖法人・複数法人の候補は採用していません。登録フリガナの確認と、神社自身に発音を確認したことは区別します。

現人神社／那珂川市仲3-6-20は、国税庁の「あらひとじんじゃ」とWikipediaの「あらひとじんしゃ」が食い違いました。[神社自身の公式「由緒と歴史」](https://arahito.com/history/)で「現人神社（あらひとじんじゃ）」と同一所在地を確認し、公式の全文読みを採用しています。Wikipediaの相違は `superseded_reference_reading` と参照原文に残しています。ユーザーが回答した読みとは扱いません。

国税庁の資料は [法人番号公表サイト・全件データ](https://www.houjin-bangou.nta.go.jp/download/zenken/index.html)の福岡県CSV（2026年10月30日、ファイルID28480）です。出典表示・加工表示・利用条件URL・元フリガナ・住所・法人番号・CSV行番号・ZIP内ファイル名・hashを各補正に保持しています。全文CSV・ページ本文・画像は公開していません。

## 京都31地域一覧と補足読みの照合

神社庁入口からリンクされた31地域一覧の1,581行を、名称・所在地・郵便番号・出典位置に照合しました。旧右京区39施設のIDと原文を保持しています。舞鶴・宮津の入口リンク表示はリンク先の地域と入れ替わっているため、所在地の決定には使用しません。外字画像2施設は原タグを保持して保留しています。

国税庁の2026年10月30日全件データの登録名・全文フリガナ・全住所を165施設、Wikipediaの本文冒頭の全文読み・所在地・版IDを59施設について照合しました。重なる11施設の読みは一致し、新規補完は213施設です。既存2施設と神社公式サイトで確認した北野天満宮1施設を合わせ、確認済み読みは216施設、重複除去後の辞書行は162行です。補足資料は神社庁への掲載条件を代替しません。原文・資料hash・照合住所・確認日時は `data/corrections.json` に保存しています。取得したページ本文・ZIP・画像は収録していません。実際のIME取り込みは未確認です。

京都の外字2施設は、舞鶴市広報と与謝野町の文化財発表資料も実取得しました。舞鶴市南田辺の名称は資料で「鸕鷀神社」、読み注記は「うのもり」までです。与謝野町岩屋の資料本文テキストは「阿知江●部神社」、読み注記は「あちえいそべ」までです。いずれも全文読みと所在地の番地までの対応を確定していないため、接尾語を補わず保留します。資料URL・hash・原文・不足情報は該当施設の `reading_research` に保存しました。

## 兵庫の公開地図検索と個別プロフィール

公式JavaScriptが用いる矩形検索の実応答3,834コードから、先頭2000施設をプロフィールの掲載名・全文カナ・所在地・印字コードと照合しました。以前の確認範囲のうち照合範囲外8施設を残し、正本は2008施設です。選択した矩形は検索条件であり、県境・サイト全件・上限なしを確認したものではありません。全文読みの適格施設は1996施設、重複除去後の辞書行は908行です。

大神宮神社（コード6301041、神戸市中央区中尾町10-20）の原文カナ「ナカオダイジングウジンジャ」は、掲載名との対応が未解決です。取得側が再び確認済みと分類しても、独立した補正の保留判断によって辞書出力を防ぎます。外字のUnicode確認で住所・コード・XML同一コードの原名衝突を解消したことにはしません。実際のIME取り込みは未確認です。

## 高知の公開一覧の全ページ照合

公開CMSの352ページすべてを取得し、全4,215行のCMS IDと表示行IDの集合を照合しました。名称・所在地のある4,214施設と、いずれも空欄の1行を分けています。以前の4,202施設のID・名称/読み/所在地の原文tuple・hashを保持し、118ページの12施設を追加しました。公開CMSの全表示行を調査したという範囲であり、県内全神社数を証明するものではありません。全文読みは一覧に掲載されず、補足資料で確認できた登録だけを辞書へ出力します。

## 京都の神社公式サイト補完と兵庫のプロフィール照合

北野天満宮は、神社庁がリンクする[神社公式サイト](https://kitanotenmangu.or.jp/)のHTML descriptionに「北野天満宮（きたのてんまんぐう）」、同ページに掲載所在地「京都市上京区馬喰町」を確認しました。京都の補完読みは216施設、府内の重複除去後辞書行は162行です。他の公式リンク先9施設は全文読み未掲載、名称・住所の相違、接続失敗などを解決できず保留し、該当施設の `official_site_reading_research` に原文と不足情報を保存しました。

兵庫は選択矩形のXMLが返した3834コードすべてのプロフィールをXML・掲載名・全文カナ・所在地・印字コード・hash・日時で照合しました。旧2008施設のID・原文と人手補正を保持し、正本は3834施設、読み適格3810施設、兵庫内の重複除去後辞書行は1632行です。応答内の走査は完了しましたが、県内全神社・サイト全件性や検索上限は未確認です。コード6301041の保留は維持しています。コード6305032（川西市火打2-18-7）は、[詳細ページ](https://www.hyogo-jinjacho.com/data/6305032.html)の「八阪神社／ヤサカジンジャ」と公式XMLの「八坂神社」が相違します。[川西市](https://www.city.kawanishi.hyogo.jp/shiseijoho/machi/keikan/1018977.html)も「八坂神社／川西市火打2丁目18-7」と掲載し、神社庁がリンクする兼務神社の対象ページは404でした。相違を無断統一せず保留しています。

## 兵庫の市名変更と注記名の補正

市公式条例に基づき、XMLの「篠山市」と詳細の「丹波篠山市」の市名部分だけが異なる172施設を比較しました。残りの住所全文・掲載名・印字コードの一致が条件です。元の文字列とhashを保持し、各施設の `address_comparisons` に根拠を保存しています。味淵神社は市名照合が通っても、全文読み2種の併記を解消していないため登録を保留しています。

[丹波市観光協会の記事](https://www.tambacity-kankou.jp/spot/spot-1606/)は「𡶌部神社（いそべじんじゃ）」、丹波市氷上町石生526、神社庁と同じ電話番号、社務所の文責を明示しています。記事の実HTMLの字（U+21D8C）を根拠に補正し、元の「イソ部神社(イソは山篇に石)」を保持しています。協会は神社自身のサイトとは区別し、市の公式リンクで運営主体も確認しました。別番地532の市文化財表は、この補正の住所根拠に使用していません。

| コード | 掲載名 | 保留事項 |
| --- | --- | --- |
| 6301041 | 大神宮神社 | 原名にない地名を含む全文カナとの対応 |
| 6305032 | 八阪神社 | XMLは八坂神社 |
| 6306023 | 天満神社 | XMLは末西天満宮 |
| 6306046 | 駒宇佐八幡宮 | XMLは駒宇佐八幡神社 |
| 6306053 | 東山八幡神社 | XMLは東山八幡宮 |
| 6307008 | 佐佐婆神社 | XML地番376、詳細地番377 |
| 6307024 | 波々伯部神社 | 詳細所在地の丹波が重複 |
| 6307065 | 味淵神社 | ミジブチジンジャ（アジブチジンジャ）の併記 |
| 6308001 | 柏原八幡宮 | XMLは柏原八幡神社 |

## 兵庫の追加掲載名と読み欄の確認

主掲載名が「大明神」「稲荷」で終わる4施設は、h1の施設名・専用カナ欄・印字コード・所在地・XMLの照合を行い、そのままの掲載名に対する全文読みを確認しました。原文は保持し、カタカナからひらがなへの機械変換のみを補正として保存しています。通称欄の名称は追加していません。

| 神社庁掲載名 | 登録読み | 実掲載ページ |
| --- | --- | --- |
| 住吉大明神 | すみよしだいみょうじん | [6311154](https://www.hyogo-jinjacho.com/data/6311154.html) |
| 若森稲荷大明神 | わかもりいなりだいみょうじん | [6313067](https://www.hyogo-jinjacho.com/data/6313067.html) |
| 若一王子大明神 | わかいちおうじだいみょうじん | [6313068](https://www.hyogo-jinjacho.com/data/6313068.html) |
| 琴雪稲荷 | ことゆきいなり | [6316055](https://www.hyogo-jinjacho.com/data/6316055.html) |

未解決の登録は計24件です。前掲9件に加え、天津神社6310104はXMLの「字下馬場」の省略、八幡神社6310112はXMLの「字峠」の省略、二子住吉神社6314166はXML名「阿閇神社」との相違を保留しています。すべて原文と出典を保持し、照合できない名称や住所の部分を削って出力することはしていません。

追加の12件は以下です。掲載カナの順序・接尾語や住所を推測で修復していません。各コードは神社庁の実掲載ページを参照します。

| コード | 掲載名 | 保留事項 |
| --- | --- | --- |
| [6316218](https://www.hyogo-jinjacho.com/data/6316218.html) | 天満宮社 | 掲載カナ「テンマンジンジャ」と掲載名の対応 |
| [6317006](https://www.hyogo-jinjacho.com/data/6317006.html) | 大歳神社 | 所在地「神崎郡神河福本528-1」に町の表記がない |
| [6317009](https://www.hyogo-jinjacho.com/data/6317009.html) | 薬王子神社 | 所在地「神崎郡神河東柏尾718-1」に町の表記がない |
| [6317064](https://www.hyogo-jinjacho.com/data/6317064.html) | 一之宮與位神社 | 掲載カナ「ノミヤヨイジンジャイチ」の順序 |
| [6320017](https://www.hyogo-jinjacho.com/data/6320017.html) | 天神神社 | 詳細・XMLに所在地がなく、郵便番号のみ |
| [6320027](https://www.hyogo-jinjacho.com/data/6320027.html) | 庥篥神社 | XML名「篥神社」と詳細名が相違 |
| [6322026](https://www.hyogo-jinjacho.com/data/6322026.html) | ●神社(舟偏に益) | 外字の確定根拠が不足 |
| [6325035](https://www.hyogo-jinjacho.com/data/6325035.html) | 藤井神社 | 掲載カナ「フジイシャジン」の順序 |
| [6326027](https://www.hyogo-jinjacho.com/data/6326027.html) | 大野八幡神社 | 掲載カナ「ハチマンジンジャオオノ」の順序 |
| [6328113](https://www.hyogo-jinjacho.com/data/6328113.html) | 貴船神社 | 詳細・XMLに所在地がない |
| [6328128](https://www.hyogo-jinjacho.com/data/6328128.html) | 西濱神社 | XML名「住吉神社」と詳細名が相違 |
| [6328164](https://www.hyogo-jinjacho.com/data/6328164.html) | 鳥飼八幡宮 | 詳細・XMLに所在地がない |

## 滋賀の全文読み補完

地主神社（神社庁掲載所在地：大津市葛川坊村町）は、[大津の観光協会ページ](https://otsu.or.jp/thingstodo/spot199/)の見出し・専用ふりがな欄「じしゅじんじゃ」・住所欄「日本、〒520-0475 滋賀県大津市葛川坊村町116」を実HTMLで照合しました。[大津市歴史博物館](https://www.rekihaku.otsu.shiga.jp/db/jiten/data/006.html)の同名・同町の記事にも全文読みがあります。神社庁の原文は変更せず、読みを出典・ページhash付きの補正として保存しています。同名の他施設には適用していません。

## 兵庫・㯮椒神社の外字補正

[神社庁6322137](https://www.hyogo-jinjacho.com/data/6322137.html)の原名「●椒神社(●は燭の火篇が木篇)」を、[実参考記事の保存版](https://ja.wikipedia.org/w/index.php?title=%E3%AF%AE%E6%A4%92%E7%A5%9E%E7%A4%BE&oldid=110313094)のUnicode表記「㯮椒神社」から補正しました。部首の説明から字を推定したものではありません。読みは神社庁の専用カナ欄「ハジカミジンジャ」を採用し、参考記事の全文読みとも一致します。

参考記事にある神社庁の対象プロフィールへの実リンクを開き、HTTPから同じHTTPSページへの302転送と本文hashの一致を確認しました。参考住所「兵庫県豊岡市竹野町椒字岩内1738-2」と神社庁住所「豊岡市竹野町椒1738-2」は町名・全地番が一致し、差は「字岩内」の有無です。双方の住所原文とリンク・転送・hash・取得日時を補正根拠に保持しています。別の市町・地番・枝番・異体字の差や、リンクのない資料へこの判断を広げません。

## 岐阜の776施設部分範囲の照合

保存済みの公式一覧15・検索317・詳細776の計1108ページから776施設を照合しました。既存550施設の全レコードを保持し、追加226施設の掲載名・専用全文カナ・所在地・`shrno`・ページhash・取得日時を元HTMLと独立に照合しています。対応する検索・一覧の実hrefも確認しました。

同名44群は施設番号と所在地で区別しています。同じ読み・表記・品詞の辞書行だけを出力時に重複除去します。以前の名前解決失敗から通常取得で復旧した詳細ページの履歴は、ページhash・日時とともに `previous_acquisition_failures` に保持しています。

施設数の上限なしで取得しましたが、熊野神社の検索7ページ目で接続拒否が発生し停止しました。今回の失敗1URL、未取得13URLと後続索引を保存しています。成功した応答キャッシュを再使用し、直近の再開は5秒間隔・再試行0回でした。間隔変更との因果やサイト全体の障害とは断定していません。表示828件は名称・読みグループ登録行数で、確認したのは300行です。県内施設総数・一覧走査完了とは主張していません。

## 高知の追加4施設の登録フリガナ照合

公式一覧118ページの拡張分について、保存済みの[国税庁全件データ](https://www.houjin-bangou.nta.go.jp/download/zenken/index.html)（2026-10-30、高知県、file ID 28477）を再照合しました。名称・全所在地が一致する一意な存続法人で、全文フリガナが明記された以下の4施設を補完しています。登録フリガナの裏づけであり、神社へ発音を問い合わせたことを意味しません。

| 神社庁掲載名 | 登録読み | 神社庁掲載所在地 | 法人番号 | CSV行 |
| --- | --- | --- | --- | --- |
| 君子方神社 | くしかたじんじゃ | 香南市香我美町中西川字宮ﾉ谷1508番地 | 3490005005067 | 8565 |
| 阿梨宮神社 | ありみやじんじゃ | 香南市香我美町中西川字大東2726番地 | 4490005005017 | 11496 |
| 天満宮 | てんまんぐう | 香南市香我美町上分尾ﾉ上3210番地 | 6490005004999 | 17324 |
| 八幡宮 | はちまんぐう | 香南市香我美町山北字城山4063番地 | 6490005005031 | 17328 |

元の読み空欄と住所表記を保持し、国税庁の原文・CSV行・ZIP内メンバー名・hash・出典加工表示を補正に保存しています。旧652施設と合わせ、読み適格は656施設です。公開一覧352ページの走査完了と、全文読みの補完範囲は別々に数えています。

## 滋賀の344詳細と全文読みの照合

一覧1434施設のうち、保存済み国税庁資料に一意の名称・所在地・全文フリガナ候補がある344施設の詳細を調査しました。一覧の実リンク・施設ID・名称と、詳細の番地までの鎮座地を照合し、290施設の全文読みを補完しています。既存90施設と合わせ380施設が読み適格です。国税庁資料は2026-10-30現在、滋賀県file ID 28432、ZIP内メンバー25_shiga_all_20261030.csvです。

詳細タイトルの最初のカナと末尾の別称を分離する解析へ修正し、344施設を保存済みHTMLで再照合しました。別称をカナとして表示していた保留記録を訂正しています。修正前に別称を辞書へ出力したものはありません。新たに条件を満たした10施設は実HTMLと国税庁原文から独立照合し、別称を登録せず掲載名の全文読みだけを採用しました。

都久夫須麻神社は神社庁詳細の「ツクブスマ」と、[滋賀県観光情報の明示された全文読み・所在地](https://www.biwako-visitors.jp/spot/detail/1312/)を照合し「つくぶすまじんじゃ」を採用しました。国税庁の「ツクフスマジンジャ」は未採用の参考原文として保持しています。観光情報に併記された別称の登録は追加していません。

神社庁詳細が名称全体のカナを明記する以下の4施設は、その一次出典を採用します。国税庁候補の所在地・読みとの相違は未採用参考として残し、同一の町名だけで国税庁候補を施設と同一視しません。

| 掲載名・神社庁詳細 | 所在地原文 | 明示された全文カナ | 登録読み |
| --- | --- | --- | --- |
| [八幡宮](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=871) | 滋賀県東近江市中岸本町434 | ハチマングウ | はちまんぐう |
| [大将軍神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1425) | 滋賀県高島市新旭町安井川314 | タイショウグンジンシャ | たいしょうぐんじんしゃ |
| [天満宮](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1386) | 滋賀県高島市安曇川町五番領233 | テンマングウ | てんまんぐう |
| [榊宮社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=28) | 滋賀県大津市坂本4-9-57 | サカキノミヤシロ | さかきのみやしろ |

石部神社（愛荘町沓掛147）は[町公式資料の画像](https://www.town.aisho.shiga.jp/material/files/group/5/K-05.jpg)に「いしべじんじゃ」と明記されていますが、神社庁の「イソベ」と相違するため保留を継続します。画像の原本は配布せず、リンク・hash・短い転記と確認根拠を補正参考欄に保存しています。伊夫岐神社も[県観光情報](https://www.biwako-visitors.jp/spot/detail/349/)の「いぶきじんじゃ」と神社庁の「イフキ」の相違が解消しないため、候補を勝手に選びません。

神社庁の「ヒエ」に対する国税庁「ヒエダジンジャ」、「テンマ」に対する「テンマンジンジャ」は、先頭が一致していても名称末尾以外の音が相違します。この2件も保留とし、どちらかの読みを推定して選びません。

残る54候補は以下の相違を保持し、辞書に出力しません。神社庁の語幹に語尾を推定追加せず、名称・字・番地を削除して一致させることもしません。原文、実リンク、hash、取得日・確認日、採用・保留理由は data/corrections.json に保存しています。元の一覧の所在地や読み空欄は変更していません。

### 読みが食い違う21候補（未登録）

国税庁欄は参考候補の原文です。名称・所在地等の照合が通らない候補については、当該施設との同一性も未確定です。

| 神社庁詳細（掲載名） | 詳細の名称・カナ原文 | 詳細の所在地原文 | 国税庁候補の名称・所在地・カナ原文 |
| --- | --- | --- | --- |
| [日枝神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=285) | 日枝神社 / ヒエ | 滋賀県近江八幡市田中江町131 | 日枝神社 / 滋賀県近江八幡市田中江町１３１番地 / ヒエダジンジャ |
| [天満神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=819) | 天満神社 / テンマ | 滋賀県東近江市今町41 | 天満神社 / 滋賀県東近江市今町４１番地 / テンマンジンジャ |
| [三十八社神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=577) | 三十八社神社 / サンジュウハッシャ | 滋賀県甲賀市水口町伴中山2645 | 三十八社神社 / 滋賀県甲賀市水口町伴中山２６４５番地 / サンジュウハチシャジンジャ |
| [三所神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=399) | 三所神社 / サンショ | 滋賀県東近江市市辺町1081 | 三所神社 / 滋賀県東近江市市辺町１０８１番地 / ミショジンジャ |
| [二童子神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=636) | 二童子神社 / ニドウジ | 滋賀県甲賀市信楽町中野140 | 二童子神社 / 滋賀県甲賀市信楽町中野１４０番地 / ニドウシジンジャ |
| [伊夫岐神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1000) | 伊夫岐神社 / イフキ | 滋賀県米原市伊吹603 | 伊夫岐神社 / 滋賀県米原市伊吹６０３番地 / イブキジンジャ |
| [八宮赤山神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=836) | 八宮赤山神社 / ハチノミヤアカヤマ | 滋賀県東近江市小川町1410 | 八宮赤山神社 / 滋賀県東近江市小川町１４１０番地 / ハチミヤアカヤマジンジャ |
| [冠者殿神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=33) | 冠者殿神社 / カンジャデン | 滋賀県大津市坂本5-24-46 | 冠者殿神社 / 滋賀県大津市坂本５丁目２４番４６号 / カジャドノジンジャ |
| [勝手神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=668) | 勝手神社 / カツテ | 滋賀県蒲生郡竜王町岡屋1347 | 勝手神社 / 滋賀県蒲生郡竜王町大字岡屋１３４７番地 / カッテジンジャ |
| [大将軍神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=32) | 大将軍神社 / タイショウグン | 滋賀県大津市坂本6-1-19 | 大将軍神社 / 滋賀県大津市坂本６丁目１番１９号 / ダイショウグンジンジャ |
| [大川神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1293) | 大川神社 / オカワ | 滋賀県長浜市西浅井町余1146 | 大川神社 / 滋賀県長浜市西浅井町余１１４６番地 / オオカワジンジャ |
| [天川命神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1209) | 天川命神社 / アマガワノミコト | 滋賀県長浜市高月町雨森1185 | 天川命神社 / 滋賀県長浜市高月町雨森１１８５番地 / アマカワノミコトジンジャ |
| [小川原神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=934) | 小川原神社 / コガハラ | 滋賀県犬上郡甲良町小川原499 | 小川原神社 / 滋賀県犬上郡甲良町大字小川原４９９番地 / コガワラジンジャ |
| [屋棟神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=502) | 屋棟神社 / ヤムネ | 滋賀県野洲市永原546 | 屋棟神社 / 滋賀県野洲市永原５４６番地 / ヤナムネジンジャ |
| [忍海神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=207) | 忍海神社 / オシウミ | 滋賀県長浜市寺田町318 | 忍海神社 / 滋賀県長浜市寺田町３１８番地 / ニンカイジンジャ |
| [意冨布良神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1250) | 意冨布良神社 / オオフラ | 滋賀県長浜市木之本町木之本488 | 意冨布良神社 / 滋賀県長浜市木之本町木之本４８８番地 / オオホラジンジャ |
| [望湖古宮神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=829) | 望湖古宮神社 / ボウコフルミヤ | 滋賀県東近江市伊庭町779 | 望湖古宮神社 / 滋賀県東近江市伊庭町７７９番地 / ボウココミヤジンジャ |
| [百枝天満神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=39) | 百枝天満神社 / モモエテンマングウ | 滋賀県大津市坂本6-2-28 | 百枝天満神社 / 滋賀県大津市坂本６丁目２番２８号 / モモエテンマンジンジャ |
| [石部神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=898) | 石部神社 / イソベ | 滋賀県愛知郡愛荘町沓掛147 | 石部神社 / 滋賀県愛知郡愛荘町沓掛１４７番地 / イシベジンジャ |
| [菅原神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=77) | 菅原神社 / スガハラ | 滋賀県大津市膳所平尾町987 | 菅原神社 / 滋賀県大津市膳所平尾町９８７番地 / スガワラジンジャ |
| [谷王神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=999) | 谷王神社 / ヤオ | 滋賀県米原市小泉406 | 谷王神社 / 滋賀県米原市小泉４０６番地 / タニオウジンジャ |

### 名称・所在地等の照合が通らない33候補（未登録）

国税庁欄は参考候補の原文です。名称・所在地等の照合が通らない候補については、当該施設との同一性も未確定です。

| 神社庁詳細（掲載名） | 詳細の名称・カナ原文 | 詳細の所在地原文 | 国税庁候補の名称・所在地・カナ原文 |
| --- | --- | --- | --- |
| [今宮天満宮神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=299) | 今宮天満宮神社 / イマミヤテンマング | 滋賀県近江八幡市浅小井町531 | 今宮天満宮神社 / 滋賀県近江八幡市浅小井町５３０番地 / イマミヤテンマングウジンジャ |
| [住吉神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=202) | 住吉神社 / スミヨシ | 滋賀県長浜市地福寺町996 | 住吉神社 / 滋賀県長浜市地福寺町８番１９号 / スミヨシジンジャ |
| [八幡神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=10) | 八幡神社 / ハチマン | 滋賀県大津市真野谷口町309 | 八幡神社 / 滋賀県大津市真野谷口町１７番３号 / ハチマンジンジャ |
| [八幡神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=397) | 八幡神社 / ハチマン | 滋賀県東近江市中羽田町169 | 八幡神社 / 滋賀県東近江市中羽田町１６８番地３５ / ハチマンジンジャ |
| [八幡神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1031) | 八幡神社 / ハチマン | 滋賀県米原市枝折566 | 八幡神社 / 滋賀県米原市枝折５６６番地５６７番地 / ハチマンジンジャ |
| [八田神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=576) | 八田神社 / ハツタ | 滋賀県甲賀市水口町八田187 | 八田神社 / 滋賀県甲賀市水口町八田１８７番地・１８８番地 / ハッタジンジャ |
| [八阪神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=635) | 八阪神社 / ヤサカ | 滋賀県甲賀市信楽町柞原332 | 八阪神社 / 滋賀県甲賀市信楽町柞原３２１番地 / ヤサカジンジャ |
| [加茂神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1423) | 加茂神社 / カモ | 滋賀県高島市新旭町新庄488 | 加茂神社 / 滋賀県高島市新旭町新庄４４８番地の１ / カモジンジャ |
| [古矢真神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1139) | 古矢真神社 / コヤマ | 滋賀県長浜市湖北町伊部44 | 古矢真神社 / 滋賀県長浜市湖北町伊部４５番地 / コヤマジンジャ |
| [天神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=817) | 天神社 / テン | 滋賀県東近江市佐野町799 | 天神社 / 滋賀県東近江市佐野町７４５番地 / テンジンジャ |
| [宇和宮神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=384) | 宇和宮神社 / ウワミヤ | 滋賀県栗東市蜂屋231 | 宇和宮神社 / 滋賀県栗東市蜂屋２３１番地１ / ウワミヤジンジャ |
| [山神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=100) | 山神社 / ヤマ | 滋賀県大津市太子1-2-1 | 山神社 / 滋賀県大津市太子１丁目２番１１号 / ヤマジンジャ |
| [川桁神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=907) | 川桁神社 / カワケタ | 滋賀県彦根市出路町640 | 川桁神社 / 滋賀県彦根市出路町４３７番地 / カワケタジンジャ |
| [愛知神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=926) | 愛知神社 / エチ | 滋賀県犬上郡豊郷町吉田1177 | 愛知神社 / 滋賀県犬上郡豊郷町大字吉田１１７７番地の１ / エチジンジャ |
| [日吉神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=860) | 日吉神社 / ヒヨシ | 滋賀県東近江市青山町66 | 日吉神社 / 滋賀県東近江市青山町６１６番地 / ヒヨシジンジャ |
| [日吉神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1410) | 日吉神社 / ヒヨシ | 滋賀県高島市鴨2395 | 日吉神社 / 滋賀県高島市鴨２２９５番地 / ヒヨシジンジャ |
| [日吉神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1389) | 日吉神社 / ヒヨシ | 滋賀県高島市安曇川町西万木783 | 日吉神社 / 滋賀県高島市安曇川町西万木７８３番地の１ / ヒヨシジンジャ |
| [日置神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1338) | 日置神社 / ヒオキ | 滋賀県高島市今津町酒波855 | 日置神社 / 滋賀県高島市今津町酒波８５５番地８５９番地 / ヒオキジンジャ |
| [日高神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1086) | 日高神社 / ヒダカ | 滋賀県長浜市当目町551 | 日高神社 / 滋賀県長浜市当目町３７３番地 / ヒダカジンジャ |
| [春日神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=575) | 春日神社 / カスガ | 滋賀県甲賀市水口町春日1803-2 | 春日神社 / 滋賀県甲賀市水口町春日１８０３番地の２、１８０４番地 / カスガジンジャ |
| [杉尾神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=637) | 杉尾神社 / スギオ | 滋賀県甲賀市信楽町杉山73 | 杉尾神社 / 滋賀県甲賀市信楽町杉山７３、７４番地 / スギオジンジャ |
| [杉崎稲荷神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=727) | 杉崎稲荷神社 / スギサキイナリ | 滋賀県蒲生郡日野町松尾1179 | 杉崎稲荷神社 / 滋賀県蒲生郡日野町松尾５丁目８４ / スギサキイナリジンジャ |
| [樹下神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=8) | 樹下神社 / コノモト | 滋賀県大津市真野佐川町515 | 樹下神社 / 滋賀県大津市真野佐川町６番１７号 / ジュゲジンジャ |
| [河内神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=9) | 河内神社 / カワチ | 滋賀県大津市真野大野549 | 河内神社 / 滋賀県大津市真野大野１丁目１０番５号 / カワチジンジャ |
| [津野神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=1352) | 津野神社 / ツノウ | 滋賀県高島市今津町角川95 | 津野神社 / 滋賀県高島市今津町角川７８番地 / ツノジンジャ |
| [白鳥神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=769) | 白鳥神社 / シラトリ | 滋賀県東近江市市原野町2128 | 白鳥神社 / 滋賀県東近江市市原野町２１２８番地１ / シラトリジンジャ |
| [神山神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=629) | 神山神社 / コウヤマ | 滋賀県甲賀市信楽町神山1994 | 神山神社 / 滋賀県甲賀市信楽町神山１９９２番地 / コウヤマジンジャ |
| [神明神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=204) | 神明神社 / シンメイ | 滋賀県長浜市勝町212 | 神明神社 / 滋賀県長浜市勝町５２６番地 / ジンメイジンジャ |
| [能登川神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=822) | 能登川神社 / ノトガワ | 滋賀県東近江市垣見町798 | 能登川神社 / 滋賀県東近江市垣見町７８８番地 / ノトガワジンジャ |
| [藤尾神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=57) | 藤尾神社 / フジオ | 滋賀県大津市藤尾奥町1-1 | 藤尾神社 / 滋賀県大津市藤尾奥町１０５番地 / フジオジンジャ |
| [賢木神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=149) | 賢木神社 / サカキ | 滋賀県彦根市安清町149 | 賢木神社 / 滋賀県彦根市安清町１番１号 / カタキジンジャ |
| [里宮神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=642) | 里宮神社 / サトミヤ | 滋賀県甲賀市信楽町多羅尾2017 | 里宮神社 / 滋賀県甲賀市信楽町多羅尾２１１６番地 / サトミヤジンジャ |
| [高宮神社](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=643) | 高宮神社 / タカミヤ | 滋賀県甲賀市信楽町多羅尾646 | 高宮神社 / 滋賀県甲賀市信楽町多羅尾６５６番地 / タカミヤジンジャ |

## 滋賀の掲載1434施設の詳細確認

一覧の同一行にある実リンク・施設番号・掲載名・所在地を、1434施設すべての詳細と照合しました。1432施設には名称・カナ・番地を含む鎮座地の原文参照を `data/sources/shiga.json` の `agency_detail_reading_research` に保存し、残る2施設の抽出不足も理由と出典を保持しています。短縮カナに語尾を追加していません。

独立照合した新規30施設の補正を追加しました。22施設は神社庁詳細が明記する全文カナ、8施設は同じ詳細の全住所と国税庁の一意な存続法人の名称・全文カナを照合しています。国税庁8件は保存した2026年10月30日版の実CSVから再抽出して確認しました。同名・同町でも施設番号と番地が異なる八幡神社・八坂神社・若宮神社は別施設として保持しています。既存の補正・除外・人手判断を変更していません。既存380施設と合わせ410施設が適格、1024施設の読みは未確定です。

[平野天神社・若宮八幡宮（施設番号406）](https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=406)は東近江市土器町1051、カナ原文は「ヒラノテンワカミヤ」です。最後が「みや」で終わるだけでは連記された名称全体の読みの根拠にならないため保留しました。各名称の全文読みの個別根拠が必要です。複数名称の区切りを持つ掲載名は自動で確認済みにせず、原文を残して個別確認へ回します。

1434詳細の確認完了と、全文読みの確認・県内全神社の網羅を区別します。実際のIME取り込みは未確認です。


## 熊本のExcel入力ふりがな候補

県名簿Excelの法人名称セル内に残る入力用ふりがな151施設分を、確認済みの読みと分離して保存しました。すでに別根拠で補正した5施設の判断は変えず、未補正146施設にもこの資料だけで読みを追加していません。完全な範囲のふりがなでも、入力履歴に由来する可能性があるため個別の全文読み資料で確認します。

合津神社は県名簿の入力用カナ「アイヅジンジャ」と、上天草市教育委員会の『上天草市の文化財』（2021年7月22日発行、印刷29頁）のルビ「あいつじんじゃ」が異なります。元のカナを無断修正せず、資料の性質と確認根拠を分けて保持します。


合津神社は、市の原PDFの印刷ルビ「あいつ」「じんじゃ」を画像でも確認し、名称・全文読み・所在地「熊本県上天草市松島町合津3820」を明記した[参考プロフィール](https://omairi.club/spots/126178)と照合して「あいつじんじゃ」を採用しました。神社庁に掲載された同名・同地域の対象は一意です。市資料そのものには番地がないこと、番地の補足が第三者プロフィールであることを補正記録に明記しています。市PDF・参考ページのhashと取得日、Excel未採用カナは別々に保存し、参考サイトを神社公式サイトとは扱いません。
