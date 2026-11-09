"""macOS 27 additional-dictionary CSV; separate from text replacement."""
import csv
import io
from njd.normalize import normalize_reading

PROFILE=dict(status='enabled',extension='txt',target='macOS 27.0.1 (26A434), JapaneseIM preferences 1.1 (261)',
    encoding='utf-8',bom=False,newline='\n',delimiter=',',header=None,
    columns=['reading','surface','pos'],pos='その他の固有名詞',
    escape='quote every field; double ASCII quotes; reject control characters',
    max_reading_units=32,max_surface_units=64,max_line_units=127,
    length_count='conservative UTF-16 code units, serialized line includes LF; not a claim about internal grapheme counting',
    max_rows=None,max_rows_note='not specified by the versioned guide; no unlimited-capacity claim',
    reference='https://support.apple.com/ja-jp/guide/japanese-input-method/jpim10226/6.3/mac/27',
    pos_reference='https://support.apple.com/ja-jp/guide/japanese-input-method/jpim10211/6.3/mac/27',
    implementation_probe='official installed TextFile parser: UTF-8/no BOM/LF, quoted commas/spaces/quotes, non-BMP and variant characters preserved',
    parser_executable_sha256='21ab1829feeb666d19b27a881b46cde4bc3a74f0a484b3f250e10c4eb54b1da0',
    parser_fixture_sha256='fc9ef8ab5d65df086eb82cb4618eb7ebabec27aa30afebc2ae48db568c4125f8',
    parser_fixture_rows=5,
    pos_rationale='神社施設の固有名。Apple公式品詞表にあるその他の固有名詞を使用。',
    actual_ime_import='not_tested')


def encode_row(row):
    stream=io.StringIO(newline='')
    csv.writer(stream,quoting=csv.QUOTE_ALL,lineterminator='\n').writerow(row)
    return stream.getvalue()


def row_problem(row):
    if len(row)!=3:return 'expected three CSV fields'
    reading,surface,pos=row
    if not reading or not surface:return 'empty reading or surface'
    if pos!=PROFILE['pos']:return 'wrong POS for the macOS profile'
    if any(ord(c)<32 or ord(c)==127 for field in row for c in field):return 'control character in CSV field'
    try:
        if normalize_reading(reading)!=reading:return 'reading must be full-width hiragana'
        reading_units=len(reading.encode('utf-16-le'))//2
        surface_units=len(surface.encode('utf-16-le'))//2
        line_units=len(encode_row(row).encode('utf-16-le'))//2
    except (UnicodeError,ValueError):return 'invalid Unicode or non-hiragana reading'
    if reading_units>32:return 'reading exceeds conservative 32 UTF-16 code-unit bound'
    if surface_units>64:return 'surface exceeds conservative 64 UTF-16 code-unit bound'
    if line_units>127:return 'escaped CSV line exceeds conservative 127 UTF-16 code-unit bound including LF'
    return None


def check_macos(content):
    try:text=content.decode('utf-8')
    except UnicodeDecodeError:return [dict(reason='invalid UTF-8')]
    issues=[]
    if content.startswith(b'\xef\xbb\xbf'):issues.append(dict(reason='profile emits no BOM'))
    if '\r' in text or (text and not text.endswith('\n')):issues.append(dict(reason='profile requires LF record endings'))
    try:rows=list(csv.reader(io.StringIO(text,newline=''),strict=True))
    except csv.Error:return issues+[dict(reason='invalid CSV quoting')]
    seen=set()
    for number,row in enumerate(rows,1):
        problem=row_problem(row)
        if problem:issues.append(dict(line=number,reason=problem))
        key=tuple(row)
        if key in seen:issues.append(dict(line=number,reason='duplicate dictionary row'))
        seen.add(key)
    if ''.join(encode_row(row) for row in rows)!=text:
        issues.append(dict(reason='profile requires canonical quoted CSV records'))
    return issues
