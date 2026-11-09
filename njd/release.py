"""Build release assets offline from the canonical data of a specific commit."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import zipfile
from njd.__main__ import build_outputs, _review_lists
from njd.exporters import FORMATS
from njd.corrections import apply_corrections
from njd.nationwide import merge_collections, ensure_public_metadata
from njd.storage import apply_decisions, json_bytes, load_dataset, write_json
from njd.validation import blocking_problems


def _input_hashes(data_dir):
    paths=sorted((data_dir/'sources').glob('*.json'))
    paths += [data_dir/name for name in ('manifest.json','decisions.json','identities.json','corrections.json','source_catalog.json') if (data_dir/name).exists()]
    return {str(p.relative_to(data_dir)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def create_release(data_dir,output_dir,version,source_commit):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,80}',version): raise ValueError('unsafe release version')
    if not re.fullmatch(r'[0-9a-f]{40,64}|unknown',source_commit): raise ValueError('invalid source commit')
    data_dir=Path(data_dir);output_dir=Path(output_dir)
    initial_inputs=_input_hashes(data_dir)
    data=merge_collections(data_dir)
    corrections=data_dir/'corrections.json'
    if corrections.exists():data=apply_corrections(data,load_dataset(corrections))
    decisions=data_dir/'decisions.json'
    if decisions.exists() and load_dataset(decisions):data=apply_decisions(data,load_dataset(decisions))
    ensure_public_metadata(data)
    problems=blocking_problems(data)
    if problems:raise ValueError('canonical data cannot be released: '+str(problems[:5]))
    destination=output_dir/'dictionaries'
    report,has_blocked=build_outputs(data,data_dir,list(FORMATS),sample_names=('倭文神社','大國神社'),output_dir=destination)
    _review_lists(data,destination)
    for name in ('manifest.json','corrections.json','source_catalog.json'):
        path=data_dir/name
        if path.exists():
            value=load_dataset(path);ensure_public_metadata(value)
            write_json(destination/name,value)
    source=dict(version=version,source_commit=source_commit,
        canonical_location='repository data/sources/*.json',
        effective_data_sha256=hashlib.sha256(json_bytes(data)).hexdigest(),
        data_files=initial_inputs,
        generation='offline from committed canonical data; no crawling during release',
        blocked_formats=[name for name,profile in FORMATS.items() if profile['status']=='blocked'])
    write_json(destination/'SOURCE.json',source)
    totals=report['totals']
    lines=[f'# 全国神社辞書 {version}','',
        '調査した都道府県神社庁の公式掲載情報に基づく辞書です。収集済み範囲はreport.jsonで確認してください。','',
        f'- 正本コミット: `{source_commit}`',
        f"- 施設レコード: {totals['facilities']}",
        f"- 確認済み施設: {totals['verified_facilities']}",
        f"- 重複除去後辞書行: {totals['dictionary_rows']}",
        '- 全形式の実際のIME取り込みは未確認です。','',
        '| 形式 | 出力状態 | レコード／行数 |','| --- | --- | ---: |']
    for name,item in report['format_outputs'].items():
        lines.append(f"| {name} | {item['status']} | {item['rows']} |")
    lines += ['', 'JSON・CSVは未確認を含む管理用データです。IME用の登録行とは件数が異なります。',
        '保留形式は仕様確認不足のためファイルを生成していません。全国の全神社を網羅したとは主張しません。',
        '出典と検証状態は管理用JSON/CSV・サンプルmanifestに含まれます。',
        'ソースコードはMIT。収集元データの利用条件は正本の出典別メタデータを参照してください。','']
    notes='\n'.join(lines)
    (destination/'README.md').write_text(notes,encoding='utf-8')
    (output_dir/'RELEASE_NOTES.md').write_text(notes,encoding='utf-8')
    checks={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.rglob('*')) if p.is_file() and p.name!='checksums.json'}
    write_json(destination/'checksums.json',checks)
    if _input_hashes(data_dir)!=initial_inputs:
        raise ValueError('canonical inputs changed during generation; retry from a fixed commit')
    archive=output_dir/f'national-jinja-dictionary-{version}.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(destination.rglob('*')):
            if not path.is_file():continue
            info=zipfile.ZipInfo(str(path.relative_to(destination)),date_time=(1980,1,1,0,0,0))
            info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,path.read_bytes(),compresslevel=9)
    checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum_file=output_dir/'SHA256SUMS'
    checksum_file.write_text(f'{checksum}  {archive.name}\n',encoding='utf-8')
    return dict(archive=str(archive),checksum_file=str(checksum_file),source_commit=source_commit,
        totals=totals,blocked_formats=source['blocked_formats'])


def require_matching_tag(repository,tag):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,80}',tag):raise ValueError('unsafe release tag')
    def rev(ref):
        result=subprocess.run(['git','rev-parse','--verify',ref],cwd=repository,capture_output=True,text=True)
        if result.returncode:raise ValueError('release tag or checkout commit not found')
        return result.stdout.strip()
    head=rev('HEAD');expected=rev('refs/tags/'+tag+'^{commit}')
    if head!=expected:raise ValueError('checkout does not match the fully qualified release tag')
    return head


def main(argv=None):
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description='Generate fresh release assets from repository canonical data, offline')
    p.add_argument('--data-dir',type=Path,default=root/'data')
    p.add_argument('--output-dir',type=Path,default=root/'dist')
    p.add_argument('--version',required=True)
    p.add_argument('--source-commit')
    p.add_argument('--expected-tag',help='require checkout HEAD to equal refs/tags/TAG before publishing')
    args=p.parse_args(argv)
    commit=args.source_commit
    if args.expected_tag:
        actual=require_matching_tag(root,args.expected_tag)
        if commit is not None and commit!=actual:raise ValueError('source commit differs from the release tag')
        commit=actual
    if commit is None:
        result=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True)
        commit=result.stdout.strip() if result.returncode==0 else 'unknown'
    result=create_release(args.data_dir,args.output_dir,args.version,commit)
    print(result['archive'])
    return 0

if __name__=='__main__':raise SystemExit(main())
