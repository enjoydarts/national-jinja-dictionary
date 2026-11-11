"""Direct canonical-data exporters. Unsupported specs never produce guessed files."""
from dataclasses import dataclass, field
import csv
import io
import json
from njd.storage import json_bytes
from njd.validation import eligible, validate
from njd.macos import PROFILE as MACOS_PROFILE, encode_row as encode_macos_row, row_problem as macos_row_problem, check_macos
from njd.atok import PROFILE as ATOK_PROFILE, UNICODE_PROFILE as ATOK_UNICODE_PROFILE, encode_rows as encode_atok_rows, row_problem as atok_row_problem, check_atok
from njd.msime import PROFILE as MSIME_PROFILE, encode_rows as encode_msime_rows, row_problem as msime_row_problem, check_msime

MOZC_COMMIT='d918f30063999d4ca250f76ced8b92169a0e0b25'
MOZC_PROFILE=dict(status='enabled',extension='txt',encoding='utf-8',bom=False,
        newline='\n',delimiter='\t',header=None,pos='固有名詞',
        columns=['reading','surface','pos'],escape='reject TAB CR LF',
        max_reading_bytes=300,max_surface_bytes=300,max_rows=1_000_000,
        reference=f'https://github.com/google/mozc/tree/{MOZC_COMMIT}')
FORMATS={
    'mozc':MOZC_PROFILE,
    'json':dict(status='enabled',extension='json',encoding='utf-8',bom=False,newline='\n'),
    'csv':dict(status='enabled',extension='csv',encoding='utf-8',bom=False,newline='\n',
        delimiter=',',escape='RFC4180 double quotes via csv.writer; LF records'),
    'atok':ATOK_PROFILE,
    'atok_unicode':ATOK_UNICODE_PROFILE,
    'google':{**MOZC_PROFILE,
        'target':'Google Japanese Input for macOS 3.34.6260.1, DictionaryTool arm64',
        'reference':'https://www.google.co.jp/ime/',
        'implementation_evidence':'docs/GOOGLE_FORMAT_EVIDENCE.json',
        'executable_sha256':'e460cc3c28b67aa571ee6cf24d5fbab7391bfb3b7303eef38e975d0568e552c5',
        'compatibility_scope':'confirmed shared UTF-8 three-column TSV/POS/300-byte bounds in pinned product implementation; not full product equivalence',
        'actual_ime_import':'not_tested'},
    'msime':MSIME_PROFILE,
    'macos':MACOS_PROFILE,
}

@dataclass
class Output:
    content: bytes | None
    rows: int=0
    status: str='generated'
    reason: str=''
    exclusions: list[dict]=field(default_factory=list)
    deduplicated: int=0
    validation: list[dict]=field(default_factory=list)
    def summary(self):
        return dict(rows=self.rows,status=self.status,reason=self.reason,
            exclusions=self.exclusions,deduplicated=self.deduplicated,validation=self.validation,
            actual_ime_import='not_tested')

def render(data: dict, name: str) -> Output:
    profile=FORMATS[name]
    if profile['status']=='blocked': return Output(None,status='blocked',reason=profile['reason'])
    if any(p['kind']=='global' for p in validate(data)):
        return Output(None,status='blocked',reason='invalid canonical data structure',validation=validate(data))
    if name=='json': return Output(json_bytes(data),rows=len(data['entries']))
    if name=='csv':
        fmap={f['id']:f for f in data['facilities']}; records=[]
        for entry in data['entries']:
            row={'facility_'+k:v for k,v in fmap.get(entry['facility_id'],{}).items()}
            row.update({'entry_'+k:v for k,v in entry.items()})
            records.append(row)
        fields=sorted({k for r in records for k in r})
        stream=io.StringIO(newline=''); writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
        writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in records)
        return Output(stream.getvalue().encode('utf-8'),rows=len(records))
    if name not in ('mozc','google','macos','atok','atok_unicode','msime'): raise ValueError('exporter unavailable')
    accepted=eligible(data); accepted_ids={e['id'] for e in accepted}
    problems=validate(data); reasons={}
    for p in problems: reasons.setdefault(p['id'],[]).append(p['reason'])
    rejected=[]; lines=set(); duplicate_count=0
    for e in data['entries']:
        if e['id'] not in accepted_ids:
            why=e.get('reason') or '; '.join(reasons.get(e['id'],[]) + reasons.get(e['facility_id'],[])) or 'entry or facility not eligible'
            rejected.append(dict(entry_id=e['id'],facility_id=e['facility_id'],reason=why)); continue
        reading,surface=e['reading'],e['surface']
        line=(reading,surface,profile['pos'])
        if name=='macos':problem=macos_row_problem(line)
        elif name in ('atok','atok_unicode'):problem=atok_row_problem(line,unicode=name=='atok_unicode')
        elif name=='msime':problem=msime_row_problem(line)
        else:problem='reading or surface exceeds 300 UTF-8 bytes' if max(len(reading.encode('utf-8')),len(surface.encode('utf-8')))>300 else None
        if problem:
            rejected.append(dict(entry_id=e['id'],facility_id=e['facility_id'],reason=problem));continue
        if line in lines: duplicate_count+=1
        else: lines.add(line)
    if profile.get('max_rows') is not None and len(lines)>profile['max_rows']:
        return Output(None,status='blocked',reason='dictionary exceeds 1000000 rows; split required',exclusions=rejected)
    if name=='msime':
        content=encode_msime_rows(sorted(lines));checks=check_msime(content)
    elif name in ('atok','atok_unicode'):
        content=encode_atok_rows(sorted(lines),unicode=name=='atok_unicode');checks=check_atok(content,unicode=name=='atok_unicode')
    else:
        content=''.join(encode_macos_row(line) if name=='macos' else '\t'.join(line)+'\n' for line in sorted(lines)).encode('utf-8')
        checks=check_macos(content) if name=='macos' else check_mozc(content)
    if checks: raise ValueError('generated '+name+' failed format checks: '+str(checks))
    return Output(content,rows=len(lines),exclusions=rejected,deduplicated=duplicate_count,validation=checks)

def check_mozc(content: bytes) -> list[dict]:
    issues=[]
    try: text=content.decode('utf-8')
    except UnicodeDecodeError: return [dict(reason='invalid UTF-8')]
    if content.startswith(b'\xef\xbb\xbf'): issues.append(dict(reason='profile emits no BOM'))
    if '\r' in text or (text and not text.endswith('\n')): issues.append(dict(reason='profile requires LF record endings'))
    seen=set()
    for n,line in enumerate(text.splitlines(),1):
        fields=line.split('\t')
        if len(fields)!=3: issues.append(dict(line=n,reason='expected three fields')); continue
        reading,surface,pos=fields
        if pos!='固有名詞': issues.append(dict(line=n,reason='wrong POS'))
        if not reading or not surface or max(len(reading.encode()),len(surface.encode()))>300:
            issues.append(dict(line=n,reason='empty or overlong field'))
        if line in seen: issues.append(dict(line=n,reason='duplicate dictionary row'))
        seen.add(line)
    return issues
