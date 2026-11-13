"""Comparison-only locality binding to explicit columns of one CSV record."""
import re
import unicodedata
from urllib.parse import urlsplit
from njd.document_context import _dated, _parcel
from njd.locations import _hash, _plain


_COLUMNS = ('No', '神社名', 'カナ', '所在地', '小字')


def csv_context_address(ref, facility):
    """Return a comparison address without changing any acquired column."""
    context = ref.get('csv_address_context')
    if (not isinstance(context, dict) or context.get('kind') != 'same_csv_record_explicit_aza'
        or ref.get('source_kind') != 'university_hosted_community_research_csv'
        or ref.get('mime_type') != 'text/csv' or ref.get('reading_scope') != 'full_name'
        or 'address_components' in ref or 'document_address_context' in ref
        or ref.get('name_raw') != facility.get('listed_name')):
        return None
    for evidence in (ref, context):
        if (any(not _plain(evidence.get(k)) for k in ('url', 'page_hash', 'checked_at', 'locator', 'excerpt'))
            or not _hash(evidence['page_hash']) or not _dated(evidence['checked_at'])):
            return None
    if any(context[k] != ref[k] for k in ('url', 'page_hash', 'checked_at')):
        return None
    try:
        url = urlsplit(ref['url'])
    except ValueError:
        return None
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
        return None
    record = ref.get('csv_record_number')
    if type(record) is not int or record < 2 or type(context.get('csv_record_number')) is not int:
        return None
    if context['csv_record_number'] != record:
        return None
    fields = ref.get('source_fields')
    if (not isinstance(fields, dict) or set(fields) != set(_COLUMNS)
        or context.get('source_fields') != fields or any(not _plain(fields[k]) for k in _COLUMNS)):
        return None
    if (not re.fullmatch(r'[1-9][0-9]*', fields['No']) or context.get('row_id_raw') != fields['No']
        or fields['神社名'] != ref.get('name_raw') or fields['カナ'] != ref.get('reading_raw')
        or fields['所在地'] != ref.get('address_raw')):
        return None
    excerpt=' / '.join(k+'='+fields[k] for k in _COLUMNS)
    if any(evidence['excerpt'] != excerpt for evidence in (ref, context)):
        return None
    separator=context.get('comparison_separator')
    if separator not in ('', '字'):
        return None
    printed = _parcel(fields['所在地'])
    aza = unicodedata.normalize('NFKC', fields['小字'])
    if (not printed or not re.fullmatch(r'[\u3400-\u9fff々〆ヶぁ-ゖァ-ヺー]+', aza)
        or aza.startswith(('字', '小字'))):
        return None
    # 字 is an address-column separator. The locality and every numeric
    # component come from this same record; neither is guessed or discarded.
    return printed[0]+separator+aza+printed[1]
