"""Select the documented glyph and the unchanged agency reading in Toyooka."""
from datetime import datetime

from njd.hyogo_profile_review import _numeric_address
from njd.hyogo_registry_window import MONTHLY_HASH
from njd.locations import _hash, _plain

KIND = 'hyogo_profile_registered_glyph'
_REASON = 'annotated official name requires review'
_CODE = '6322026'
_NAME = '●神社(舟偏に益)'
_REGISTERED_NAME = '艗神社'
_ADDRESS = '豊岡市森津629-2'
_REGISTERED_ADDRESS = '兵庫県豊岡市森津字奥中口629-2'
_KANA = 'ヘサキジンジャ'
_CORPORATION = '2140005012248'
_IMAGE = '00042294'
_PROFILE = f'https://www.hyogo-jinjacho.com/data/{_CODE}.html'
_NTA = 'https://www.houjin-bangou.nta.go.jp'
_DISPLAYED_NAME = '＿神社（外字が含まれています。）'


def glyph_review_problems(review, facility, entry, source):
    digest = entry.get('source_hash')
    original = dict(name_raw=_NAME, reading_raw=_KANA, address=_ADDRESS, listing_url=_PROFILE)
    if (any(facility.get(key) != value for key, value in dict(source_key='hyogo', prefecture_code='28',
            municipality='豊岡市', native_source_id=_CODE, name_raw=_NAME, listed_name=_NAME,
            address=_ADDRESS, map_address_raw=_ADDRESS, listing_url=_PROFILE, review_reason=_REASON).items())
            or entry.get('facility_id') != facility.get('id') or entry.get('reading_raw') != _KANA
            or entry.get('reading_display_raw') != _KANA or entry.get('printed_code_raw') != _CODE+'/兼務'
            or not _hash(digest) or facility.get('source_hash') != digest
            or any(row.get('identity_review_required') or row.get('source_conflicts')
                   or row.get('status') not in ('pending','verified') or row.get('reason') not in ('',_REASON)
                   for row in (facility, entry))
            or (source or {}).get('authority_status') in ('pending','unconfirmed')
            or review.get('confirmation') != 'source_review' or review.get('original') != original
            or review.get('facility_id') != facility.get('id') or review.get('expected_source_hash') != digest
            or not all(_plain(review.get(key)) for key in ('case_id','reason'))
            or any(review.get(key) for key in ('split','accepted_identity_differences','resolved_reading_conflicts'))):
        return ['glyph review differs from the acquired Toyooka profile or overrides another condition']
    outputs = [dict(surface=_REGISTERED_NAME, reading='へさきじんじゃ', reading_url=_PROFILE, basis='agency_selected')]
    if review.get('outputs') != outputs:
        return ['glyph review requires the literal registered name and unchanged agency kana']

    refs = review.get('references')
    if (not isinstance(refs,list) or len(refs) != 4
            or any(not isinstance(ref,dict) or not _plain(ref.get('evidence_role')) for ref in refs)):
        return ['glyph review requires four scoped reference records']
    roles = {ref['evidence_role']:ref for ref in refs}
    if set(roles) != {'agency_profile','registry','official_current','locality'}:
        return ['glyph review lacks the profile, archive, current individual record or locality']
    try:
        approved = datetime.fromisoformat(review['recorded_at'])
        for ref in refs:
            fetched = datetime.fromisoformat(ref['fetched_at'])
            checked = datetime.fromisoformat(ref['checked_at'])
            if (not all(date.tzinfo for date in (fetched,checked,approved)) or not fetched <= checked <= approved
                    or not _hash(ref.get('page_hash')) or not all(_plain(ref.get(k)) for k in ('title','locator'))
                    or not _plain(ref['excerpt'].replace('\n',' '))):
                raise ValueError()
    except (AttributeError, TypeError, ValueError, KeyError):
        return ['glyph review has incomplete or inconsistent observation dates and provenance']

    profile, registry, current, locality = (roles[key] for key in ('agency_profile','registry','official_current','locality'))
    raw = facility.get('address_raw')
    if (not isinstance(raw,str) or raw != '〒668-0006\n'+_ADDRESS
            or any(profile.get(k) != v for k,v in dict(url=_PROFILE, page_hash=facility.get('page_hash'),
                source_locator=facility.get('source_locator'), name_raw=_NAME, reading_raw=_KANA,
                printed_code_raw=_CODE+'/兼務', address_raw=raw, source_kind='agency').items())
            or not all(value in profile['excerpt'] for value in (_NAME,_KANA,_ADDRESS,_CODE+'/兼務'))):
        return ['glyph review profile caption, full kana or address changed']
    observations = facility.get('xml_occurrences')
    if (not isinstance(observations,list) or len(observations)!=1 or not isinstance(observations[0],dict)
            or any(observations[0].get(k)!=v for k,v in dict(name_raw=_NAME,address_raw=_ADDRESS,code_raw=_CODE).items())
            or not _hash(observations[0].get('page_hash'))):
        return ['glyph review requires one matching original map observation']
    fields = registry.get('source_fields')
    if (not isinstance(fields,dict) or any(fields.get(k)!=v for k,v in dict(name=_REGISTERED_NAME,
            furigana='', corporateNumber=_CORPORATION, prefectureCode='28', prefectureName='兵庫県',
            cityName='豊岡市', kind='399', nameImageId=_IMAGE, addressImageId='').items())
            or any(registry.get(k)!=v for k,v in dict(snapshot='20261030', csv_row=44268, page_hash=MONTHLY_HASH,
                zip_member='28_hyogo_all_20261030.csv', url=_NTA+'/download/zenken/index.html').items())
            or not isinstance(registry.get('address_raw'),str)
            or _numeric_address(registry['address_raw']) != _REGISTERED_ADDRESS
            or not all(value in registry['excerpt'] for value in (_REGISTERED_NAME,registry['address_raw']))):
        return ['glyph review archive does not match the documented corporation and whole parcel']
    from njd.corporate import image_review_problems
    if image_review_problems(registry):
        return ['glyph review lacks a bound inspection of the official glyph image']
    if (any(current.get(k)!=v for k,v in dict(url=_NTA+'/henkorireki-johoto.html?selHouzinNo='+_CORPORATION,
            name_raw=_DISPLAYED_NAME, corporate_number=_CORPORATION, image_id=_IMAGE, reading_raw='',
            address_raw=registry['address_raw']).items())
            or not all(value in current['excerpt'] for value in (_DISPLAYED_NAME, current['address_raw']))):
        return ['glyph review individual record differs from the archived corporation or whole parcel']
    if (any(locality.get(k)!=v for k,v in dict(municipality_code='282090',town_id='0272150',
            oaza_raw='森津',koaza_raw='奥中口', url='https://data.address-br.digital.go.jp/mt_town/mt_town_all.csv.zip').items())
            or not all(value in locality['excerpt'] for value in ('豊岡市','森津','奥中口'))):
        return ['glyph review lacks the official parent locality for the registered minor locality']
    return []
