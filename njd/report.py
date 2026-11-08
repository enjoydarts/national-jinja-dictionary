"""Collection and export counts without conflating facilities with dictionary rows."""
from collections import Counter
import copy
import unicodedata
from njd.validation import eligible, validate

PREFECTURES='北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'.split()

def subset(data,code):
    result=dict(data)
    result['collection']=dict(data['collection'])
    if 'sources' in result['collection']:
        result['collection']['sources']={k:v for k,v in data['collection']['sources'].items() if v['prefecture_code']==code}
        result['collection']['source_rows_observed']=sum(v.get('source_rows_observed',0) for v in result['collection']['sources'].values())
    result['facilities']=[f for f in data['facilities'] if f['prefecture_code']==code]
    ids={f['id'] for f in result['facilities']}
    result['entries']=[e for e in data['entries'] if e['facility_id'] in ids]
    result['collection']['output_scope']=code
    return result

def _counts(data):
    accepted=eligible(data)
    return dict(facilities=len(data['facilities']),verified_facilities=len({e['facility_id'] for e in accepted}),
        dictionary_rows=len({(e['reading'],e['surface'],e['semantic_type']) for e in accepted}),
        entry_status_counts=dict(sorted(Counter(e['status'] for e in data['entries']).items())))

def report(data,outputs=None):
    totals=_counts(data)
    totals['output_rows']={k:v.rows for k,v in (outputs or {}).items() if v.content is not None}
    return dict(totals=totals,prefectures=[dict(prefecture_code=f'{i:02}',prefecture=pref,
        collection_status='partial' if any(f['prefecture_code']==f'{i:02}' for f in data['facilities']) else 'not_collected',
        **_counts(subset(data,f'{i:02}'))) for i,pref in enumerate(PREFECTURES,1)],
        collection=collection_summary(data['collection']),validation_problems=validate(data),
        format_outputs={k:v.summary() for k,v in (outputs or {}).items()},
        counting_notes=['dictionary_rows uses neutral semantic_type; format POS deduplication is counted separately',
            'JSON/CSV rows count management entry records, including pending/excluded; not IME candidates',
            'observed source rows are not claimed prefectural shrine totals',
            'actual IME import not performed for any format'])

def samples(data,maximum=12,names=()):
    valid=eligible(data); counts=Counter(e['surface'] for e in valid)
    chosen=[]; categories={}
    def select(entry,category):
        if len(chosen)<maximum and entry['id'] not in {e['id'] for e in chosen}:
            chosen.append(entry); categories[entry['id']]=category
    for e in valid:
        if e['surface'] in names: select(e,'explicitly selected source name')
    for e in valid:
        if counts[e['surface']]>1: select(e,'same-name distinct facility')
        if sum(1 for x in chosen if categories[x['id']]=='same-name distinct facility')>=2: break
    for e in valid:
        if any(c in '國神﨑塚邊邉澤福髙' or unicodedata.name(c,'').startswith('CJK COMPATIBILITY IDEOGRAPH') for c in e['surface']):
            select(e,'variant glyph preserved')
    for e in sorted(valid,key=lambda e:(-len(e['surface']),e['surface'],e['id'])): select(e,'long name or additional source entry')
    result=dict(data);result['collection']=collection_summary(data['collection']); ids={e['facility_id'] for e in chosen}
    result['facilities']=[f for f in data['facilities'] if f['id'] in ids]
    result['entries']=chosen; result['collection']['sample_selection']=categories
    result['collection']['sample_missing_requested_names']=sorted(set(names)-{e['surface'] for e in chosen})
    result['collection']['output_scope']='import sample; actual IME import not tested'
    return result


def collection_summary(collection):
    """Reports need scope and source facts, not repeated identity registries."""
    result={k:v for k,v in collection.items() if k not in ('identity_history','pages')}
    if 'pages' in collection:result['source_page_count']=len(collection['pages'])
    if 'sources' in collection:
        result['sources']={k:collection_summary(v) for k,v in collection['sources'].items()}
    return result
