"""Read-only identity/structure checks for two manually reviewed official binaries.

No IME is launched and no dictionary or preferences are opened. This guards the
identity and specific markers of the reviewed implementation; it is not a
general disassembler verifier, executed parser test, or actual import test.
Only metadata and independent findings are output, never product code.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import struct
import subprocess

ATOK=Path('/Library/Application Support/JustSystems/ATOK36/Support/ATOK DicUtility.app/Contents/MacOS/ATOK DicUtility')
ATOK_SHA='325d04b0d757a8a1a66cbe4c5f156fe7032d698296e91e914290154de7376bb0'
GOOGLE_SHA='e460cc3c28b67aa571ee6cf24d5fbab7391bfb3b7303eef38e975d0568e552c5'


def method(disassembly,name):
    start=disassembly.index(name+':\n')+len(name)+2
    end=re.search(r'^\S[^\n]*:\n',disassembly[start:],re.M)
    return disassembly[start:start+end.start()] if end else disassembly[start:]


def require(text,*markers):
    if any(marker not in text for marker in markers):
        raise ValueError('reviewed implementation markers changed; manual review required')


def product_pos(raw):
    # Read only the reviewed arm64 image's POS-name table. Chained pointers in
    # this exact image store image-relative addresses in the low 36 bits.
    if raw[:4]!=b'\xca\xfe\xba\xbe':raise ValueError('expected reviewed universal Mach-O')
    for index in range(struct.unpack_from('>I',raw,4)[0]):
        cpu,_,offset,size,_=struct.unpack_from('>IIIII',raw,8+20*index)
        if cpu==0x100000c:
            raw=raw[offset:offset+size];break
    else:raise ValueError('arm64 slice unavailable')
    segments=[];offset=32
    for _ in range(struct.unpack_from('<I',raw,16)[0]):
        command,size=struct.unpack_from('<II',raw,offset)
        if command==0x19:
            vm,_,file_offset,file_size=struct.unpack_from('<QQQQ',raw,offset+24)
            segments.append((vm,file_offset,file_size))
        offset+=size
    def read(address,size):
        for vm,file_offset,file_size in segments:
            if vm<=address and address+size<=vm+file_size:
                return raw[file_offset+address-vm:file_offset+address-vm+size]
        raise ValueError('POS table address outside reviewed file-backed segments')
    pointer,length,_=struct.unpack('<QQQ',read(0x1001b3598+24*4,24))
    address=pointer&((1<<36)-1)
    if address<0x100000000:address+=0x100000000
    if length!=12 or read(address,length).decode('utf-8')!='固有名詞':
        raise ValueError('reviewed PROPER_NOUN label changed')
    return dict(label='固有名詞',enum_value=4)


def inspect(binary,kind):
    raw=binary.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=(ATOK_SHA if kind=='atok' else GOOGLE_SHA):
        raise ValueError('binary differs from reviewed product; manual review required')
    text=subprocess.run(['otool','-arch','arm64','-tvV',str(binary)],check=True,capture_output=True,text=True).stdout
    result=dict(schema_version=1,checked_at='2026-11-11',architecture='arm64',executable_sha256=sha,
        method='manual static inspection of the pinned official implementation, with read-only identity and structural-marker recheck',
        validation_scope='identity/structure guards only; not an automated proof of program semantics',
        actual_ime_import='not_tested',executed_product_parser=False,product_files_redistributed=False)
    if kind=='atok':
        bom=method(text,'-[CUTTangoFile addUnicodeHeader]')
        require(bom,'#0xfffe','strh','_FSWriteFork','#0x2')
        writer=method(text,'-[CUTTangoFile writeString:]')
        require(writer,'getCharacters:','rev\tw10','_FSWriteFork','#0xd','#0xa, lsl #16','#0x4')
        detector=method(text,'-[CUTTangoFile isUnicodeText]')
        require(detector,'#0xfe','#0xff','_FSReadFork')
        reader=method(text,'-[CUTTangoFile readString:maxLen:]')
        require(reader,'rev\tw10','stringWithCharacters:length:','#0xa','#0xd')
        result.update(product='ATOK for Mac 36.0.2 (245128.3.0)',component='DicUtility 36.0.0 (245010.75.0)',
            findings=dict(unicode_export_encoding='UTF-16BE',unicode_export_bom_hex='feff',newline='CRLF',
                input_bom_recognition=['feff','fffe'],unicode_string_source='NSString UTF-16 code units'),
            reviewed_methods=['CUTTangoFile addUnicodeHeader','CUTTangoFile writeString:',
                'CUTTangoFile isUnicodeText','CUTTangoFile readString:maxLen:'],
            official_sources=['https://www.atok.com/other/support/howtouse/mac/dc/pgs/dc_word_file.htm',
                'https://www.atok.com/other/support/howtouse/mac/mn/pgs/mn_tool_ut_out_word_out_d.htm'])
    else:
        iterator=method(text,'__ZN4mozc15user_dictionary17TextInputIterator4NextEPNS0_8RawEntryE')
        require(iterator,'#0x9','cmp\tx8, #0x3','cmp\tx8, #0x4','ChopReturns')
        validator=method(text,'__ZN4mozc15user_dictionary13ValidateEntryERKNS0_20UserDictionary_EntryE')
        require(validator,'#0x12d','IsValidUtf8')
        exporter=method(text,'__ZNK4mozc21UserDictionaryStorage16ExportDictionaryEyNSt3__117basic_string_viewIcNS1_11char_traitsIcEEEE')
        require(exporter,'literal pool for: "\\t"','GetStringPosType','#0xa')
        full=method(text,'__ZN4mozc21UserDictionaryStorage16IsDictionaryFullERKNS_15user_dictionary14UserDictionaryE')
        require(full,'#0x423f','#0xf, lsl #16','cset\tw0, hi')
        lines=method(text,'__ZN4mozc3gui12_GLOBAL__N_125MultiByteTextLineIterator4NextEPNSt3__112basic_stringIcNS3_11char_traitsIcEENS3_9allocatorIcEEEE')
        require(lines,'#0xa','#0xd','StripUtf8Bom','ChopReturns')
        result.update(product='Google Japanese Input for macOS 3.34.6260.1',component='DictionaryTool',
            findings=dict(input='UTF-8 TAB-separated reading/surface/POS, optional fourth comment field',
                export='UTF-8 TAB-separated fields, no BOM/header, LF records',
                shared_output_subset='three fields, comment omitted, LF, no BOM',pos=product_pos(raw),
                max_field_utf8_bytes=300,max_dictionary_rows=1000000),
            reviewed_methods=['TextInputIterator::Next','MultiByteTextLineIterator::Next','ValidateEntry',
                'UserDictionaryStorage::ExportDictionary','UserDictionaryStorage::IsDictionaryFull','UserPos::GetStringPosType'],
            official_sources=['https://www.google.co.jp/ime/','https://support.google.com/ime/japanese/answer/166765?hl=ja'])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--atok',action='store_true')
    choice.add_argument('--google-binary',type=Path,help='DictionaryTool from the reviewed official macOS package')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if platform.system()!='Darwin':raise SystemExit('macOS and Apple otool required')
    result=inspect(ATOK if args.atok else args.google_binary,'atok' if args.atok else 'google')
    encoded=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    if args.report:args.report.write_text(encoded,encoding='utf-8')
    print(encoded,end='')


if __name__=='__main__':main()
