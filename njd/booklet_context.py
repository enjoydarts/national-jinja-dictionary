"""Bind a numbered profile to an explicitly abbreviated address in one PDF."""
import re
from urllib.parse import urlsplit
from njd.document_context import _dated
from njd.locations import _hash, _plain


def booklet_context_address(ref, facility):
    """Return only a comparison value; preserve all printed and acquired text."""
    context = ref.get('booklet_address_context')
    if (not isinstance(context, dict)
        or context.get('kind') != 'same_pdf_numbered_profile_explicit_prefix'
        or ref.get('source_kind') != 'tourism_organization_booklet'
        or ref.get('reading_scope') != 'full_name'
        or any(k in ref for k in ('address_components', 'csv_address_context', 'document_address_context'))
        or ref.get('name_raw') != facility.get('listed_name')):
        return None
    for observation in (ref, context):
        if (any(not _plain(observation.get(k)) for k in ('url', 'page_hash', 'checked_at', 'locator'))
            or not _hash(observation['page_hash']) or not _dated(observation['checked_at'])):
            return None
    if any(context[k] != ref[k] for k in ('url', 'page_hash', 'checked_at')):
        return None
    try:
        url = urlsplit(ref['url'])
    except ValueError:
        return None
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
        or url.fragment or not url.path.lower().endswith('.pdf')):
        return None
    pages, profile_page, table_page, number, row_number = (
        ref.get('pdf_pages'), ref.get('source_page_index'), context.get('source_page_index'),
        ref.get('source_card_number'), context.get('record_number'))
    if (any(type(v) is not int for v in (pages, profile_page, table_page, number, row_number))
        or not 0 <= table_page < profile_page < pages or number < 1 or row_number != number):
        return None
    visual = ref.get('visual_review')
    if (not isinstance(visual, dict) or visual.get('method') != 'pdf_render_individual_review'
        or any(not _hash(visual.get(k)) for k in ('profile_page_image_sha256', 'table_page_image_sha256'))
        or context.get('individual_identity_review') != 'same_subject_no_unresolved_location_conflict'):
        return None
    fields = ('prefecture_raw', 'municipality_raw', 'town_raw', 'heading_raw',
              'prefix_declaration_raw', 'name_raw', 'address_raw')
    if any(not _plain(context.get(k)) for k in fields):
        return None
    prefecture, city, town = (context[k] for k in fields[:3])
    if (prefecture != facility.get('prefecture') or city != facility.get('municipality')
        or not re.fullmatch(r'[\u3400-\u9fff々ヶ]+町', town)
        or not re.fullmatch(re.escape(town)+r'（[1-9][0-9]*社）', context['heading_raw'])):
        return None
    prefix = prefecture+city+town
    if (context['prefix_declaration_raw'] != '「'+prefix+'」を省略'
        or context.get('prefix_excerpt') != context['heading_raw']+'\n'+context['prefix_declaration_raw']):
        return None
    name, reading, address = (ref.get(k) for k in ('name_raw', 'reading_raw', 'address_raw'))
    if (any(not _plain(v) for v in (name, reading, address))
        or not re.search(r'[0-9０-９]', address)
        or (context['name_raw'], context['address_raw']) != (name, address)):
        return None
    annotation = ref.get('profile_locality_annotation_raw')
    if not isinstance(annotation, str) or (annotation and (not _plain(annotation) or not address.startswith(annotation))):
        return None
    profile_name = name+('（'+annotation+'）' if annotation else '')
    if ref.get('profile_name_raw') != profile_name:
        return None
    profile_excerpt = reading+'\n'+profile_name+'\n神社番号 '+str(number)
    row_excerpt = str(number)+' / '+name+' / '+address
    if (context.get('profile_excerpt') != profile_excerpt or context.get('row_excerpt') != row_excerpt
        or ref.get('excerpt') != profile_excerpt+'\n'+row_excerpt):
        return None
    acquired = facility.get('address')
    if not isinstance(acquired, str) or acquired.removeprefix(prefecture) != city+town+address:
        return None
    return prefix+address
