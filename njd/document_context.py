"""Offline binding of a printed locality to scope in the same document."""
import re
from datetime import datetime
from urllib.parse import urlsplit
from njd.locations import _hash, _plain


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
    number = match[2].translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    number = re.sub(r'(?<=\d)(?:丁目|番(?:地)?(?:の)?|の)(?=\d)', '-', number)
    number = re.sub(r'(?<=\d)(?:番地|番|号)$', '', number)
    if not re.fullmatch(r'[0-9]+(?:-[0-9]+)*', number):
        return None
    return match[1], number


def document_context_address(ref, facility):
    """Return a comparison address; raw evidence is never rewritten."""
    context = ref.get('document_address_context')
    if not isinstance(context, dict):
        return None
    if context.get('kind') == 'same_pdf_profile_locality_and_parcel':
        return _profile_address(ref, context, facility)
    if context.get('kind') != 'same_document_explicit_municipality':
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


def _profile_address(ref, context, facility):
    """Bind the locality sentence and parcel label within one printed profile."""
    if (ref.get('source_kind') != 'local_community_field_survey'
        or ref.get('reading_scope') != 'full_name'
        or ref.get('name_raw') != facility.get('listed_name')
        or any(k in ref for k in ('address_components', 'article_address_context',
                                  'booklet_address_context', 'csv_address_context'))):
        return None
    if any(not _plain(r.get(k)) for r in (ref, context)
           for k in ('url', 'page_hash', 'checked_at', 'locator', 'excerpt')):
        return None
    if (any(context[k] != ref[k] for k in ('url', 'page_hash', 'checked_at'))
        or not _hash(ref['page_hash']) or not _dated(ref['checked_at'])):
        return None
    try:
        url = urlsplit(ref['url'])
    except ValueError:
        return None
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
        or url.fragment or not url.path.lower().endswith('.pdf')):
        return None
    pages, page, scope_page, record = (ref.get('pdf_pages'), ref.get('source_page_index'),
                                      context.get('source_page_index'), ref.get('source_card_number'))
    if (any(type(v) is not int for v in (pages, page, scope_page, record, context.get('record_number')))
        or not 0 <= scope_page < page < pages or record < 1 or context['record_number'] != record):
        return None
    review = ref.get('visual_review')
    if not isinstance(review, dict) or not _hash(review.get('image_sha256')):
        return None
    city, scope, locality = (context.get(k) for k in ('municipality_raw', 'scope_raw', 'locality_raw'))
    if (any(not _plain(v) for v in (city, scope, locality)) or city != facility.get('municipality')
        or not re.fullmatch(re.escape(city)+r'[^\d\s]+地域文化財の現況', scope)
        or scope not in context['excerpt']):
        return None
    town = re.fullmatch(r'大字([^字\d\s]+)(字[^字\d\s]+)', locality)
    name, reading, parcel = (ref.get(k) for k in ('name_raw', 'reading_raw', 'address_raw'))
    if (not town or any(not _plain(v) or v not in ref['excerpt'] for v in (name, reading, parcel))
        or context.get('locality_excerpt') != locality+'にあり'
        or context['locality_excerpt'] not in ref['excerpt']
        or context.get('parcel_label_raw') != '所在地' or '所在地 '+parcel not in ref['excerpt']):
        return None
    acquired = facility.get('address')
    if not isinstance(acquired, str):
        return None
    acquired = acquired.removeprefix(facility.get('prefecture', ''))
    printed = _parcel(parcel)
    if (not acquired.startswith(city) or not printed or printed[0] != town[2]
        or _parcel(acquired[len(city):]) != (town[1]+town[2], printed[1])):
        return None
    return city+town[1]+parcel
