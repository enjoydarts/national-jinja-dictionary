"""Offline binding of a printed locality to scope in the same document."""
import re
from datetime import datetime
from urllib.parse import urlsplit
from njd.locations import _hash, _plain
from njd.normalize import compare_address_units


def _dated(value):
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except (TypeError, ValueError):
        return False


def _parcel(value):
    """Keep literal locality; compare only the following numeric units."""
    if not isinstance(value, str):
        return None
    value = re.sub(r'[ \u3000]', '', value)
    match = re.fullmatch(r'([^0-9０-９]+)([0-9０-９][0-9０-９番地号の丁目\-]*)', value)
    if not match:
        return None
    return match[1], compare_address_units(match[2])


def document_context_address(ref, facility):
    """Return a comparison address; raw evidence is never rewritten."""
    context = ref.get('address_context')
    if not isinstance(context, dict) or context.get('kind') != 'same_document_explicit_municipality':
        return None
    if (ref.get('source_kind') != 'municipality_hosted_citizen_university_report'
        or ref.get('reading_scope') != 'full_name' or ref.get('address_components') is not None
        or ref.get('name_raw') != facility.get('listed_name')):
        return None
    fields = ('url', 'page_hash', 'checked_at', 'locator', 'table_heading_raw', 'excerpt')
    if any(not _plain(r.get(k)) for r in (ref, context) for k in fields):
        return None
    if any(not _plain(context.get(k)) for k in ('table_heading_locator', 'table_heading_excerpt')):
        return None
    try:
        url = urlsplit(ref['url'])
    except ValueError:
        return None
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
        or url.fragment or not url.path.lower().endswith('.pdf')
        or context['url'] != ref['url'] or context['page_hash'] != ref['page_hash']
        or not _hash(ref['page_hash']) or not all(_dated(r['checked_at']) for r in (ref, context))):
        return None
    pages, page, scope_page = (ref.get('pdf_pages'), ref.get('source_page_index'), context.get('source_page_index'))
    card = ref.get('source_card_number')
    heading_page = context.get('table_heading_page_index')
    if (any(type(v) is not int for v in (pages, page, scope_page, heading_page, card, context.get('record_number')))
        or not 0 <= scope_page < heading_page <= page < pages or card < 1 or context['record_number'] != card
        or context['table_heading_raw'] != ref['table_heading_raw']
        or context['table_heading_raw'] not in context['table_heading_excerpt']):
        return None
    city = context.get('municipality_raw')
    if (not _plain(city) or city != facility.get('municipality')
        or context.get('scope_raw') != city+'の神社'
        or context['scope_raw'] not in context['excerpt']):
        return None
    if any(not _plain(ref.get(k)) or ref[k] not in ref['excerpt']
           for k in ('name_raw', 'reading_raw', 'address_raw')):
        return None
    address = facility.get('address')
    if not isinstance(address, str):
        return None
    address = address.removeprefix(facility.get('prefecture', ''))
    if not address.startswith(city):
        return None
    printed = _parcel(ref['address_raw'])
    if not printed or printed != _parcel(address[len(city):]):
        return None
    return city+ref['address_raw']
