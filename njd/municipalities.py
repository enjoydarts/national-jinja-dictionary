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


def municipal_comparison_address(ref,facility,entry):
    """Return an evidenced prefix substitution; never change an acquired field.

    The caller must still compare the ENTIRE resulting address to the
    reference, including its original locality, parcel, branch and suffix.
    This helper neither verifies a reading nor authorizes a name change.
    """
    proof=ref.get('address_identity_proof')
    if not isinstance(proof,dict) or proof.get('kind')!='documented_municipality_prefix_change':return None
    if facility.get('prefecture_code')!='41' or facility.get('prefecture')!='佐賀県':return None
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
    raw=comparison(facility['address']).removeprefix('佐賀県')
    # A number in a locality such as 1丁目/第1区 is not a parcel. Require a
    # literal terminal lot/house number, retaining all original branch units.
    if not re.search(r'[0-9](?:番地|番|号)?$',raw):return None
    evidence=proof.get('change_reference')
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
