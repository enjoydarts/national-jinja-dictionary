"""Direct ATOK text profiles: lossless Shift JIS and BOM-marked UTF-16BE.

Product import is tracked separately from offline format/implementation checks.
"""
import unicodedata
from njd.normalize import normalize_reading

HEADER='!!ATOK_TANGO_TEXT_HEADER_1'
PROFILE=dict(status='enabled',extension='txt',
    target='ATOK for Mac 36.0.2 (245128.3.0), Japanese (Shift JIS) text input setting',
    encoding='shift_jis',bom=False,newline='\r\n',delimiter='\t',header=HEADER,
    columns=['reading','surface','pos'],pos='固有地名',
    escape='no quoting; reject control, format and line/paragraph separator characters',
    max_reading_units=32,max_surface_units=100,max_rows=None,
    max_rows_note='not specified by the reviewed guide; no unlimited-capacity claim',
    length_count='conservative UTF-16 code units; no internal counting claim',
    encoding_policy='strict standard Shift JIS; require identity after Shift JIS and CP932 decoding; no replacement or vendor extensions',
    newline_policy='project chooses conventional CRLF text records; not a captured product export',
    bom_policy='no BOM for the project standard Shift JIS profile; not a Unicode export claim',
    reference='https://www.atok.com/other/support/howtouse/mac/dc/pgs/dc_word_file.htm',
    encoding_reference='https://www.atok.com/other/support/howtouse/mac/mn/pgs/mn_tool_d_com_encoding.htm',
    pos_reference='https://www.atok.com/other/support/howtouse/mac/shrd/shrd_hinsi_meisi.htm',
    pos_rationale='神社という場所の固有名を、公式品詞表の固有地名（5）へ対応づける。',
    actual_ime_import='not_tested')

UNICODE_PROFILE={**PROFILE,
    'target':'ATOK for Mac 36.0.2 (245128.3.0); DicUtility 36.0.0 (245010.75.0), arm64',
    'encoding':'utf-16-be','bom':True,
    'encoding_policy':'strict UTF-16BE with FE FF BOM; original Unicode code points preserved',
    'newline_policy':'CRLF as observed in the pinned official CUTTangoFile writeString implementation',
    'bom_policy':'FE FF as observed in the pinned official CUTTangoFile addUnicodeHeader implementation',
    'encoding_reference':'https://www.atok.com/other/support/howtouse/mac/mn/pgs/mn_tool_ut_out_word_out_d.htm',
    'implementation_evidence':'docs/ATOK_UNICODE_EVIDENCE.json',
    'executable_sha256':'325d04b0d757a8a1a66cbe4c5f156fe7032d698296e91e914290154de7376bb0'}


def row_problem(row,*,unicode=False):
    if len(row)!=3:return 'expected three TAB fields'
    reading,surface,pos=row
    if not reading or not surface:return 'empty reading or surface'
    if pos!=PROFILE['pos']:return 'wrong POS for the ATOK profile'
    if any(unicodedata.category(c) in ('Cc','Cf','Cs','Zl','Zp') for field in row for c in field):
        return 'control, format or separator character in TAB field'
    try:
        if normalize_reading(reading)!=reading or reading.startswith('ー'):
            return 'reading must be full-width hiragana and not start with a prolonged sound mark'
        if len(reading.encode('utf-16-le'))//2>32:return 'reading exceeds conservative 32 UTF-16 code-unit bound'
        if len(surface.encode('utf-16-le'))//2>100:return 'surface exceeds conservative 100 UTF-16 code-unit bound'
    except (UnicodeError,ValueError):return 'invalid Unicode or non-hiragana reading'
    if unicode:return None
    try:
        for field in row:
            raw=field.encode('shift_jis',errors='strict')
            if raw.decode('shift_jis')!=field or raw.decode('cp932')!=field:
                return 'Shift JIS mapping does not preserve the original Unicode characters'
    except UnicodeError:return 'not representable in the lossless standard Shift JIS subset'
    return None


def encode_rows(rows,*,unicode=False):
    text=HEADER+'\r\n'+''.join('\t'.join(row)+'\r\n' for row in rows)
    return b'\xfe\xff'+text.encode('utf-16-be',errors='strict') if unicode else text.encode('shift_jis',errors='strict')


def check_atok(content,*,unicode=False):
    if unicode and not content.startswith(b'\xfe\xff'):
        return [dict(reason='profile requires UTF-16BE with FE FF BOM')]
    try:text=(content[2:].decode('utf-16-be',errors='strict') if unicode else content.decode('shift_jis',errors='strict'))
    except UnicodeDecodeError:return [dict(reason='invalid UTF-16BE' if unicode else 'invalid standard Shift JIS')]
    if not text.startswith(HEADER+'\r\n'):return [dict(reason='missing ATOK header or CRLF header ending')]
    issues=[]
    if not text.endswith('\r\n') or '\r' in text.replace('\r\n','') or '\n' in text.replace('\r\n',''):
        issues.append(dict(reason='profile requires CRLF record endings'))
    seen=set()
    for number,line in enumerate(text[len(HEADER)+2:].removesuffix('\r\n').split('\r\n'),2):
        if line=='' and text==HEADER+'\r\n':break
        row=line.split('\t');problem=row_problem(row,unicode=unicode)
        if problem:issues.append(dict(line=number,reason=problem))
        if line in seen:issues.append(dict(line=number,reason='duplicate dictionary row'))
        seen.add(line)
    return issues
