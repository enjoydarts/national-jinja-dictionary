"""Pinned Microsoft IME WORDLIST input subset, generated from canonical data."""
import unicodedata
from njd.normalize import normalize_reading

HEADER=('!Microsoft IME Dictionary Tool','!Version:','!Format:WORDLIST')
PROFILE=dict(status='enabled',extension='txt',
    target='Microsoft IME User Dictionary Tool IMJPDCT.EXE 10.0.26100.9818, x64; OS build not measured',
    encoding='utf-16-le',bom=True,newline='\r\n',delimiter='\t',header=list(HEADER),
    columns=['reading','surface','pos'],pos='固有名詞',
    escape='no quoting; reject control, format and line/paragraph separator characters',
    max_reading_units=60,max_surface_units=60,length_count='UTF-16 code units, as checked by the pinned SetWordW implementation',
    max_rows=None,max_rows_note='total capacity and existing user dictionary occupancy not established; no unlimited-capacity claim',
    header_policy='parser-compatible first three native header lines; no invented Version value or personal export metadata',
    reference='https://support.microsoft.com/ja-jp/windows/hardware/input-devices/microsoft-japanese-ime',
    implementation_evidence='docs/MSIME_FORMAT_EVIDENCE.json',
    executable_sha256='56f33d04670ddc5e59a70c7f46c9222937a1d12f01bfefdc0ee2e7d5c9923333',
    pos_rationale='神社という特定施設の名称を、公式実装で入力可能な固有名詞（ID 0x76）へ対応づける。',
    actual_ime_import='not_tested')


def row_problem(row):
    if len(row)!=3:return 'expected three TAB fields'
    reading,surface,pos=row
    if not reading or not surface:return 'empty reading or surface'
    if pos!=PROFILE['pos']:return 'wrong POS for the Microsoft IME profile'
    if any(unicodedata.category(c) in ('Cc','Cf','Cs','Zl','Zp') for field in row for c in field):
        return 'control, format or separator character in TAB field'
    try:
        if normalize_reading(reading)!=reading:return 'reading must be full-width hiragana'
        if len(reading.encode('utf-16-le'))//2>60:return 'reading exceeds 60 UTF-16 code units'
        if len(surface.encode('utf-16-le'))//2>60:return 'surface exceeds 60 UTF-16 code units'
    except (UnicodeError,ValueError):return 'invalid Unicode or non-hiragana reading'
    return None


def encode_rows(rows):
    text='\r\n'.join(HEADER)+'\r\n'+''.join('\t'.join(row)+'\r\n' for row in rows)
    return b'\xff\xfe'+text.encode('utf-16-le',errors='strict')


def check_msime(content):
    if not content.startswith(b'\xff\xfe'):return [dict(reason='profile requires UTF-16LE with FF FE BOM')]
    try:text=content[2:].decode('utf-16-le',errors='strict')
    except UnicodeDecodeError:return [dict(reason='invalid UTF-16LE')]
    header='\r\n'.join(HEADER)+'\r\n'
    if not text.startswith(header):return [dict(reason='missing or noncanonical Microsoft IME WORDLIST header')]
    issues=[]
    if not text.endswith('\r\n') or '\r' in text.replace('\r\n','') or '\n' in text.replace('\r\n',''):
        issues.append(dict(reason='profile requires CRLF record endings'))
    seen=set();body=text[len(header):]
    for number,line in enumerate(body.removesuffix('\r\n').split('\r\n') if body else [],4):
        problem=row_problem(line.split('\t'))
        if problem:issues.append(dict(line=number,reason=problem))
        if line in seen:issues.append(dict(line=number,reason='duplicate dictionary row'))
        seen.add(line)
    return issues
