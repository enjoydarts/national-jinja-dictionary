"""Command-line collection, validation, auditing and reproducible generation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from njd import __version__
from njd.corrections import apply_corrections
from njd.locations import apply_locations
from njd.reviews import apply_reviews
from njd.catalog import registry
from njd.nationwide import merge_collections, run_collections
from njd.adapters import gunma
from njd.audit import audit_gunma
from njd.exporters import render, FORMATS
from njd.http import Client, FetchError
from njd.report import report, samples, subset
from njd.storage import apply_decisions, load_dataset, save_dataset, write_json, reconcile_identity
from njd.validation import validate, blocking_problems
from njd.source_aliases import apply_saved_source_aliases

REPOSITORY=Path(__file__).resolve().parents[1]

def external_workspace(value):
    path=Path(value).expanduser().resolve()
    if path==REPOSITORY or REPOSITORY in path.parents:
        raise ValueError('HTTP cache and legacy workspaces must be outside the public repository; canonical data belongs in data/')
    return path

def parser():
    p=argparse.ArgumentParser(description='全国神社辞書: source-grounded data and IME generation')
    p.add_argument('--version',action='version',version=__version__)
    p.add_argument('--workspace',help='legacy external combined workspace (prefer separate data/cache/output directories)')
    p.add_argument('--data-dir',default=str(REPOSITORY/'data'),help='version-controlled canonical source data')
    p.add_argument('--cache-dir',default=str(Path.home()/'.cache'/'national-jinja-dictionary'/'http'),help='private HTTP cache, outside the repository')
    p.add_argument('--output-dir',default=str(REPOSITORY/'dist'/'dictionaries'),help='fresh generated release files')
    sub=p.add_subparsers(dest='command',required=True)
    collect=sub.add_parser('collect'); collect.add_argument('source',help='registered source key or all')
    collect.add_argument('--limit',type=int,default=0,help='maximum source rows; 0 selects all observed rows')
    collect.add_argument('--offline',action='store_true'); collect.add_argument('--refresh',action='store_true')
    sub.add_parser('validate'); sub.add_parser('report')
    audit=sub.add_parser('audit',help='independent source audit (currently Gunma only)')
    audit.add_argument('--source',choices=['gunma'],default='gunma')
    build=sub.add_parser('build'); build.add_argument('--formats',default='all',help='all or comma-separated mozc,json,csv,atok,google,msime,macos')
    build.add_argument('--prefecture',choices=[f'{i:02}' for i in range(1,48)])
    build.add_argument('--sample-name',action='append',default=[])
    return p

def _effective(work):
    data=merge_collections(work)
    locations=work/'locations.json'
    if locations.exists():data=apply_locations(data,load_dataset(locations))
    corrections=work/'corrections.json'
    if corrections.exists():data=apply_corrections(data,load_dataset(corrections))
    reviews=work/'reviews.json'
    if reviews.exists():data=apply_reviews(data,load_dataset(reviews))
    decisions=work/'decisions.json'
    if decisions.exists() and load_dataset(decisions):data=apply_decisions(data,load_dataset(decisions))
    return apply_saved_source_aliases(data,work)

def _review_lists(data,work):
    facilities={f['id']:f for f in data['facilities']}
    for status in ['pending','excluded']:
        write_json(work/(status+'.json'),[dict(entry=e,facility=facilities[e['facility_id']]) for e in data['entries'] if e['status']==status])
    sources=data['collection'].get('sources',{data['collection'].get('source_key','unknown'):data['collection']})
    pending=[]
    for key,source in sorted(sources.items()):
        fields={field:source[field] for field in ('article_reviews','observation_reviews','identity_reviews') if source.get(field)}
        if fields:pending.append(dict(source_key=key,prefecture_code=source.get('prefecture_code'),listing_basis=source.get('listing_basis','agency'),**fields))
    write_json(work/'source-reviews.json',dict(schema_version=1,sources=pending,
        counting_notice='Unadopted source observations/articles are not facility counts; identity candidates may already be represented in canonical data.'))

def build_outputs(data,work,formats,requested_prefecture=None,sample_names=(),output_dir=None):
    unknown=set(formats)-FORMATS.keys()
    if unknown: raise ValueError('unknown formats: '+','.join(sorted(unknown)))
    destination=Path(output_dir) if output_dir is not None else work/'generated'
    staging=destination.with_name(destination.name+'.tmp')
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir(parents=True)
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
    backup=destination.with_name(destination.name+'.previous')
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
    if args.workspace:
        work=external_workspace(args.workspace); cache=work/'cache'; output=work/'generated'
    else:
        work=Path(args.data_dir).expanduser().resolve()
        cache=external_workspace(args.cache_dir)
        output=Path(args.output_dir).expanduser().resolve()
    if args.command=='collect': work.mkdir(parents=True,exist_ok=True)
    if args.command=='collect':
        if args.limit<0: raise ValueError('limit must be nonnegative')
        if args.offline and args.refresh: raise ValueError('offline and refresh cannot be combined')
        available=registry()
        keys=sorted(available,key=lambda k:available[k]['code']) if args.source=='all' else [args.source]
        if any(k not in available for k in keys): raise ValueError('unknown or unsupported source key')
        states=run_collections(work,available,keys,offline=args.offline,refresh=args.refresh,
            limit=args.limit or None,cache_dir=cache)
        if not (work/'identities.json').exists(): write_json(work/'identities.json',{})
        if not (work/'decisions.json').exists(): write_json(work/'decisions.json',{})
        print(json.dumps({k:v for k,v in states.items() if v['source_key'] in keys},ensure_ascii=False))
        return 1 if any(states[available[k]['code']]['status'].startswith('failed') for k in keys) else 0
    if args.command!='audit':data=_effective(work)
    if args.command=='validate':
        issues=validate(data); write_json((work if args.workspace else output)/'validation.json',issues); _review_lists(data,work if args.workspace else output)
        aliases=sum(bool(f.get('source_alias_of')) for f in data['facilities'])
        print(json.dumps(dict(errors=len(blocking_problems(data)),reviews=sum(p.get('severity')=='review' for p in issues),facilities=len(data['facilities'])-aliases,facility_records=len(data['facilities']),source_alias_records=aliases),ensure_ascii=False))
        return 1 if blocking_problems(data) else 0
    if args.command=='audit':
        # Audit pristine acquired records; human decisions remain separate.
        raw=load_dataset(work/'sources'/(args.source+'.json')) if (work/'sources').exists() else load_dataset(work/'common.json')
        page=Client(cache,offline=True).fetch(gunma.URL)
        result=audit_gunma(raw,page.text,page.sha256); write_json((work if args.workspace else output)/'source-audit.json',result)
        print(json.dumps(result,ensure_ascii=False)); return 1 if result['mismatches'] else 0
    if args.command=='report':
        result=report(data); write_json((work if args.workspace else output)/'report.json',result)
        print(json.dumps(result['totals'],ensure_ascii=False)); return 0
    if args.command=='build':
        formats=list(FORMATS) if args.formats=='all' else args.formats.split(',')
        result,blocked=build_outputs(data,work,formats,args.prefecture,args.sample_name,output_dir=output)
        _review_lists(data,work if args.workspace else output)
        print(json.dumps(result['totals'],ensure_ascii=False))
        if blocked: print('Some requested formats are blocked; see generated/report.json',file=sys.stderr)
        return 2 if blocked else 0
    return 1

if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError,KeyError,FetchError) as exc:
        print(f'error: {exc}',file=sys.stderr); sys.exit(1)
