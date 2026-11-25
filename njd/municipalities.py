"""Comparison-only municipality changes bound to inspected government material."""
from datetime import datetime
import re
import unicodedata
from njd.locations import _hash, _plain

# The displayed examples on pages 1-2 were extracted and visually inspected.
# These rules do not cover the Arita parcel/locality subdivisions on pages 3-10.
_SAGA_PDF='https://www.pref.saga.lg.jp/kiji00329259/3_29259_6_chouazamei.pdf'
_SAGA_PDF_HASH='19ef4a4d2ff1ece43a6e2bb8ef9822b1766f77367cf9528c5cfc47dcac100308'
_SAGA_RULES=(
    ('佐賀郡諸富町','佐賀市諸富町',1,'2005-10-01','大字諸富津','大字諸富津'),
    ('佐賀郡大和町','佐賀市大和町',1,'2005-10-01','大字尼寺','大字尼寺'),
    ('佐賀郡富士町','佐賀市富士町',1,'2005-10-01','大字古湯','大字古湯'),
    ('神埼郡三瀬村','佐賀市三瀬村',1,'2005-10-01','大字三瀬','三瀬'),
    ('佐賀郡川副町','佐賀市川副町',2,'2007-10-01','大字鹿江','大字鹿江'),
    ('佐賀郡東与賀町','佐賀市東与賀町',2,'2007-10-01','大字下古賀','大字下古賀'),
    ('佐賀郡久保田町','佐賀市久保田町',2,'2007-10-01','大字新田','大字新田'),
    ('小城郡小城町','小城市小城町',1,'2005-03-01','大字畑田','畑田'),
    ('神埼郡千代田町','神埼市千代田町',2,'2006-03-20','大字直鳥','直鳥'),
)

ISAHAYA_LOCALITY_PROOF = 'documented_isahaya_locality_change'
_POSTAL_LIST = 'https://www.post.japanpost.jp/cgi-zip/zipcode.php?addr=&city={}&cmp=1&mode=list&pref=42'
_ISAHAYA_LOCALITIES = {
    '諫早市高来町船津名': (
        '諫早市高来町船津', '北高来郡高来町', '船津名', '859-0105', '1423431',
        '7268addacd3cdc04caa3427c20cb54866f98c63b792cc931bfb63a926d6db8a5',
    ),
    '諫早市森山町大字森山本村名': (
        '諫早市森山町本村', '北高来郡森山町', '森山本村名', '854-0203', '1423411',
        '2a134ed6fb6dee34b1afc2831e3a5b93ee61ed28e52a372251debbecb8088834',
    ),
}


def _isahaya_address(raw, evidence):
    """Bind the acquired locality to one inspected postal change row."""
    parts = re.fullmatch(r'([^0-9]+)([0-9]+(?:(?:-|番地の?|番|の)[0-9]+)*(?:番地|番|号)?)', raw)
    if parts is None or parts[1] not in _ISAHAYA_LOCALITIES or not isinstance(evidence, dict):
        return None
    current, old_city, old_town, postcode, city_code, digest = _ISAHAYA_LOCALITIES[parts[1]]
    expected = dict(url=_POSTAL_LIST.format(city_code), page_hash=digest, source_publisher='日本郵便株式会社',
                    effective_date='2005-03-01', former_municipality_raw=old_city, former_locality_raw=old_town,
                    current_locality_raw=current, postal_code_raw=postcode)
    if any(evidence.get(key) != value for key, value in expected.items()) or not _plain(evidence.get('locator')):
        return None
    try:
        if datetime.fromisoformat(evidence.get('checked_at', '')).tzinfo is None:
            return None
    except (TypeError, ValueError):
        return None
    return '長崎県'+current+parts[2]


def municipal_comparison_address(ref,facility,entry):
    """Return an evidenced municipality or locality prefix for comparison.

    The caller must still compare the ENTIRE resulting address to the
    reference, including its original locality, parcel, branch and suffix.
    This helper neither verifies a reading nor authorizes a name change.
    """
    proof=ref.get('address_identity_proof')
    if not isinstance(proof, dict):return None
    kind = proof.get('kind')
    if kind == ISAHAYA_LOCALITY_PROOF:
        if (facility.get('prefecture_code'), facility.get('prefecture'), facility.get('municipality')) != ('42','長崎県','諫早市'):
            return None
    elif kind != 'documented_municipality_prefix_change' or (facility.get('prefecture_code'), facility.get('prefecture')) != ('41','佐賀県'):
        return None
    if (entry.get('facility_id')!=facility.get('id') or
        proof.get('facility_id')!=facility.get('id') or proof.get('entry_id')!=entry.get('id') or
        not _hash(proof.get('expected_source_hash')) or
        proof['expected_source_hash']!=entry.get('source_hash') or
        proof['expected_source_hash']!=facility.get('source_hash') or
        proof.get('listing_address_raw')!=facility.get('address') or
        proof.get('reference_address_raw')!=ref.get('address_raw') or
        proof.get('reference_url')!=ref.get('url') or
        not _hash(proof.get('reference_page_hash')) or
        proof['reference_page_hash']!=ref.get('page_hash')):return None
    def comparison(value):
        return re.sub(r'\s+','',unicodedata.normalize('NFKC',value))
    if (not _plain(ref.get('name_raw')) or not _plain(facility.get('listed_name')) or
        comparison(ref['name_raw'])!=comparison(facility['listed_name']) or
        not _plain(facility.get('address')) or not _plain(ref.get('address_raw'))):return None
    raw=comparison(facility['address']).removeprefix(facility['prefecture'])
    evidence=proof.get('change_reference')
    if kind == ISAHAYA_LOCALITY_PROOF:
        return _isahaya_address(raw, evidence)
    # A number in a locality such as 1丁目/第1区 is not a parcel. Require a
    # literal terminal lot/house number, retaining all original branch units.
    if not re.search(r'[0-9](?:番地|番|号)?$',raw):return None
    if (not isinstance(evidence,dict) or evidence.get('url')!=_SAGA_PDF or
        evidence.get('page_hash')!=_SAGA_PDF_HASH or evidence.get('source_publisher')!='佐賀県' or
        not _plain(evidence.get('locator')) or type(evidence.get('pdf_page')) is not int):return None
    for field in ('fetched_at','checked_at'):
        try:
            if datetime.fromisoformat(evidence.get(field,'')).tzinfo is None:return None
        except (TypeError,ValueError):return None
    for former,current,page,date,old_example,new_example in _SAGA_RULES:
        if not raw.startswith(former):continue
        if (evidence['pdf_page']!=page or evidence.get('effective_date')!=date or
            evidence.get('former_example_raw')!=former+old_example+'○○番地' or
            evidence.get('current_example_raw')!=current+new_example+'○○番地'):return None
        return '佐賀県'+current+raw[len(former):]
    return None
