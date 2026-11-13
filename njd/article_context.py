"""Compare literal article addresses under an explicit omission declaration."""
import re
from urllib.parse import urlsplit
from njd.document_context import _dated, _parcel
from njd.locations import _hash, _plain


def article_context_address(ref, facility):
    """Use only bound direct-body blocks; never rewrite printed evidence."""
    context = ref.get('article_address_context')
    if (not isinstance(context, dict) or context.get('kind') != 'same_article_explicit_omitted_municipality'
        or ref.get('source_kind') != 'independent_secondary_reference'
        or ref.get('mime_type') != 'text/html' or ref.get('reading_scope') != 'full_name'
        or ref.get('name_raw') != facility.get('listed_name')
        or any(k in ref for k in ('address_components', 'csv_address_context', 'document_address_context', 'booklet_address_context'))):
        return None
    for observation in (ref, context):
        if (any(not _plain(observation.get(k)) for k in ('url', 'page_hash', 'checked_at'))
            or not _hash(observation['page_hash']) or not _dated(observation['checked_at'])):
            return None
    if (any(context[k] != ref[k] for k in ('url', 'page_hash', 'checked_at'))
        or any(not _plain(o.get('locator')) for o in (ref, context))):
        return None
    try:
        url = urlsplit(ref['url'])
    except ValueError:
        return None
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
        return None
    scope, heading, address_index, count, scope_count = (context.get('scope_element_index'),
        ref.get('heading_element_index'), ref.get('address_element_index'),
        ref.get('body_elements'), context.get('body_elements'))
    ref_scope = ref.get('scope_element_index')
    if (any(type(v) is not int for v in (scope, heading, address_index, count, scope_count, ref_scope))
        or scope != ref_scope
        or not 0 <= scope < heading < address_index < count or address_index != heading+1 or count != scope_count
        or ref.get('heading_tag') != 'h2' or ref.get('address_tag') != 'p' or context.get('scope_tag') != 'p'
        or ref.get('body_locator') != '#mainEntity > div.clearfix' or context.get('body_locator') != ref['body_locator']
        or context.get('structure_kind') != 'direct_article_body_children'
        or context.get('individual_identity_review') != 'literal_heading_and_full_parcel_no_identity_hold'):
        return None
    prefecture, city = context.get('prefecture_raw'), context.get('municipality_raw')
    if (not _plain(prefecture) or not _plain(city)
        or prefecture != facility.get('prefecture') or city != facility.get('municipality')):
        return None
    prefix = prefecture+city
    declaration = context.get('declaration_raw')
    scope_text = context.get('scope_paragraph_raw')
    if (declaration not in ('※以下、'+prefix+'を省略', '（以下、'+prefix+'を省略）')
        or not isinstance(scope_text, str) or not _plain(scope_text.replace('>>', ''))
        or scope_text.count(declaration) != 1 or scope_text.count('を省略') != 1):
        return None
    name, reading, address = (ref.get(k) for k in ('name_raw', 'reading_raw', 'address_raw'))
    if any(not _plain(v) for v in (name, reading, address)):
        return None
    heading_text = name+'（'+reading+'）'
    paragraph = ref.get('address_paragraph_raw')
    if (ref.get('heading_raw') != heading_text or not isinstance(paragraph, str)
        or not re.fullmatch(re.escape(address)+r'[ \u3000]*>>[ \u3000]*Googleマップ', paragraph)
        or ref.get('excerpt') != heading_text+'\n'+paragraph):
        return None
    annotation = ref.get('address_kana_annotation')
    compared = address
    if annotation is not None:
        if not isinstance(annotation, dict):
            return None
        start, end, raw = (annotation.get(k) for k in ('start', 'end', 'raw'))
        if (type(start) is not int or type(end) is not int or not isinstance(raw, str)
            or not re.fullmatch(r'（[ぁ-ゖー]+）', raw) or not 0 < start < end < len(address)
            or address[start:end] != raw or address.count(raw) != 1):
            return None
        compared = address[:start]+address[end:]
    acquired = facility.get('address')
    if not isinstance(acquired, str):
        return None
    expected = _parcel(acquired.removeprefix(prefecture))
    actual = _parcel(city+compared)
    if expected is None or actual != expected:
        return None
    return prefix+compared
