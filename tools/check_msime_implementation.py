"""Read-only guards for a manually reviewed official Microsoft IME implementation.

Requires the pinned EXE/PDB and LLVM objdump. Does not execute Microsoft code,
open user dictionaries, download files, or prove program semantics. Product
files and disassembly must remain outside the public repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import uuid

VERSION='10.0.26100.9818'
EXE_SHA='56f33d04670ddc5e59a70c7f46c9222937a1d12f01bfefdc0ee2e7d5c9923333'
PDB_SHA='9de229514368f4451377d4f4e03c5bd0fa3c6d6a648413c59d722c52f4c7aa35'
EXE_URL='https://msdl.microsoft.com/download/symbols/imjpdct.exe/F5BF7367ae000/imjpdct.exe'
PDB_URL='https://msdl.microsoft.com/download/symbols/imjpdct.pdb/FF86E931172E016353583CE5126E5D7C1/imjpdct.pdb'


def streams(raw):
    block_size,_,_,directory_size,_,map_block=struct.unpack_from('<6I',raw,32)
    count=(directory_size+block_size-1)//block_size
    blocks=struct.unpack_from('<'+'I'*count,raw,map_block*block_size)
    directory=b''.join(raw[b*block_size:(b+1)*block_size] for b in blocks)[:directory_size]
    count=struct.unpack_from('<I',directory)[0]
    sizes=struct.unpack_from('<'+'I'*count,directory,4);offset=4+4*count;result=[]
    for size in sizes:
        count=0 if size==0xffffffff else (size+block_size-1)//block_size
        blocks=struct.unpack_from('<'+'I'*count,directory,offset);offset+=count*4
        result.append(b''.join(raw[b*block_size:(b+1)*block_size] for b in blocks)[:size] if size!=0xffffffff else b'')
    return result


class ReviewedPE:
    def __init__(self,raw):
        self.raw=raw;pe=struct.unpack_from('<I',raw,0x3c)[0];optional=pe+24
        if raw[pe:pe+4]!=b'PE\0\0' or struct.unpack_from('<H',raw,pe+4)[0]!=0x8664:
            raise ValueError('reviewed x64 PE required')
        self.base=struct.unpack_from('<Q',raw,optional+24)[0]
        section_count=struct.unpack_from('<H',raw,pe+6)[0]
        optional_size=struct.unpack_from('<H',raw,pe+20)[0];self.sections=[]
        for index in range(section_count):
            _,_,rva,size,file_offset=struct.unpack_from('<8sIIII',raw,optional+optional_size+40*index)
            self.sections.append((rva,size,file_offset))

    def read(self,rva,size):
        for start,length,offset in self.sections:
            if start<=rva and rva+size<=start+length:return self.raw[offset+rva-start:offset+rva-start+size]
        raise ValueError('reviewed address outside file-backed PE sections')

    def string(self,rva):
        data=bytearray()
        while True:
            pair=self.read(rva+len(data),2)
            if pair==b'\0\0':return data.decode('utf-16-le')
            data.extend(pair)


def inspect(exe,pdb,objdump='objdump'):
    raw=exe.read_bytes();debug=pdb.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXE_SHA or hashlib.sha256(debug).hexdigest()!=PDB_SHA:
        raise ValueError('product/debug data differs from reviewed version; manual review required')
    pe=ReviewedPE(raw);debug_streams=streams(debug);info=debug_streams[1];dbi=debug_streams[3];rsds=raw.index(b'RSDS')
    # Public PDB postprocessing can advance InfoStream age without changing
    # DBI age. The latter is the age matched to the executable (LLVM D152189).
    if raw[rsds+4:rsds+20]!=info[12:28] or raw[rsds+20:rsds+24]!=dbi[8:12]:
        raise ValueError('debug GUID/age mismatch')
    version_offset=raw.index(b'\xbd\x04\xef\xfe')
    high,low=struct.unpack_from('<II',raw,version_offset+8)
    if (high>>16,high&65535,low>>16,low&65535)!=(10,0,26100,9818):raise ValueError('component version changed')
    # These reviewed RVAs are meaningful only for the exact hash above.
    checks=[
        ('CText::IsUnicodeText',0x40a68,0x40b24,['0xfeff']),
        ('CVdrMS::WriteHeader',0x42550,0x427f0,['0xfeff','0x2']),
        ('CVdrMS::GetFormatW',0x415d0,0x41830,['0x8','0x7']),
        ('CVdrMS::SetDataW',0x41bc0,0x41d50,['0x400','0x50']),
        ('CVdrMS::SetWordW',0x423b8,0x42550,['cmp\teax, 0x3c']),
        ('CVdrMS::GetLineDataW',0x418d0,0x41980,['0x21','0x9']),
        ('CVender::FGetsW',0x43504,0x435c4,['0xd','0xa','0x2']),
        ('PosStr2PosW',0x405cc,0x40680,['0x30','0xa1']),
        ('CVdrMS::WriteLineWord',0x43290,0x434ac,['0x14'])]
    for _,start,end,markers in checks:
        disassembly=subprocess.run([objdump,'-d','--x86-asm-syntax=intel','--no-show-raw-insn',
            f'--start-address={pe.base+start}',f'--stop-address={pe.base+end}',str(exe)],check=True,capture_output=True,text=True).stdout
        if any(marker not in disassembly for marker in markers):raise ValueError('reviewed structure marker missing')
    literal_checks={0x56888:'!Microsoft IME Dictionary Tool',0x568f0:'!Version:',0x568d8:'!Format:',
        0x56960:'WORDLIST',0x567a0:'%s\t%s\t%s',0x53c50:'\r\n',0x53c68:'\t\r\n'}
    for rva,want in literal_checks.items():
        if pe.string(rva)!=want:raise ValueError('reviewed literal differs')
    header=[]
    for index,want in enumerate([literal_checks[0x56888],'!Version:','!Format:']):
        kind,_,pointer,_=struct.unpack('<IIQQ',pe.read(0x64e30+24*index,24))
        if kind!=[1,4,2][index] or pe.string(pointer-pe.base)!=want:raise ValueError('header table changed')
        header.append(want+('WORDLIST' if kind==2 else ''))
    entry=pe.read(0x632c0,48);pos=struct.unpack_from('<I',entry)[0]
    pointer=struct.unpack_from('<Q',entry,16)[0];enabled=struct.unpack_from('<I',entry,44)[0]
    if pos!=0x76 or not enabled or pe.string(pointer-pe.base)!='固有名詞':raise ValueError('POS table changed')
    return dict(schema_version=1,checked_at='2026-11-11',product='Microsoft IME User Dictionary Tool',
        component='IMJPDCT.EXE',component_version=VERSION,architecture='x64',os_build='not_measured',
        executable_url=EXE_URL,executable_sha256=EXE_SHA,pdb_url=PDB_URL,pdb_sha256=PDB_SHA,
        pdb_guid=str(uuid.UUID(bytes_le=info[12:28])),pdb_dbi_age=struct.unpack_from('<I',dbi,8)[0],
        pdb_info_age=struct.unpack_from('<I',info,8)[0],
        method='manual static inspection of the pinned official EXE/PDB, with read-only identity, structural-marker and literal-table recheck',
        validation_scope='identity/structure guards only; not an automated proof of semantics or registration-engine acceptance',
        findings=dict(encoding='UTF-16LE',bom_hex='fffe',newline='CRLF',columns=['reading','surface','pos'],
            optional_comment=True,selected_header=header,native_header_items=7,
            header_scope='selected minimal parser-compatible first three native header lines; personal metadata omitted',
            pos=dict(label='固有名詞',id=pos),max_reading_utf16_units=60,max_surface_utf16_units=60,total_capacity='not_established'),
        reviewed_methods=[name for name,_,_,_ in checks],executed_product_parser=False,actual_ime_import='not_tested',
        product_files_redistributed=False,authenticode_validation='not_performed',
        acquisition_terms='https://learn.microsoft.com/en-us/legal/windows-sdk/microsoft-symbol-server-license-terms',
        official_sources=['https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/microsoft-public-symbols',
            'https://support.microsoft.com/ja-jp/windows/hardware/input-devices/microsoft-japanese-ime'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,required=True);parser.add_argument('--pdb',type=Path,required=True)
    parser.add_argument('--objdump',default='objdump',help='LLVM objdump executable')
    parser.add_argument('--report',type=Path);args=parser.parse_args()
    result=inspect(args.exe,args.pdb,args.objdump)
    encoded=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    if args.report:args.report.write_text(encoded,encoding='utf-8')
    print(encoded,end='')


if __name__=='__main__':main()
