"""Evidence-backed overlays; acquired names/readings remain immutable."""
import copy
import re
import unicodedata
from datetime import datetime
from urllib.parse import urlsplit
from njd.normalize import normalize_reading, compare_address_units
from njd.municipalities import (
    FUJIYOSHIDA_RESIDENCE_PROOF, ISAHAYA_LOCALITY_PROOF, municipal_comparison_address,
)
from njd.locations import raw_address, _redirect_authority, _reference_in_scope, _hash, _date, _plain
from njd.corporate_aza import PROOF_KIND as REGISTERED_TOWN_PROOF, registered_town_matches
from njd.nantan_identity import PROOF_KIND as NANTAN_PROOF, nantan_reference_matches

_UJITAWARA_KOAZA_PROOF = 'ujitawara_documented_koaza_marker'
_UJITAWARA_WITNESS_HOSTS = {'ujitawara-kyoto.com', 'www.town.ujitawara.kyoto.jp', 'www.kyoto-be.ne.jp'}
# Published locality spellings and whole parcels, with sources in docs/DATA.md.
_PUBLISHED_PARCEL_SPELLINGS = {
    ('19', '笛吹市', '熊野神社', '笛吹市八代町北字竹之内1615'): '笛吹市八代町北1615',
    ('19', '南都留郡富士河口湖町', '諏訪神社', '南都留郡富士河口湖町精進西入84'):
        '南都留郡富士河口湖町精進84',
    ('20', '佐久市', '諏訪神社', '佐久市大字本新町49'): '佐久市本新町砂原49',
    ('20', '佐久市', '諏訪神社', '佐久市協和字蛇山6218'): '佐久市協和6218',
    ('20', '佐久市', '諏訪神社', '佐久市大字協和字宮久保650'): '佐久市協和650',
    ('20', '佐久市', '諏訪神社', '佐久市大字協和字伊咋田6694'): '佐久市協和6694',
    ('20', '佐久市', '諏訪神社', '佐久市大字協和字小平1319'): '佐久市協和1319',
    ('20', '佐久市', '諏訪神社', '佐久市大字下越字後田519'): '佐久市下越519',
    ('20', '下伊那郡大鹿村', '大磧神社', '下伊那郡大鹿村大字大河原字森下3402'):
        '下伊那郡大鹿村大字大河原3402',
    ('26', '福知山市', '天満神社', '福知山市上天津81.82.83.84合地'):
        '福知山市字上天津81・82・83・84番地合地',
    ('26', '南丹市', '八幡神社', '南丹市八木町池上北谷11-1'): '南丹市八木町池上北谷11番地ノ1',
    ('39', '四万十市', '天神社', '四万十市西土佐江川﨑2432'): '四万十市西土佐江川崎2432',
    ('39', '四万十市', '鷣神社', '四万十市西土佐江川﨑2972'): '四万十市西土佐江川崎2972',
    ('40', '柳川市', '日吉神社', '柳川市田脇947番地・946番地合併'): '柳川市田脇946・947',
    ('26', '亀岡市', '八幡宮社', '亀岡市曽我部町西條丙中垣内1-1'): '亀岡市曽我部町西条丙中垣内1-1',
    ('26', '亀岡市', '若宮神社', '亀岡市曽我部町南條中荒水代4'): '亀岡市曽我部町南条中荒水代4',
    ('37', '高松市', '三社神社', '高松市花宮町929'): '高松市花ノ宮町929',
    ('39', '香美市', '仁井田神社', '香美市香北町梅久保1230番地ロ'):
        '香美市香北町梅久保字向田1230番地ロ',
    ('42', '五島市', '神﨑神社', '五島市岐宿町川原字神﨑3482'): '五島市岐宿町川原字神崎3482',
    ('42', '平戸市', '淀姫神社', '平戸市大島村大字大島西宇戸免字石原1568'):
        '平戸市大島村西宇戸字石原1568',
    ('42', '壱岐市', '八坂神社', '壱岐市郷ノ浦町郷ノ浦313番地・314'): '壱岐市郷ノ浦町郷ノ浦313・314',
    ('42', '南松浦郡新上五島町', '蛭子神社', '南松浦郡新上五島町町飯ノ瀬戸郷10'):
        '南松浦郡新上五島町飯ノ瀬戸郷10',
    ('42', '南松浦郡新上五島町', '山神社', '南松浦郡新上五島町船崎郷字色摩245'):
        '南松浦郡新上五島町船崎郷色摩245',
    ('42', '南松浦郡新上五島町', '琴平神社', '南松浦郡新上五島町小串郷字園山467'):
        '南松浦郡新上五島町小串郷467',
    ('42', '南松浦郡新上五島町', '天満神社', '南松浦郡新上五島町岩瀬浦郷字杉ノ本642-2'):
        '南松浦郡新上五島町岩瀬浦郷642-2',
    ('42', '南松浦郡新上五島町', '塩竃神社', '南松浦郡新上五島町船崎郷字色摩247'):
        '南松浦郡新上五島町船崎郷247',
    ('42', '南松浦郡新上五島町', '潮目天満神社', '南松浦郡新上五島町七目郷字宮の下144'):
        '南松浦郡新上五島町七目郷144',
    ('42', '南松浦郡新上五島町', '大王神社', '南松浦郡新上五島町東神ノ浦郷字鯛の浦道脇266'):
        '南松浦郡新上五島町東神ノ浦郷266',
    ('19', '北杜市', '天神社', '北杜市武川町柳澤2351'): '北杜市武川町柳沢2351',
    ('20', '長野市', '諏訪社', '長野市松代町西條3161'): '長野市松代町西条3161',
    ('20', '長野市', '八幡神社', '長野市大字石渡字宮澤411'): '長野市大字石渡字宮沢411',
    ('20', '上田市', '葦原渕神社', '上田市下之條字若宮919'): '上田市下之条字若宮919',
    ('20', '上田市', '宮川神社', '上田市中之條字宮方586'): '上田市中之条字宮方586',
    ('20', '上田市', '須々岐神社', '上田市下之條字須々貴山1880'): '上田市下之条字須々貴山1880',
    ('20', '木曽郡南木曽町', '諏訪神社', '木曽郡南木曽町吾妻字廣瀬4441'): '木曽郡南木曽町吾妻字広瀬4441',
    ('20', '諏訪郡富士見町', '大理神社', '諏訪郡富士見町落合字澤良平12219'): '諏訪郡富士見町落合字沢良平12219',
    ('20', '上伊那郡南箕輪村', '日光社月光社合殿', '南箕輪村字澤尻8309'): '南箕輪村字沢尻8309',
    ('20', '上伊那郡辰野町', '神明神社', '上伊那郡辰野町大字伊那富字日向9610'):
        '上伊那郡辰野町大字伊那富日向9610',
    ('20', '上伊那郡辰野町', '鎮大神社', '上伊那郡辰野町大字沢底字ワゴ1856'):
        '上伊那郡辰野町大字沢底1856',
    ('20', '上田市', '篠井神社', '上田市古里字篠井窪1000番地イ'): '上田市古里字篠井窪1000-イ',
    ('20', '上田市', '大屋神社', '上田市大屋字南遠河原506'): '上田市大屋南遠河原506',
    ('20', '佐久市', '平井神社', '佐久市大字根岸字滝丿山4860'): '佐久市根岸字滝ノ山4860',
}
_KYOTO_GLYPH_PARCELS = {
    ('与謝郡与謝野町岩屋森谷763', '阿知江𡶌部神社'): (
        '与謝郡与謝野町字岩屋小字森谷763', '4130005009689', '00038800'),
    ('舞鶴市南田辺小字二の丸8', '鸕鷀神社'): (
        '舞鶴市字南田辺小字二の丸8', '4130005011587', '00038865'),
}


def _kyoto_glyph_parcel(value, ref, facility, changes):
    acquired = facility.get('address')
    surface = changes.get('surface')
    documented = _KYOTO_GLYPH_PARCELS.get((acquired, surface))
    if not documented or ref.get('name_raw') != surface:
        return value
    registered, corporation, image_id = documented
    if value == registered and ref.get('source_kind') == 'government_corporate_registry_glyph':
        base = 'https://www.houjin-bangou.nta.go.jp'
        profile = ref.get('registry_profile')
        image = ref.get('image_review')
        if (isinstance(profile, dict) and isinstance(image, dict)
                and ref.get('url') == profile.get('url') == base+'/henkorireki-johoto.html?selHouzinNo='+corporation
                and ref.get('page_hash') == profile.get('page_hash') and _hash(ref.get('page_hash'))
                and ref.get('address_raw') == profile.get('address_raw')
                and profile.get('image_id') == image.get('image_id') == image_id
                and image.get('url') == base+'/image?imageid='+image_id
                and _hash(image.get('page_hash')) and image.get('visual_reviewed') is True
                and image.get('printed_text') == surface):
            return acquired
    if (surface == '鸕鷀神社' and value == '舞鶴市南田辺8' and ref.get('source_kind') == 'independent_field_article'
            and ref.get('url') == 'https://www.buccyake-kojiki.com/archives/1066702507.html'
            and _hash(ref.get('page_hash')) and isinstance(ref.get('excerpt'),str)
            and '城内の二の丸に奉斎され' in ref['excerpt']):
        return acquired
    return value


def _url(value):
    if not isinstance(value,str):return False
    try:return urlsplit(value).scheme in ('http','https') and bool(urlsplit(value).hostname)
    except (TypeError,ValueError):return False


def discovery_only(value):
    """The user designated this directory for finding candidates, not evidence."""
    if not isinstance(value,str):return False
    try:host=(urlsplit(value).hostname or '').lower().rstrip('.')
    except ValueError:return False
    return host=='jinja-net.jp' or host.endswith('.jinja-net.jp')


def _comparison(value):
    """Matching only. Never writes normalized text to acquired/output fields."""
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',value or ''))


def _literal_reference_address(ref):
    """Retain separately printed CSV columns, without inventing a quotation."""
    parts=ref.get('address_components');excerpt=ref.get('excerpt','')
    if parts is None:
        return bool(ref.get('address_raw')) and ref['address_raw'] in excerpt
    columns=('都道府県名','市区町村名','住所')
    if (ref.get('source_kind')!='municipal_open_data' or not isinstance(parts,dict)
        or set(parts)!=set(columns) or type(ref.get('csv_row')) is not int
        or ref['csv_row']<2 or not _hash(ref.get('page_hash'))
        or not _plain(ref.get('locator'))):return False
    if any(not _plain(parts[k]) or k+'='+parts[k] not in excerpt for k in columns):return False
    return ref.get('address_raw')==''.join(parts[k] for k in columns)


def _subject_profile_link(ref,facility,proof):
    """Require recorded observations, not a guessed URL or a nearby-site link."""
    link=proof.get('subject_link')
    if not isinstance(link,dict):return False
    locator=link.get('locator')
    if (link.get('relation')!='subject_agency_profile' or
        not isinstance(locator,str) or not locator.strip() or
        link.get('reference_url')!=ref.get('url') or
        link.get('reference_page_hash')!=ref.get('page_hash')):return False
    def digest(value):return isinstance(value,str) and bool(re.fullmatch(r'[0-9a-f]{64}',value))
    if not digest(ref.get('page_hash')) or not digest(facility.get('page_hash')):return False
    href=link.get('href');target=facility.get('listing_url')
    if not _url(href) or not _url(target):return False
    before=urlsplit(href);after=urlsplit(target)
    # The only permitted redirect is the observed HTTP -> HTTPS upgrade of
    # the very same profile. No host/path/query substitution or credentials.
    if (before.username or before.password or after.username or after.password or
        before.fragment or after.fragment or
        (before.netloc,before.path,before.query)!=(after.netloc,after.path,after.query)):
        return False
    chain=link.get('responses')
    if not isinstance(chain,list) or len(chain) not in (1,2):return False
    if any(not isinstance(r,dict) for r in chain):return False
    if chain[0].get('url')!=href:return False
    for r in chain:
        if not digest(r.get('page_hash')):return False
        try:observed=datetime.fromisoformat(r.get('fetched_at',''))
        except (TypeError,ValueError):return False
        if observed.tzinfo is None:return False
    if len(chain)==2:
        if (before.scheme!='http' or after.scheme!='https' or
            chain[0].get('status') not in (301,302,307,308) or
            chain[0].get('location')!=target):return False
    elif href!=target:return False
    last=chain[-1]
    return (last.get('url')==target and last.get('status')==200 and
            last.get('page_hash')==facility['page_hash'])


def _additional_aza_matches(actual,expected,ref,facility):
    proof=ref.get('address_identity_proof')
    if not isinstance(proof,dict) or proof.get('kind')!='additional_aza_with_subject_link':return False
    extra=proof.get('added_aza_raw')
    if not isinstance(extra,str) or not re.fullmatch(r'(?:小字|字)[\u3400-\u9fff々〆ヶぁ-ゖァ-ヺー]+',extra):return False
    parcel=re.fullmatch(r'(.+?)([0-9]+(?:-[0-9]+)*)',expected)
    if not parcel or actual!=parcel[1]+extra+parcel[2]:return False
    return _subject_profile_link(ref,facility,proof)


def _nagano_booklet_address(ref,facility,entry):
    proof=ref['address_identity_proof']
    visual=ref.get('visual_review')
    if (facility.get('source_key')!='nagano' or facility.get('prefecture_code')!='20'
        or ref.get('source_kind')!='official_agency_booklet' or ref.get('reading_scope')!='full_name'
        or ref.get('name_raw')!=facility.get('listed_name') or not _url(ref.get('url'))
        or not _url(facility.get('listing_url')) or not _plain(ref.get('locator'))
        or not _plain(facility.get('address')) or not _plain(ref.get('address_raw'))
        or not _hash(ref.get('page_hash')) or not isinstance(visual,dict) or not _hash(visual.get('image_sha256'))):
        return None
    source=urlsplit(ref['url'])
    listing=urlsplit(facility['listing_url'])
    if (source.scheme!='https' or source.netloc!='www.nagano-jinjacho.jp'
        or listing.netloc!=source.netloc or source.query or source.fragment
        or not re.fullmatch(r'/_userdata/[A-Za-z0-9_-]+\.pdf',source.path)):
        return None
    original=re.fullmatch(r'.+?([0-9０-９]+(?:-[0-9０-９]+)*)',facility.get('address',''))
    printed=re.fullmatch(r'(.+?)([〇一二三四五六七八九]+(?:[-‐][〇一二三四五六七八九]+)*)',ref.get('address_raw',''))
    digest=entry.get('source_hash')
    if (not original or not printed or not _hash(digest) or facility.get('source_hash')!=digest
        or proof!=dict(kind='nagano_booklet_terminal_digits',expected_source_hash=digest,
            reference_page_hash=ref['page_hash'],original_number_raw=original[1],reference_number_raw=printed[2])):
        return None
    numeric=printed[2].translate(str.maketrans('〇一二三四五六七八九‐','0123456789-'))
    if numeric!=_comparison(original[1]):return None
    return printed[1]+numeric


def _ujitawara_koaza_matches(ref, facility, entry, changes):
    """Compare documented marker omission without changing the printed address."""
    proof = ref['address_identity_proof']
    witness = proof.get('municipality_witness')
    acquired = facility.get('address')
    digest = entry.get('source_hash')
    if (set(changes) != {'reading'} or entry.get('status') == 'excluded'
            or facility.get('source_key') != 'kyoto' or facility.get('prefecture_code') != '26'
            or facility.get('municipality') != '綴喜郡宇治田原町'
            or ref.get('name_raw') != facility.get('listed_name')
            or ref.get('reading_scope') != 'full_name'
            or not _hash(digest) or facility.get('source_hash') != digest
            or proof.get('expected_source_hash') != digest or proof.get('agency_address_raw') != acquired
            or not _hash(ref.get('page_hash')) or proof.get('reference_page_hash') != ref['page_hash']
            or not isinstance(witness, dict) or witness.get('name_raw') != ref['name_raw']
            or not _hash(witness.get('page_hash')) or witness['page_hash'] == ref['page_hash']
            or not _date(witness.get('checked_at')) or not _url(witness.get('url'))
            or witness['url'] == ref.get('url')
            or not _plain(witness.get('locator')) or not _plain(witness.get('excerpt'))):
        return False
    authority = urlsplit(witness['url'])
    if authority.scheme != 'https' or authority.netloc not in _UJITAWARA_WITNESS_HOSTS:
        return False
    source_address, witness_address = ref.get('address_raw'), witness.get('address_raw')
    if (not all(_plain(s) for s in (acquired, source_address, witness_address))
            or witness_address not in witness['excerpt'] or witness['name_raw'] not in witness['excerpt']):
        return False

    def municipal_part(value):
        text = _comparison(value).removeprefix('京都府').removeprefix('綴喜郡')
        text = re.sub(r'(?<=\d)(?:番(?:地)?(?:の)?|の)(?=\d)', '-', text)
        return re.sub(r'(?<=\d)(?:番地|番)$', '', text)

    locality = r'[\u3400-\u9fffぁ-ゖァ-ヶ々〆ー]+?'
    expected = municipal_part(acquired)
    parts = re.fullmatch(rf'宇治田原町大字({locality})小字({locality})([0-9]+(?:-[0-9]+)*)', expected)
    if not parts:
        return False
    oaza, koaza, parcel = parts.groups()
    area = f'宇治田原町大字{oaza}小字{koaza}'
    return (municipal_part(source_address) == f'宇治田原町{oaza}{koaza}{parcel}'
            and municipal_part(witness_address) in (area, expected))


def _reference_matches(ref,facility,entry,changes):
    registered_variant = 'registered_name_variant' in ref
    if registered_variant and (set(changes)!={'reading'} or entry.get('status')=='excluded'):
        return False
    names={_comparison(facility.get('listed_name')),_comparison(entry.get('surface')),
           _comparison(changes.get('surface'))}-{''}
    strict_registered_address=False
    if registered_variant or _comparison(ref.get('name_raw')) not in names:
        from njd.corporate import bound_registered_shrine_name
        bound_name=bound_registered_shrine_name(ref)
        if (not bound_name and not registered_variant and set(changes)=={'reading'}
            and entry.get('status')!='excluded' and facility.get('source_key')=='kumamoto'):
            from njd.kumamoto_location import yamato_registered_shrine_name
            bound_name=yamato_registered_shrine_name(ref,facility)
        if _comparison(bound_name) not in names:return False
        strict_registered_address=True
        if not re.search('[0-9０-９]',facility.get('address','')) or not re.search('[0-9０-９]',ref.get('address_raw','')):return False
    def address(value):
        value=re.sub(r'^〒\d{3}-\d{4}','',_comparison(value))
        value=value.removeprefix(facility.get('prefecture',''))
        if facility.get('prefecture_code')=='37' and facility.get('municipality')=='丸亀市':
            # The city records this locality as 三条町. Keep the parcel comparison exact.
            value=re.sub(r'^丸亀市三條町(?=\d)','丸亀市三条町',value)
        if facility.get('prefecture_code')=='26' and facility.get('municipality')=='木津川市':
            # The municipal address table assigns 平尾 to the former 山城町.
            value=re.sub(r'^木津川市山城町平尾里屋敷(?=\d)','木津川市平尾里屋敷',value)
        if facility.get('prefecture_code')=='26' and facility.get('municipality')=='京丹後市':
            # The published addresses use 小字 as a marker for these named localities.
            for district, subdistrict in (('峰山町鱒留', '大成'), ('峰山町泉', '奥山'), ('網野町生野内', '下大クゴ')):
                value=re.sub(rf'^(京丹後市{district})小字(?={subdistrict} ?\d)',r'\1',value)
        if facility.get('prefecture_code')=='40':
            # Use the published street spellings in these two Kitakyushu wards.
            value=re.sub(r'^北九州市八幡西区浅川日の峰(?=\d)','北九州市八幡西区浅川日の峯',value)
            value=re.sub(r'^北九州市八幡東区春ノ町(?=\d)','北九州市八幡東区春の町',value)
            if (facility.get('listed_name')=='八坂神社' and set(changes)=={'reading'}
                and value=='福岡市西区元岡26411'):
                # The corporate record and the independent site article show this branch.
                value='福岡市西区元岡2641-1'
        if facility.get('prefecture_code')=='42':
            # The Sasebo town directory uses 高梨町. Compare complete parcels.
            value=re.sub(r'^佐世保市髙梨町(?=\d)','佐世保市高梨町',value)
        value=compare_address_units(value)
        # The town's own ordinances use both spellings (docs/DATA.md).
        # Compare only this Kochi municipality, with a literal parcel present.
        # Never rewrite stored text, shrine names, or a locality elsewhere.
        if facility.get('prefecture_code')=='39' and facility.get('prefecture')=='高知県':
            value=re.sub(r'^(高岡郡)?檮原町(?=.*[0-9])',r'\1梼原町',value)
            # Compare the separators while keeping the ordered numbers and 合番地.
            value=re.sub(r'(?<=\d)(?:番地)?[.・](?=\d+合?番地$)','・',value)
            if (facility.get('municipality') == '室戸市' and facility.get('listed_name') == '惠美須神社'
                and set(changes) == {'reading'} and value == '室戸市元米ケ谷西甲2737番地15'):
                # The current registry and the MLIT locality use 米ヶ谷西.
                value = '室戸市元米ヶ谷西甲2737番地15'
        # Compare both endpoints of an explicitly marked parcel range.
        value = re.sub(r'自([0-9]+)(?:番地)?[.・]?至([0-9]+)(?:番地)?$', r'自\1至\2', value)
        value=re.sub(r'(?<=\d)[−‐‑‒–—―](?=\d)','-',value)
        # Preserve the literal kana in a parcel branch such as 2番地-イ.
        value=re.sub(r'(?<=\d)(?:番地)?[−‐‑‒–—―-](?=[ァ-ヶ]$)','-',value)
        value=re.sub(r'(?<=\d)丁目(?=\d)','-',value)
        value=re.sub(r'(?<=\d)番(?:地)?(?:の)?(?=\d)','-',value)
        value=re.sub(r'(?<=\d)(?:番地|番|号)$','',value)
        value=re.sub(r'(?<=\d)の(?=\d)','-',value)
        if set(changes) == {'reading'}:
            locality = (facility.get('prefecture_code'), facility.get('municipality'), facility.get('listed_name'))
            value = _PUBLISHED_PARCEL_SPELLINGS.get((*locality, value), value)
        if facility.get('prefecture_code') == '26' and 'surface' in changes:
            value = _kyoto_glyph_parcel(value, ref, facility, changes)
        if facility.get('prefecture_code') == '19' and set(changes) == {'reading'}:
            # The Minobu histories locate these shrines on the registered parcels.
            minobu_addresses = {
                ('十二天神社', '南巨摩郡身延町下八木沢字太田43'): '南巨摩郡身延町下八木沢43',
                ('山神社', '南巨摩郡身延町上八木沢宮之前18'): '南巨摩郡身延町上八木沢18',
                ('諏訪神社', '南巨摩郡身延町古関宮ノ平1382'): '南巨摩郡身延町古関1382',
            }
            value = minobu_addresses.get((facility.get('listed_name'), value), value)
        if (facility.get('prefecture_code')=='26' and facility.get('listed_name')=='阿良須神社'
            and set(changes)=={'reading'} and value=='舞鶴市大字小倉小字フル宮13'):
            # The shrine sign and the journal differ in the locality markers.
            return '舞鶴市小倉フル宮13'
        if (facility.get('prefecture_code')=='37' and facility.get('listed_name')=='幡羅八幡神社'
            and set(changes)=={'reading'} and value=='高松市牟礼町原井手東651'):
            # The prefecture documents 井手東 within 牟礼町原 at this locality.
            return '高松市牟礼町原651'
        if (facility.get('prefecture_code')=='47' and facility.get('listed_name')=='宮古神社'
            and set(changes)=={'reading'} and value=='宮古島市平良市西里5-1'):
            # The agency's own link leads to the shrine at this single parcel.
            return '宮古島市平良字西里5-1'
        return value.replace('大字','')
    def county(value):
        # A 市/区 before 郡 belongs to the municipality/locality, not an
        # omitted county. 高市郡 and 余市郡 are actual county names containing
        # 市 (official prefectural references are recorded in docs/DATA.md).
        match=re.match(r'((?:高市|余市|[^都道府県市区]+?)郡)(.+)',value)
        return match.groups() if match else ('',value)
    proof=ref.get('address_identity_proof')
    if isinstance(proof,dict) and proof.get('kind')==REGISTERED_TOWN_PROOF:
        return registered_town_matches(ref,facility,entry,changes)
    if isinstance(proof,dict) and proof.get('kind')==_UJITAWARA_KOAZA_PROOF:
        return _ujitawara_koaza_matches(ref,facility,entry,changes)
    if isinstance(proof, dict) and proof.get('kind') == NANTAN_PROOF:
        return nantan_reference_matches(ref, facility, entry, changes)
    if isinstance(proof, dict) and proof.get('kind') in (ISAHAYA_LOCALITY_PROOF, FUJIYOSHIDA_RESIDENCE_PROOF):
        if set(changes) != {'reading'} or entry.get('status') == 'excluded' or ref.get('reading_scope') != 'full_name':
            return False
        mapped = municipal_comparison_address(ref, facility, entry)
        return mapped is not None and address(mapped) == address(ref['address_raw'])
    if isinstance(proof,dict) and proof.get('kind')=='nagano_booklet_terminal_digits':
        matched=_nagano_booklet_address(ref,facility,entry)
        if set(changes)!={'reading'} or matched is None:return False
        reference_address=address(matched)
    elif 'article_address_context' in ref:
        from njd.article_context import article_context_address
        contextual=article_context_address(ref,facility)
        if set(changes)!={'reading'} or entry.get('status')=='excluded' or contextual is None:return False
        reference_address=address(contextual)
    elif 'booklet_address_context' in ref:
        from njd.booklet_context import booklet_context_address
        contextual=booklet_context_address(ref,facility)
        if set(changes)!={'reading'} or entry.get('status')=='excluded' or contextual is None:return False
        reference_address=address(contextual)
    elif 'csv_address_context' in ref:
        from njd.csv_context import csv_context_address
        contextual=csv_context_address(ref,facility)
        if set(changes)!={'reading'} or entry.get('status')=='excluded' or contextual is None:return False
        reference_address=address(contextual)
    elif 'document_address_context' in ref:
        from njd.document_context import document_context_address
        contextual=document_context_address(ref,facility)
        if (set(changes)!={'reading'} or entry.get('status')=='excluded'
            or contextual is None):return False
        reference_address=address(contextual)
    else:
        reference_address=address(ref.get('address_raw'))
    if set(changes)=={'reading'}:
        mapped=municipal_comparison_address(ref,facility,entry)
        if mapped is not None and address(mapped)==reference_address:return True
    sources=[facility.get('address')]
    detail=facility.get('address_source',{})
    if detail.get('url')==facility.get('native_source_id'):
        sources.append(detail.get('address_raw'))
    # A source may publish only a locality. Exact full street numbers, when
    # present, must match; do not accept lot 1 as a prefix of lot 10.
    for raw in sources:
        expected=address(raw)
        actual=reference_address
        if not expected or not actual:continue
        actual_county,actual_locality=county(actual)
        expected_county,expected_locality=county(expected)
        # Omission is permitted; explicitly different counties are not.
        if actual_county and expected_county and actual_county!=expected_county:continue
        actual,expected=actual_locality,expected_locality
        if actual==expected:return True
        if strict_registered_address:continue
        if _additional_aza_matches(actual,expected,ref,facility):return True
        suffix=actual[len(expected):] if actual.startswith(expected) else ''
        # Unit comparison can turn a locality word (五番領, 後三条町) into
        # digits. Keep the acquired locality's scope; the comparison must not
        # invent a parcel that was never printed in that agency row. A newly
        # converted terminal parcel number still cannot prefix another lot.
        original_locality=re.sub(r'^〒\d{3}-\d{4}','',_comparison(raw))
        if (not re.search(r'\d',original_locality) and not re.search(r'\d$',expected)
            and suffix and suffix[0].isdigit()):return True
    return False


def _official_reading_authority(correction,facility):
    proof=correction.get('official_site_binding')
    if proof is None:return None,[]
    if not isinstance(proof,dict):return None,['invalid official site binding']
    link=proof.get('agency_link');native=facility.get('official_site_url')
    if (not isinstance(link,dict) or not _url(native)
        or link.get('url')!=facility.get('listing_url') or link.get('name_raw')!=facility.get('name_raw')
        or link.get('address_raw')!=raw_address(facility) or link.get('href_raw')!=native
        or not _plain(link.get('locator')) or link['locator']!=facility.get('source_locator')
        or not _hash(link.get('page_hash')) or link['page_hash']!=facility.get('page_hash')
        or not _date(link.get('fetched_at'))):
        return None,['official site binding differs from the acquired agency name/address/link observation']
    return _redirect_authority(proof,native)


def _official_reading_reference(ref,authority,facility):
    return (isinstance(ref,dict) and ref.get('source_kind')=='official_shrine'
        and ref.get('name_raw')==facility.get('listed_name')
        and _reference_in_scope(authority,ref.get('url'))
        and urlsplit(ref['url']).query==urlsplit(authority).query
        and _hash(ref.get('page_hash')) and _date(ref.get('checked_at')) and _plain(ref.get('locator')))


def _linked_locality_reference(ref,correction,facility):
    """An observed agency link identifies its own site's more precise address.

    Permit a locality followed by a literal aza/parcel, or a single explicit
    aza marker with an otherwise identical full address. Neither case replaces
    an existing street number or authorizes another site's same-name facility.
    """
    authority,problems=_official_reading_authority(correction,facility)
    if (problems or not authority or set(correction.get('changes',{}))!={'reading'}
        or not _official_reading_reference(ref,authority,facility)):return False
    proof=ref.get('address_identity_proof');raw=raw_address(facility)
    if (not isinstance(proof,dict) or proof.get('kind') not in ('agency_linked_locality_with_aza','agency_linked_aza_marker')
        or proof.get('listing_address_raw')!=raw
        or proof.get('official_address_raw')!=ref.get('address_raw')):return False
    expected=_comparison(raw).removeprefix(facility.get('prefecture',''))
    actual=_comparison(ref.get('address_raw')).removeprefix(facility.get('prefecture',''))
    literal=(ref.get('name_raw') in ref.get('excerpt','')
        and bool(ref.get('address_raw')) and ref['address_raw'] in ref.get('excerpt',''))
    if proof['kind']=='agency_linked_aza_marker':
        # Only an explicit marker, not an added aza name or another parcel.
        marker=re.fullmatch(r'(.+[市区町村郡])字([^0-9]+)([0-9]+(?:-[0-9]+)*(?:番地|番|号)?)',actual)
        return (proof.get('added_marker_raw')=='字' and bool(marker)
            and ''.join(marker.groups())==expected and literal)
    if not expected or re.search(r'\d',expected) or not actual.startswith(expected):return False
    suffix=actual[len(expected):]
    return (bool(re.fullmatch(r'(?:小字|字)[\u3400-\u9fff々〆ヶぁ-ゖァ-ヺー]+[0-9]+(?:-[0-9]+)*(?:番地|番|号)?',suffix))
        and literal)


_KUMADE_BOOKLET = 'https://www.my-kagawa.jp/files/user/site/dd5996c1b191e7ca81631b1f5ab2e69fb5a1229e.pdf'


def _normalized_reference_reading(ref):
    """Remove only declared separators between literal kana in a full reading."""
    raw=ref.get('reading_raw','');steps=ref.get('reading_normalization')
    if steps is None:
        return normalize_reading(raw)
    if ref.get('reading_scope')=='full_name' and isinstance(raw,str):
        ruby_source = ref.get('source_kind') == 'official_shrine' or (
            ref.get('source_kind') == 'tourism_booklet_reference' and ref.get('url') == _KUMADE_BOOKLET
        )
        if (steps==['remove printed reading spaces'] and ruby_source
            and re.fullmatch(r'[ぁ-ゖァ-ヶゝゞー]+(?:[ \u3000]+[ぁ-ゖァ-ヶゝゞー]+)+',raw)):
            return normalize_reading(raw.replace(' ','').replace('\u3000',''))
        if (steps==['remove printed reading middle dots']
            and re.fullmatch(r'[ぁ-ゖァ-ヶゝゞー]+(?:・[ぁ-ゖァ-ヶゝゞー]+)+',raw)):
            return normalize_reading(raw.replace('・',''))
    raise ValueError('unsupported or nonmechanical reference reading normalization')


def _joined_official_reading(ref,correction,facility,entry):
    authority,problems=_official_reading_authority(correction,facility)
    changes=correction.get('changes',{})
    if (problems or not authority or set(changes)!={'reading'} or ref.get('address_raw')
        or not _official_reading_reference(ref,authority,facility)):return False
    return any(_official_reading_reference(r,authority,facility)
        and _reference_matches(r,facility,entry,changes) and isinstance(r.get('excerpt'),str)
        and r['name_raw'] in r['excerpt'] and r.get('address_raw') and r['address_raw'] in r['excerpt']
        for r in correction.get('references',[]))


# Inspected publications linking a full shrine reading to a specific site.
# Each distinct source keeps its actual name, address and reading fields.
_PUBLISHED_READING_PAIRS = {
    ('19', '鼓楽神社', '上野原市四方津1896'): (
        dict(url='https://gtfs-jp.buskita.com/fjb/gtfs.zip', source_kind='transit_operator_gtfs',
             locator='translations.txt 1495行 ja-Hrkt、対応するstops.txt 533行',
             name_raw='鼓楽神社', reading_raw='こらくじんじゃ',
             excerpt='field_value=鼓楽神社前 ／ translation=こらくじんじゃ'),
        dict(url='https://www.yamanashi-jinjacho.or.jp/intro/search/detail/8075', source_kind='official_agency',
             locator='神社名・コードNo.・鎮座地欄', name_raw='鼓楽神社',
             address_raw='上野原市四方津1896', excerpt='鼓楽神社 ／ 上野原市四方津1896'),
        dict(url='https://www.city.uenohara.yamanashi.jp/site/kyoiku/1581.html', source_kind='municipal_reference',
             locator='見出し・所在地欄', name_raw='鼓楽神社',
             address_raw='上野原市四方津1896', excerpt='鼓楽神社のウラジロガシ ／ 上野原市四方津1896'),
    ),
    ('20', '牛牧神社', '下伊那郡高森町大字牛牧2104'): (
        dict(url='https://kaisei-jp.net/ooshika/%E5%9C%B0%E8%B3%AA%E5%AD%A6/%E4%B8%8B%E4%BC%8A%E9%82%A3%E5%8C%97%E9%83%A8%E3%81%AE%E5%9C%B0%E5%BD%A2%E3%82%92%E8%A6%B3%E5%AF%9F/',
             source_kind='regional_field_observation', locator='断層地形解説の社名全文かなと写真見出し',
             name_raw='牛牧神社', reading_raw='うしまきじんじゃ', address_raw='高森町牛牧',
             excerpt='牛牧神社（うしまきじんじゃ） ／ 牛牧神社（高森町牛牧）'),
        dict(url='https://www.nagano-jinjacho.jp/shibu/hani.htm', source_kind='official_agency',
             locator='飯伊支部・牛牧神社の一覧行', name_raw='牛牧神社',
             address_raw='下伊那郡高森町大字牛牧2104', excerpt='牛牧神社 ／ 下伊那郡高森町大字牛牧2104'),
        dict(url='https://www.town.nagano-takamori.lg.jp/docs/12697.html', source_kind='municipal_reference',
             locator='牛牧獅子舞・祭りを行っている場所と牛牧神社の見出し', name_raw='牛牧神社',
             address_raw='高森町牛牧地区', excerpt='高森町牛牧地区の牛牧神社'),
    ),
    ('25', '山王神社', '東近江市建部北町'): (
        dict(url='https://repository.nabunken.go.jp/dspace/bitstream/11177/2472/1/CaoNews90.pdf',
             source_kind='national_research_publication',
             locator='PDF第55頁・印刷54頁の山王神社周辺見出しとルビと所在地',
             name_raw='山王神社周辺', reading_raw='さんのうじんじゃ', address_raw='滋賀県八日市市建部北町',
             excerpt='山王神社周辺／さんのうじんじゃ／滋賀県八日市市建部北町'),
        dict(url='https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode%3Aview=1&view%3Aoid=431',
             source_kind='official_agency', locator='.j_title・鎮座地欄', name_raw='山王神社',
             address_raw='滋賀県東近江市建部北町394', excerpt='山王神社／滋賀県東近江市建部北町394'),
        dict(url='https://www.post.japanpost.jp/cgi-zip/zipcode.php?city=1252051&id=99414&merge=2&pref=25',
             locator='八日市市建部北町の住所変更情報',
             municipal_change='旧八日市市から東近江市', town_raw='建部北町'),
    ),
    ('40', '大堰神社', '三井郡大刀洗町冨多1302'): (
        dict(url='https://www.qsr.mlit.go.jp/chikugo/archives/history/area/area4.html',
             source_kind='government_shrine_heritage_guide', locator='h3内のa[name=anchor031]と社名・全文かな',
             name_raw='大堰神社', reading_raw='おおぜきじんじゃ', excerpt='大堰神社（おおぜきじんじゃ）'),
        dict(url='https://oozekijinja.site/', source_kind='official_shrine_location_reference',
             name_raw='大堰神社', address_raw='福岡県三井郡大刀洗町冨多１３０２番地',
             excerpt='大堰神社 ／ 福岡県三井郡大刀洗町冨多１３０２番地'),
    ),
    ('37', '熊手八幡宮', '仲多度郡多度津町大字西白方200番地'): (
        dict(url=_KUMADE_BOOKLET, source_kind='tourism_booklet_reference',
             locator='PDF第2頁 B-4 ⑤の社名と全文ルビ', name_raw='熊手八幡宮',
             reading_raw='くま で はち まん ぐう', excerpt='熊手八幡宮 ／ くま で はち まん ぐう'),
        dict(url='https://www.town.tadotsu.kagawa.jp/soshikikarasagasu/kyoikuiinkaijimukyokusyougaigakusyuka/shakaikyoiku/2/565.html',
             source_kind='municipal_reference', locator='No.22 熊手八幡宮高麗犬の名称と所在地',
             name_raw='熊手八幡宮高麗犬', address_raw='多度津町大字西白方200(熊手八幡宮)',
             excerpt='熊手八幡宮高麗犬 ／ 多度津町大字西白方200(熊手八幡宮)'),
    ),
    ('39', '二社神社', '高知県吾川郡いの町柳瀬本村929番地'): (
        dict(url='https://niyodogawa.org/blog/niyodogawa/spot/11884/', source_kind='regional_editorial_reference',
             locator='節「二社神社とは」第一段落', name_raw='二社神社', reading_raw='にしゃじんじゃ',
             address_raw='高知県吾川郡いの町柳瀬本村',
             excerpt='二社神社（にしゃじんじゃ） / 高知県吾川郡いの町柳瀬本村'),
        dict(url='https://www.town.ino.kochi.jp/bunkazai/bunka_town_80/', source_kind='municipal_reference',
             locator='h2内rubyの「二社」「神社」と個別rt、所在地、冒頭', name_raw='二社神社',
             address_raw='いの町柳瀬本村', excerpt='二社（にしゃ）神社（じんじゃ） / いの町柳瀬本村'),
        dict(url='https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo=1490005002933',
             source_kind='government_corporate_register', name_raw='二社神社',
             locator='最新情報の法人番号、商号又は名称、本店又は主たる事務所の所在地',
             address_raw='高知県吾川郡いの町柳瀬本村９２９番地',
             excerpt='二社神社 / 高知県吾川郡いの町柳瀬本村９２９番地'),
    ),
    ('41', '金立神社', '佐賀市金立町大字金立３４１５'): (
        dict(url='https://tabi-bito.net/kinnryu-shrine-jogu/', source_kind='independent_site_visit',
             locator='主見出し及び上宮への現地参拝の記録', name_raw='金立神社',
             reading_raw='きんりゅうじんじゃ', excerpt='金立神社（きんりゅうじんじゃ）上宮'),
        dict(url='https://www.city.saga.lg.jp/bunka-sports/rekishi-bunkazai/4/3/2281.html',
             source_kind='municipal_reference', locator='金立神社上宮の見出し・所在地・史跡解説',
             name_raw='金立神社上宮', address_raw='佐賀市金立町大字金立',
             excerpt='金立神社上宮 ／ 佐賀市金立町大字金立 ／ 神殿・拝殿は県内でも珍しい石殿'),
        dict(url='https://saga-jinjacho.jp/%e9%87%91%e7%ab%8b%e7%a5%9e%e7%a4%be/',
             source_kind='official_agency', locator='当該社の神社名・鎮座地・社宝欄',
             name_raw='金立神社', address_raw='佐賀市金立町大字金立３４１５',
             excerpt='金立神社 ／ 佐賀市金立町大字金立３４１５ ／ 石造本社神殿拝殿（市文）'),
    ),
}


def _record_matches_publication(ref, fields):
    return (isinstance(ref, dict) and all(ref.get(key) == value for key, value in fields.items())
            and _hash(ref.get('page_hash')) and _date(ref.get('checked_at')))


def _joined_published_reading(ref, correction, facility):
    key = (facility.get('prefecture_code'), facility.get('listed_name'), raw_address(facility))
    sources = _PUBLISHED_READING_PAIRS.get(key)
    if (not sources or set(correction.get('changes', {})) != {'reading'}
            or (ref.get('address_raw') and 'address_raw' not in sources[0])
            or ref.get('reading_scope') != 'full_name'
            or not _record_matches_publication(ref, sources[0])):
        return False
    return all(any(_record_matches_publication(site, fields) for site in correction['references'])
               for fields in sources[1:])


def _joined_reading_reference(ref, correction, facility, entry):
    return (_joined_official_reading(ref, correction, facility, entry)
            or (entry.get('status') != 'excluded' and _joined_published_reading(ref, correction, facility)))


def _agency_reading_compatible(name,raw,scope,full):
    """Compare literal evidence, never construct a reading from a stem.

    An already supplied full reading may have only the stated shrine-name
    ending after the agency's stem. Prefix agreement cannot hide extra sounds.
    """
    try:stem=normalize_reading(raw)
    except (TypeError,ValueError):return False
    if stem==full:return True
    if scope=='full_name' or not full.startswith(stem):return False
    suffixes=[('神社',('じんじゃ','じんしゃ','しんじゃ','しんしゃ')),('神宮',('じんぐう',)),
        ('大社',('たいしゃ','だいしゃ','おおやしろ')),('宮',('ぐう','みや','きゅう')),('社',('しゃ','やしろ'))]
    endings=next((endings for suffix,endings in suffixes if name.endswith(suffix)),())
    return full[len(stem):] in endings


def correction_problems(correction,facility,entry,source=None):
    problems=[]
    if not isinstance(correction,dict):return ['invalid correction object']
    if correction.get('correction_kind')=='registered_name_image_full_reading':
        from njd.registered_name_image import image_correction_problems
        return image_correction_problems(correction,facility,entry,source)
    if correction.get('status')!='verified':return ['correction is not verified']
    if (source or {}).get('authority_status') in ('pending','unconfirmed'):
        problems.append('official agency listing authority remains unconfirmed')
    if entry.get('identity_review_required'):problems.append('facility identity still requires review')
    if correction.get('facility_id')!=facility['id']:problems.append('facility identity differs from correction target')
    if correction.get('expected_source_hash')!=entry.get('source_hash'):problems.append('correction is stale; acquired source changed')
    original=correction.get('original',{})
    expected=dict(name_raw=facility.get('name_raw'),reading_raw=entry.get('reading_raw'),address=raw_address(facility),listing_url=facility.get('listing_url'))
    snapshot_matches=original==expected
    if isinstance(original,dict) and set(original)==set(expected) and facility.get('native_source_id') and _url(original.get('listing_url')) and _url(expected['listing_url']):
        # Native facility identity and raw tuple/hash stay fixed even when a
        # CGI page adds pagination/session parameters. Keep the actual old
        # evidence URL; never rewrite it to a fabricated canonical URL.
        before=urlsplit(original.get('listing_url',''));after=urlsplit(expected['listing_url'])
        same_endpoint=bool(before.hostname) and (before.scheme,before.netloc,before.path,before.fragment)==(after.scheme,after.netloc,after.path,after.fragment)
        snapshot_matches=snapshot_matches or (same_endpoint and all(original[k]==expected[k] for k in ('name_raw','reading_raw','address')))
    if not snapshot_matches:problems.append('original source snapshot differs')
    if not correction.get('reason') or not correction.get('identity_match'):problems.append('missing correction reason or facility comparison')
    changes=correction.get('changes')
    if not isinstance(changes,dict) or not changes or set(changes)-{'surface','reading'}:
        return problems+['unsupported or missing correction changes']
    if any(not isinstance(v,str) or not v for v in changes.values()):return problems+['invalid corrected value']
    if any(ord(c)<32 or ord(c)==127 for c in changes.get('surface','')):problems.append('control character in corrected surface')
    if '<' in changes.get('surface','') or '>' in changes.get('surface',''):problems.append('corrected surface is not plain text')
    refs=correction.get('references')
    if not isinstance(refs,list) or not refs:return problems+['missing inspected references']
    authority,official_problems=_official_reading_authority(correction,facility);problems.extend(official_problems)
    article_context_present=any(isinstance(r,dict) and 'article_address_context' in r for r in refs)
    if article_context_present and (set(changes)!={'reading'} or entry.get('status')=='excluded'):
        problems.append('Article address context only supports reading corrections of non-excluded entries')
    booklet_context_present=any(isinstance(r,dict) and 'booklet_address_context' in r for r in refs)
    if booklet_context_present and (set(changes)!={'reading'} or entry.get('status')=='excluded'):
        problems.append('Numbered booklet context only supports reading corrections of non-excluded entries')
    csv_context_present=any(isinstance(r,dict) and 'csv_address_context' in r for r in refs)
    if csv_context_present and (set(changes)!={'reading'} or entry.get('status')=='excluded'):
        problems.append('CSV locality context only supports reading corrections of non-excluded entries')
    registry_present=any(isinstance(r,dict) and r.get('source_kind')=='government_corporate_register' for r in refs)
    name_supported='surface' not in changes;reading_supported='reading' not in changes;identity_supported=False
    for ref in refs:
        if not isinstance(ref,dict):problems.append('invalid reference object');continue
        if 'article_address_context' in ref:
            from njd.article_context import article_context_address
            if article_context_address(ref,facility) is None:problems.append('invalid explicit article address context')
        if 'booklet_address_context' in ref:
            from njd.booklet_context import booklet_context_address
            if booklet_context_address(ref,facility) is None:problems.append('invalid numbered booklet address context')
        if 'csv_address_context' in ref:
            from njd.csv_context import csv_context_address
            if csv_context_address(ref,facility) is None:problems.append('invalid same-record CSV locality context')
        if ref.get('source_kind')=='government_corporate_register':
            from njd.corporate import image_review_problems
            problems.extend(image_review_problems(ref))
        proof=ref.get('address_identity_proof')
        if (isinstance(proof,dict) and proof.get('kind')==REGISTERED_TOWN_PROOF
            and not registered_town_matches(ref,facility,entry,changes)):
            problems.append('registered name and parcel do not match the recorded official town row')
        if (isinstance(proof,dict) and proof.get('kind')==_UJITAWARA_KOAZA_PROOF
            and not _ujitawara_koaza_matches(ref,facility,entry,changes)):
            problems.append('Ujitawara shrine locality and full parcel do not match the recorded marker omission')
        if discovery_only(ref.get('url')):problems.append('discovery-only directory cannot serve as dictionary evidence')
        if not _url(ref.get('url')) or not ref.get('title') or not ref.get('source_kind'):
            problems.append('reference URL, title or source type missing')
        try:datetime.fromisoformat(ref.get('checked_at',''))
        except (TypeError,ValueError):problems.append('reference inspection date missing')
        if not ref.get('name_raw') or not ref.get('excerpt'):
            problems.append('reference name or actual excerpt missing')
        bound=(_reference_matches(ref,facility,entry,changes)
            or _linked_locality_reference(ref,correction,facility))
        nantan = isinstance(proof, dict) and proof.get('kind') == NANTAN_PROOF
        if nantan and not bound:
            problems.append('Nantan shrine identity differs from the inspected documents')
        joined=_joined_reading_reference(ref,correction,facility,entry)
        if (registry_present and bound and 'reading' in changes and ref.get('reading_raw')
            and ref.get('source_kind') in ('agency','official_agency')
            and ref.get('reading_scope') in ('full_name','partial_or_absent')
            and _url(ref.get('url')) and _url(facility.get('listing_url'))
            and urlsplit(ref.get('url','')).hostname==urlsplit(facility.get('listing_url','')).hostname
            and not _agency_reading_compatible(ref['name_raw'],ref['reading_raw'],ref['reading_scope'],changes['reading'])):
            problems.append('proposed registry reading conflicts with literal agency kana; prefix agreement alone is insufficient')
        if bound and ref.get('name_raw') and ref.get('name_raw') in ref.get('excerpt','') and (nantan or _literal_reference_address(ref)):
            identity_supported=True
        if bound and 'surface' in changes and ref.get('name_raw')==changes['surface'] and changes['surface'] in ref.get('excerpt',''):
            name_supported=True
        if 'reading' in changes:
            raw=ref.get('reading_raw','')
            try:
                if (bound or joined) and _normalized_reference_reading(ref)==changes['reading'] and raw in ref.get('excerpt',''):
                    reading_supported=True
            except (TypeError,ValueError):pass
    if not identity_supported:problems.append('no inspected reference explicitly identifies name and location')
    if not name_supported:problems.append('corrected name is not explicit in the inspected reference')
    if not reading_supported:problems.append('corrected full reading is not explicit in the inspected reference')
    return problems


def apply_corrections(data,document):
    if document.get('schema_version')!=1 or not isinstance(document.get('entries'),dict):
        raise ValueError('unsupported correction document')
    corrections=document['entries']
    if not corrections:return data
    result=copy.deepcopy(data);facilities={f['id']:f for f in result['facilities']};applied=[];pending=[];seen=set()
    for entry in result['entries']:
        correction=corrections.get(entry['id'])
        if correction is None:continue
        seen.add(entry['id']);facility=facilities[entry['facility_id']]
        source=result['collection'].get('sources',{}).get(facility.get('source_key'),result['collection'])
        problems=correction_problems(correction,facility,entry,source)
        entry['correction']=copy.deepcopy(correction)
        if problems:
            note=correction.get('reason','')
            references=correction.get('references')
            context_excluded=(entry.get('status')=='excluded' and isinstance(references,list)
                and any(isinstance(r,dict) and (
                    any(k in r for k in ('document_address_context','csv_address_context','booklet_address_context',
                                        'article_address_context','registered_name_variant'))
                    or (isinstance(r.get('address_identity_proof'),dict)
                        and r['address_identity_proof'].get('kind') in (REGISTERED_TOWN_PROOF, _UJITAWARA_KOAZA_PROOF,
                                                                       ISAHAYA_LOCALITY_PROOF, NANTAN_PROOF)))
                    for r in references))
            # A rejected contextual correction must not erase a durable
            # exclusion: otherwise a second application could approve it.
            if not context_excluded:
                entry['status']='pending';entry['reason']='; '.join(problems+[note if isinstance(note,str) else ''])
            entry['correction']['status']='needs_review';entry['correction']['validation_problems']=problems
            pending.append(entry['id']);continue
        changes=correction['changes']
        if 'surface' in changes:
            entry['surface']=changes['surface']
            # Only name-rendering defects can be resolved by a name reference.
            # Missing addresses, conflicting identities and multiple addresses
            # remain pending even when a reading/name is known elsewhere.
            name_can_be_resolved=bool(facility['name_raw'] or facility.get('native_source_id'))
            name_reasons={'control or layout characters in source name; explicit review required',
                          'source name uses an external glyph; Unicode correction requires references',
                          'missing name, address or municipality',
                          'regional agency name differs from linked detail name',
                          'annotated official name requires review'}
            name_only=facility['status']=='verified' or facility.get('reason') in name_reasons
            review_is_name_only=not facility.get('review_reason') or facility['review_reason'] in {
                'regional agency name differs from linked detail name','annotated official name requires review'}
            address_valid=facility['address'] and not any(ord(c)<32 or ord(c)==127 for c in facility['address'])
            if name_can_be_resolved and name_only and review_is_name_only and address_valid and facility['municipality'] and not facility.get('source_conflicts'):
                facility['status']='verified';facility['reason']=''
                facility['resolved_name_unicode']=changes['surface']
        if 'reading' in changes:
            entry['reading']=changes['reading'];entry['reading_source_kind']='reference'
            if correction.get('correction_kind')=='registered_name_image_full_reading':
                ref=correction['references'][1];entry['reading_url']=ref['url'];entry['checked_at']=ref['checked_at']
            reading_refs=[] if correction.get('correction_kind')=='registered_name_image_full_reading' else correction['references']
            for ref in reading_refs:
                try:matched=_normalized_reference_reading(ref)==entry['reading'] and ref.get('reading_raw','') in ref.get('excerpt','')
                except (TypeError,ValueError):matched=False
                if matched and (_reference_matches(ref,facility,entry,changes)
                                or _linked_locality_reference(ref,correction,facility)
                                or _joined_reading_reference(ref,correction,facility,entry)):
                    entry['reading_url']=ref['url'];entry['checked_at']=ref['checked_at'];break
        reading_resolved='reading' in changes
        if not reading_resolved:
            try:reading_resolved=normalize_reading(entry['reading_raw'])==entry['reading']
            except (TypeError,ValueError):reading_resolved=False
        entry['status']='verified' if facility['status']=='verified' and reading_resolved else 'pending'
        entry['reason']='' if entry['status']=='verified' else (facility['reason'] or 'reading still requires evidence')
        (applied if entry['status']=='verified' else pending).append(entry['id'])
    result['collection']['corrections']=dict(applied=sorted(applied),pending=sorted(pending),unmatched=sorted(set(corrections)-seen))
    return result
