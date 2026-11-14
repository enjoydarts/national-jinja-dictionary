"""Build release assets offline from the canonical data of a specific commit."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import zipfile
from njd.__main__ import build_outputs, _review_lists, _effective
from njd.exporters import FORMATS
from njd.corrections import apply_corrections
from njd.locations import apply_locations
from njd.reviews import apply_reviews
from njd.nationwide import merge_collections, ensure_public_metadata
from njd.storage import apply_decisions, json_bytes, load_dataset, write_json
from njd.validation import blocking_problems
from njd.source_aliases import apply_saved_source_aliases


def licensed_reference_credits(refs):
    """Keep prescribed non-Wikipedia source credits in standalone release assets."""
    credits={}
    for ref in refs:
        if not isinstance(ref,dict) or ref.get('source_kind')=='encyclopedia' or not ref.get('license_url'):continue
        item={key:ref[key] for key in ('source_kind','url','title','license_url','attribution','processed_notice','source_publisher','doi') if key in ref}
        credits[json_bytes(item)]=item
    return [credits[key] for key in sorted(credits)]


def _input_hashes(data_dir):
    paths=sorted((data_dir/'sources').glob('*.json'))
    paths += [data_dir/name for name in ('manifest.json','decisions.json','identities.json','locations.json','corrections.json','reviews.json','source_aliases.json','source_catalog.json','reading_research.json') if (data_dir/name).exists()]
    return {str(p.relative_to(data_dir)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def write_dictionary_archive(directory,archive):
    """Package only known IME outputs from national, prefecture and sample scopes."""
    directory=Path(directory);archive=Path(archive)
    names={name+'.'+profile['extension'] for name,profile in FORMATS.items() if name not in ('json','csv')}
    selected=[]
    for path in sorted(directory.rglob('*')):
        if not path.is_file() or path.name not in names:continue
        relative=path.relative_to(directory)
        scope=relative.parts[:-1]
        if scope and scope[0]=='samples':scope=scope[1:]
        if scope==('national',) or (len(scope)==2 and scope[0]=='prefectures' and scope[1] in {f'{n:02}' for n in range(1,48)}):
            selected.append((relative,path))
    if not selected:raise ValueError('no IME dictionary files to package')
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for relative,path in selected:
            info=zipfile.ZipInfo(str(relative),date_time=(1980,1,1,0,0,0))
            info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,path.read_bytes(),compresslevel=9)
    return archive


def create_release(data_dir,output_dir,version,source_commit,changelog=None,previous_release_tag=None,*,legacy=False):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,80}',version): raise ValueError('unsafe release version')
    if not re.fullmatch(r'[0-9a-f]{40,64}|unknown',source_commit): raise ValueError('invalid source commit')
    data_dir=Path(data_dir);output_dir=Path(output_dir)
    initial_inputs=_input_hashes(data_dir)
    data=_effective(data_dir,legacy=legacy)
    ensure_public_metadata(data)
    problems=blocking_problems(data)
    if problems:raise ValueError('canonical data cannot be released: '+str(problems[:5]))
    destination=output_dir/'dictionaries'
    report,has_blocked=build_outputs(data,data_dir,list(FORMATS),sample_names=('倭文神社','大國神社','𡶌部神社','㯮椒神社'),output_dir=destination)
    _review_lists(data,destination)
    if not legacy:
        from njd.canonical import research_summary
        write_json(destination/'canonical-summary.json',dict(research=research_summary(data_dir),
            metadata_basis='Current counts generated from canonical adopted records; inherited snapshot counts are historical.'))
    for name in ('manifest.json','locations.json','corrections.json','reviews.json','source_aliases.json','source_catalog.json','reading_research.json'):
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
    if changelog is not None:
        source['changelog_sha256']=hashlib.sha256(changelog.encode('utf-8')).hexdigest()
        source['previous_release_tag']=previous_release_tag
    write_json(destination/'SOURCE.json',source)
    write_json(output_dir/'SOURCE.json',source)
    if changelog is not None:
        (destination/'CHANGELOG.md').write_text(changelog,encoding='utf-8')
        (output_dir/'CHANGELOG.md').write_text(changelog,encoding='utf-8')
    credits={}
    refs=[f.get('source_reference') for f in data['facilities']]
    refs += [ref for f in data['facilities'] for ref in f.get('additional_source_references',[])]
    refs += [ref for e in data['entries'] for ref in e.get('correction',{}).get('references',[])]
    for ref in refs:
        if not isinstance(ref,dict) or ref.get('source_kind')!='encyclopedia' or not ref.get('license_url'):continue
        item={key:ref[key] for key in ('url','title','revision_id','permalink','license_url') if key in ref}
        item['processing_notice']='日本語版Wikipediaから名称・読み・所在地の事実項目を抽出。読みのカタカナはひらがなに機械変換。'
        credits[(ref.get('url',''),str(ref.get('revision_id','')))]=item
    association=[dict(publisher=s['source_publisher'],source_key=k,listing_basis=s['listing_basis'],
        authority_reference=s.get('authority_reference'),redistribution_status=s.get('redistribution_status'),
        data_use_conditions=s.get('data_use_conditions','unconfirmed'),
        processing_notice='神道青年会の独自神社紹介から名称・読み・所在地の事実項目を抽出。神社庁掲載とは区別。本文・画像は配布しない。')
        for k,s in sorted(data['collection'].get('sources',{}).items()) if s.get('listing_basis')=='association_reference']
    licensed=licensed_reference_credits(refs)
    write_json(destination/'ATTRIBUTION.json',dict(wikipedia=[credits[key] for key in sorted(credits)],association=association,licensed_references=licensed))
    totals=report['totals']
    reference_count=totals.get('source_basis_counts',{}).get('wikipedia_reference',{}).get('facilities',0)
    description=('神社庁の公式掲載情報と、利用できない掲載情報を補うWikipediaの参考資料に基づく辞書です。出典区分と収集済み範囲はreport.jsonで確認してください。'
        if reference_count else '調査した都道府県神社庁の公式掲載情報に基づく辞書です。収集済み範囲はreport.jsonで確認してください。')
    if association:
        description='神社庁の公式掲載情報と、別区分の参考資料（Wikipedia・宮崎県神道青年会）に基づく辞書です。実際に含む出典区分と収集済み範囲はreport.jsonで確認してください。'
    lines=[f'# 全国神社辞書 {version}','',
        description,'',
        f'- 正本コミット: `{source_commit}`',
        f"- 施設レコード: {totals['facilities']}",
        *([f"- 原掲載の管理レコード: {totals['facility_records']}（同一施設の重複掲載観測 {totals['source_alias_records']} 件を含む）"] if totals.get('source_alias_records') else []),
        f"- 確認済み施設: {totals['verified_facilities']}",
        f"- 重複除去後辞書行: {totals['dictionary_rows']}",
        '- 全形式の実際のIME取り込みは未確認です。','',
        '| 形式 | 出力状態 | レコード／行数 |','| --- | --- | ---: |']
    for name,item in report['format_outputs'].items():
        lines.append(f"| {name} | {item['status']} | {item['rows']} |")
    lines += ['', 'JSON・CSVは未確認を含む管理用データです。IME用の登録行とは件数が異なります。',
        ('保留形式は仕様確認不足のためファイルを生成していません。' if has_blocked else '初版対象の全IME形式を生成しています。')+'全国の全神社を網羅したとは主張しません。',
        '出典と検証状態は管理用JSON/CSV・サンプルmanifestに含まれます。',
        'Wikipedia由来の出典・版・ライセンスはATTRIBUTION.jsonに記載しています。参考資料単独の収録を神社庁掲載確認済み件数に加えていません。',
        *(['国税庁等のライセンス付き補完資料の指定クレジット・利用条件・加工説明はATTRIBUTION.jsonのlicensed_referencesに保存しています。ソースコードのMITをこれらの資料へ適用しません。'] if licensed else []),
        *(['宮崎県神道青年会の資料の再利用条件は未確認です。MIT・WikipediaのCC BY-SAを適用しません。出典と状態はATTRIBUTION.jsonを参照してください。'] if association else []),
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
    sums=[f'{checksum}  {archive.name}',hashlib.sha256((output_dir/'SOURCE.json').read_bytes()).hexdigest()+'  SOURCE.json']
    if changelog is not None:sums.append(hashlib.sha256((output_dir/'CHANGELOG.md').read_bytes()).hexdigest()+'  CHANGELOG.md')
    checksum_file.write_text('\n'.join(sums)+'\n',encoding='utf-8')
    dictionary_archive=write_dictionary_archive(destination,output_dir/'release-assets'/archive.name)
    return dict(archive=str(archive),checksum_file=str(checksum_file),source_commit=source_commit,
        dictionary_archive=str(dictionary_archive),totals=totals,blocked_formats=source['blocked_formats'])


def require_matching_tag(repository,tag):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,80}',tag):raise ValueError('unsafe release tag')
    def rev(ref):
        result=subprocess.run(['git','rev-parse','--verify',ref],cwd=repository,capture_output=True,text=True)
        if result.returncode:raise ValueError('release tag or checkout commit not found')
        return result.stdout.strip()
    head=rev('HEAD');expected=rev('refs/tags/'+tag+'^{commit}')
    if head!=expected:raise ValueError('checkout does not match the fully qualified release tag')
    return head


def require_committed_inputs(repository,data_dir):
    repository=Path(repository).resolve();data_dir=Path(data_dir).resolve()
    try:relative=data_dir.relative_to(repository)
    except ValueError:raise ValueError('release canonical data must be in the source repository') from None
    def git(*args):
        result=subprocess.run(['git',*args],cwd=repository,capture_output=True,text=True)
        if result.returncode:raise ValueError('cannot verify release repository inputs')
        return result.stdout
    changed=git('status','--porcelain=v1','--untracked-files=all','--',str(relative),'njd','pyproject.toml')
    if changed:raise ValueError('uncommitted release inputs; commit canonical data and code before packaging')
    tracked=set(git('ls-files','-z','--',str(relative),'njd').split('\0'))
    inputs=[data_dir/name for name in _input_hashes(data_dir)]
    inputs+=list((repository/'njd').rglob('*.py'))
    if any(str(path.relative_to(repository)) not in tracked for path in inputs):
        raise ValueError('untracked or ignored release inputs cannot be attributed to a source commit')
    return git('rev-parse','--verify','HEAD').strip()


def main(argv=None):
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description='Generate fresh release assets from repository canonical data, offline')
    p.add_argument('--data-dir',type=Path,default=root/'data')
    p.add_argument('--output-dir',type=Path,default=root/'dist')
    p.add_argument('--version',required=True)
    p.add_argument('--source-commit')
    p.add_argument('--expected-tag',help='require checkout HEAD to equal refs/tags/TAG before publishing')
    args=p.parse_args(argv)
    actual=require_committed_inputs(root,args.data_dir)
    commit=args.source_commit or actual
    if commit!=actual:raise ValueError('source commit differs from the repository checkout')
    if args.expected_tag:
        actual=require_matching_tag(root,args.expected_tag)
        if commit is not None and commit!=actual:raise ValueError('source commit differs from the release tag')
        commit=actual
    result=create_release(args.data_dir,args.output_dir,args.version,commit)
    print(result['archive'])
    return 0

if __name__=='__main__':raise SystemExit(main())
