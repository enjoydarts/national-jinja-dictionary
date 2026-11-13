"""Independently inspected NTA archive window used by Hyogo profile reviews.

Only this recorded window is supported. A new window requires source inspection;
no calendar/business-day inference or network access occurs during validation.
"""
from datetime import datetime

DAILY_FILES=[{'date': '20261102',
  'file_id': '28508',
  'rows': 2346,
  'page_hash': 'fed1d994034e65a53765c77e4f7106a3949c51f9cd88600ae9aa1e507e968485',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261104',
  'file_id': '28511',
  'rows': 2156,
  'page_hash': '3c65e01545ac0e137166cf06c6d01bd88aaaf85527d1d065374dbbee4e62976d',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261105',
  'file_id': '28514',
  'rows': 2183,
  'page_hash': '38ca2001e1e0912410cb8dfbf8b7f77d2b8a98d0901294721173e6dce0879f74',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261106',
  'file_id': '28517',
  'rows': 2617,
  'page_hash': '7472580e4a837671b200a986da17567a0f7917692b3f0cb62f13f5b1010238c9',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261109',
  'file_id': '28520',
  'rows': 2362,
  'page_hash': 'f2661f24d97564cf7b14a58389dfa1fa3f819a62c29f86b347a146b56a70765b',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261110',
  'file_id': '28523',
  'rows': 2642,
  'page_hash': '38034ac0c65af5af98a5c01025c134e854c986d583886074d8d81afb79fbfb64',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261111',
  'file_id': '28526',
  'rows': 2692,
  'page_hash': 'eb1976bceee98ace70fe15f074f861ca9f7d1e3ea2956477ee8e8f03df1dbddd',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'},
 {'date': '20261112',
  'file_id': '28529',
  'rows': 2180,
  'page_hash': '896ee14905fdfcd8098dd4bdb87fdc9bd02655facaf056c3d5358b984a60c1b9',
  'url': 'https://www.houjin-bangou.nta.go.jp/download/sabun/index.html'}]
MONTHLY_HASH='0fc15a6ca6db74e8b109c8ebda38ec154057ac1f7f2ff26c2c6609eb9ae1f6cd'


def observed_between(value,earliest,checked):
    try:
        fetched=datetime.fromisoformat(value);inspected=datetime.fromisoformat(checked)
        return fetched.tzinfo is not None and inspected.tzinfo is not None and fetched.date()>=datetime.strptime(earliest,'%Y%m%d').date() and fetched<=inspected
    except (TypeError,ValueError):return False


def registry_window_problems(reg):
    state=reg.get('registry_state_proof')
    if not isinstance(state,dict):return ['missing inspected Hyogo registry window']
    if (reg.get('snapshot')!='20261030' or reg.get('file_id')!='28443'
        or reg.get('member')!='28_hyogo_all_20261030.csv' or reg.get('page_hash')!=MONTHLY_HASH
        or state.get('as_of')!='20261112'
        or type(state.get('monthly_prefecture_rows')) is not int or state['monthly_prefecture_rows']!=206383
        or type(state.get('daily_rows')) is not int or state['daily_rows']!=19178
        or type(state.get('target_corporate_or_full_parcel_events')) is not int or state['target_corporate_or_full_parcel_events']!=0
        or not observed_between(reg.get('fetched_at'),'20261030',reg.get('checked_at'))):
        return ['Hyogo registry state differs from the independently inspected archive window']
    resources=state.get('daily_resources')
    if not isinstance(resources,list) or len(resources)!=len(DAILY_FILES):return ['missing complete Hyogo daily evidence window']
    for actual,expected in zip(resources,DAILY_FILES):
        if (not isinstance(actual,dict) or any(actual.get(k)!=v for k,v in expected.items())
            or type(actual.get('rows')) is not int
            or not observed_between(actual.get('fetched_at'),expected['date'],reg.get('checked_at'))):
            return ['Hyogo daily evidence differs from inspected dates, archives, counts or timestamps']
    return []
