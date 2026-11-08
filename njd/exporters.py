"""Direct canonical-data exporters. Unsupported specs never produce guessed files."""
from dataclasses import dataclass, field
import csv
import io
import json
from njd.storage import json_bytes
from njd.validation import eligible, validate

MOZC_COMMIT='d918f30063999d4ca250f76ced8b92169a0e0b25'
FORMATS={
    'mozc':dict(status='enabled',extension='txt',encoding='utf-8',bom=False,
        newline='\n',delimiter='\t',header=None,pos='固有名詞',
        columns=['reading','surface','pos'],escape='reject TAB CR LF',
        max_reading_bytes=300,max_surface_bytes=300,max_rows=1_000_000,
        reference=f'https://github.com/google/mozc/tree/{MOZC_COMMIT}'),
    'json':dict(status='enabled',extension='json',encoding='utf-8',bom=False,newline='\n'),
    'csv':dict(status='enabled',extension='csv',encoding='utf-8',bom=False,newline='\n',
        delimiter=',',escape='RFC4180 double quotes via csv.writer; LF records'),
    'atok':dict(status='blocked',reason='current version, Unicode encoding/BOM, newline and escaping not confirmed'),
    'google':dict(status='blocked',reason='released Google Japanese Input import profile not confirmed; Mozc compatibility not assumed'),
    'msime':dict(status='blocked',reason='official bulk import syntax, encoding and target version not confirmed'),
    'macos':dict(status='blocked',reason='additional-dictionary CSV encoding/BOM and pinned macOS version not confirmed'),
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
    if name!='mozc': raise ValueError('exporter unavailable')
    accepted=eligible(data); accepted_ids={e['id'] for e in accepted}
    problems=validate(data); reasons={}
    for p in problems: reasons.setdefault(p['id'],[]).append(p['reason'])
    rejected=[]; lines=set(); duplicate_count=0
    for e in data['entries']:
        if e['id'] not in accepted_ids:
            why=e.get('reason') or '; '.join(reasons.get(e['id'],[]) + reasons.get(e['facility_id'],[])) or 'entry or facility not eligible'
            rejected.append(dict(entry_id=e['id'],facility_id=e['facility_id'],reason=why)); continue
        reading,surface=e['reading'],e['surface']
        if len(reading.encode('utf-8'))>300 or len(surface.encode('utf-8'))>300:
            rejected.append(dict(entry_id=e['id'],facility_id=e['facility_id'],reason='reading or surface exceeds 300 UTF-8 bytes')); continue
        line=(reading,surface,profile['pos'])
        if line in lines: duplicate_count+=1
        else: lines.add(line)
    if len(lines)>profile['max_rows']:
        return Output(None,status='blocked',reason='dictionary exceeds 1000000 rows; split required',exclusions=rejected)
    content=''.join('\t'.join(line)+'\n' for line in sorted(lines)).encode('utf-8')
    checks=check_mozc(content)
    if checks: raise ValueError('generated Mozc failed format checks: '+str(checks))
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
