"""Command-line collection, validation, auditing and reproducible generation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from njd import __version__
from njd.adapters import gunma
from njd.audit import audit_gunma
from njd.exporters import render, FORMATS
from njd.http import Client, FetchError
from njd.report import report, samples, subset
from njd.storage import apply_decisions, load_dataset, save_dataset, write_json
from njd.validation import validate

REPOSITORY=Path(__file__).resolve().parents[1]

def external_workspace(value):
    path=Path(value).expanduser().resolve()
    if path==REPOSITORY or REPOSITORY in path.parents:
        raise ValueError('local records must be stored outside the public repository (for example, in Obsidian)')
    return path

def parser():
    p=argparse.ArgumentParser(description='全国神社辞書: source-grounded data and IME generation')
    p.add_argument('--version',action='version',version=__version__)
    p.add_argument('--workspace',required=True,help='external directory for canonical data, caches and reports')
    sub=p.add_subparsers(dest='command',required=True)
    collect=sub.add_parser('collect'); collect.add_argument('source',choices=['gunma'])
    collect.add_argument('--limit',type=int,default=100,help='maximum source rows; 0 selects all observed rows')
    collect.add_argument('--offline',action='store_true'); collect.add_argument('--refresh',action='store_true')
    sub.add_parser('validate'); sub.add_parser('audit'); sub.add_parser('report')
    build=sub.add_parser('build'); build.add_argument('--formats',default='all',help='all or comma-separated mozc,json,csv,atok,google,msime,macos')
    build.add_argument('--prefecture',choices=[f'{i:02}' for i in range(1,48)])
    build.add_argument('--sample-name',action='append',default=[])
    return p

def _effective(work):
    data=load_dataset(work/'common.json')
    decisions=work/'decisions.json'
    return apply_decisions(data,load_dataset(decisions)) if decisions.exists() else data

def _review_lists(data,work):
    for status in ['pending','excluded']:
        write_json(work/(status+'.json'),[e for e in data['entries'] if e['status']==status])

def build_outputs(data,work,formats,requested_prefecture=None,sample_names=()):
    unknown=set(formats)-FORMATS.keys()
    if unknown: raise ValueError('unknown formats: '+','.join(sorted(unknown)))
    destination=work/'generated'; staging=work/'generated.tmp'
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir()
    scopes={'national':data}
    codes=sorted({f['prefecture_code'] for f in data['facilities']})
    for code in codes:
        if requested_prefecture is None or code==requested_prefecture:
            scopes['prefectures/'+code]=subset(data,code)
    if requested_prefecture:
        scopes={'prefectures/'+requested_prefecture:subset(data,requested_prefecture)}
    summaries={}; national_outputs={}; blocked=False
    for scope,scope_data in scopes.items():
        outputs={name:render(scope_data,name) for name in formats}
        summaries[scope]={name:out.summary() for name,out in outputs.items()}
        if scope=='national' or requested_prefecture: national_outputs=outputs
        for name,out in outputs.items():
            if out.content is not None:
                target=staging/scope/(name+'.'+FORMATS[name]['extension']); target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(out.content)
            else: blocked=True
        sample=samples(scope_data,names=sample_names)
        write_json(staging/'samples'/scope/'manifest.json',sample)
        for name in formats:
            out=render(sample,name)
            if out.content is not None:
                (staging/'samples'/scope/(name+'.'+FORMATS[name]['extension'])).write_bytes(out.content)
    report_data=report(subset(data,requested_prefecture) if requested_prefecture else data,national_outputs)
    report_data['scopes']=summaries
    write_json(staging/'report.json',report_data)
    write_json(staging/'formats.json',FORMATS)
    checksums={str(p.relative_to(staging)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(staging.rglob('*')) if p.is_file()}
    write_json(staging/'checksums.json',checksums)
    # Replace only our generated directory, so unrequested stale files cannot
    # masquerade as outputs of this run. Preserve the prior generation on errors.
    backup=work/'generated.previous'
    if backup.exists(): shutil.rmtree(backup)
    if destination.exists(): destination.rename(backup)
    try: staging.rename(destination)
    except OSError:
        if backup.exists(): backup.rename(destination)
        raise
    if backup.exists(): shutil.rmtree(backup)
    return report_data,blocked

def main(argv=None):
    args=parser().parse_args(argv)
    work=external_workspace(args.workspace)
    work.mkdir(parents=True,exist_ok=True)
    if args.command=='collect':
        if args.limit<0: raise ValueError('limit must be nonnegative')
        if args.offline and args.refresh: raise ValueError('offline and refresh cannot be combined')
        client=Client(work/'cache',offline=args.offline)
        page=client.fetch(gunma.URL,refresh=args.refresh)
        data=gunma.parse(page.text,page.fetched_at,page.sha256,limit=args.limit or None)
        delta=save_dataset(work/'common.json',data)
        if not (work/'decisions.json').exists(): write_json(work/'decisions.json',{})
        _review_lists(_effective(work),work)
        print(json.dumps(dict(facilities=len(data['facilities']),observed_rows=data['collection']['source_rows_observed'],changes={k:len(v) for k,v in delta.items()}),ensure_ascii=False))
        return 0
    data=_effective(work)
    if args.command=='validate':
        issues=validate(data); write_json(work/'validation.json',issues); _review_lists(data,work)
        print(json.dumps(dict(problems=len(issues),facilities=len(data['facilities'])),ensure_ascii=False))
        return 1 if issues else 0
    if args.command=='audit':
        # Audit pristine acquired records; human decisions remain separate.
        raw=load_dataset(work/'common.json')
        page=Client(work/'cache',offline=True).fetch(gunma.URL)
        result=audit_gunma(raw,page.text,page.sha256); write_json(work/'source-audit.json',result)
        print(json.dumps(result,ensure_ascii=False)); return 1 if result['mismatches'] else 0
    if args.command=='report':
        result=report(data); write_json(work/'report.json',result)
        print(json.dumps(result['totals'],ensure_ascii=False)); return 0
    if args.command=='build':
        formats=list(FORMATS) if args.formats=='all' else args.formats.split(',')
        result,blocked=build_outputs(data,work,formats,args.prefecture,args.sample_name)
        _review_lists(data,work)
        print(json.dumps(result['totals'],ensure_ascii=False))
        if blocked: print('Some requested formats are blocked; see generated/report.json',file=sys.stderr)
        return 2 if blocked else 0
    return 1

if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError,KeyError,FetchError) as exc:
        print(f'error: {exc}',file=sys.stderr); sys.exit(1)
