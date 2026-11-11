"""Workflow-driven release: build first, create tag, upload draft assets, publish."""
import argparse
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from urllib import request,error,parse
from njd.changelog import validate_version,previous_release_tag,generate_changelog
from njd.release import create_release,require_committed_inputs

LOG=logging.getLogger(__name__)


class GitHubError(RuntimeError):
    def __init__(self,status):
        self.status=status;super().__init__(f'GitHub API failed: HTTP {status}')


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class GitHub:
    def __init__(self,repo,token):
        import re
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise ValueError('invalid GitHub repository')
        if not token:raise ValueError('GH_TOKEN is required')
        self.repo=repo;self.token=token;self.opener=request.build_opener(NoRedirect)

    def api(self,method,path,payload=None,*,absent=False,data=None):
        host='uploads.github.com' if data is not None else 'api.github.com'
        body=data if data is not None else json.dumps(payload).encode() if payload is not None else None
        headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json',
            'X-GitHub-Api-Version':'2026-03-10','Content-Type':'application/octet-stream' if data is not None else 'application/json'}
        req=request.Request(f'https://{host}/repos/{self.repo}/'+path,data=body,method=method,headers=headers)
        try:
            with self.opener.open(req,timeout=120) as response:return json.load(response)
        except error.HTTPError as exc:
            status=exc.code;exc.close()
            if absent and status==404:return None
            raise GitHubError(status) from None

    def pages(self,path):
        result=[];page=1
        while True:
            items=self.api('GET',path+f'?per_page=100&page={page}')
            result.extend(items)
            if len(items)<100:return result
            page+=1

    def resolve_tag(self,tag):
        ref=self.api('GET','git/ref/tags/'+parse.quote(tag,safe=''),absent=True)
        if ref is None:return None
        obj=ref['object']
        for _ in range(10):
            if obj['type']=='commit':return obj['sha']
            if obj['type']!='tag':break
            obj=self.api('GET','git/tags/'+obj['sha'])['object']
        raise ValueError('release tag does not resolve to a commit')

    def published_tags(self):return [r['tag_name'] for r in self.pages('releases') if not r['draft']]

    def create_tag(self,tag,commit):
        try:self.api('POST','git/refs',dict(ref='refs/tags/'+tag,sha=commit))
        except GitHubError as exc:
            if exc.status!=422 or self.resolve_tag(tag)!=commit:raise

    def find_release(self,tag):return self.api('GET','releases/tags/'+parse.quote(tag,safe=''),absent=True)

    def create_draft(self,tag,commit,body):
        return self.api('POST','releases',dict(tag_name=tag,target_commitish=commit,name='全国神社辞書 '+tag,
            body=body,draft=True,prerelease='-' in tag.split('+',1)[0]))

    def assets(self,rid):return self.pages(f'releases/{rid}/assets')

    def upload(self,rid,path):
        return self.api('POST',f'releases/{rid}/assets?name='+parse.quote(path.name,safe=''),data=path.read_bytes())

    def publish(self,rid,body):return self.api('PATCH',f'releases/{rid}',dict(draft=False,body=body))


def _digest(path):return 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_assets(api,rid,paths,*,require_all):
    existing={asset['name']:asset for asset in api.assets(rid)}
    unexpected=set(existing)-{path.name for path in paths}
    if unexpected:raise ValueError('unexpected release asset: '+sorted(unexpected)[0])
    missing=[]
    for path in paths:
        item=existing.get(path.name)
        if item is None:missing.append(path);continue
        if item.get('state')!='uploaded' or item.get('digest')!=_digest(path):
            raise ValueError('release asset differs or cannot be verified: '+path.name)
    if missing and require_all:raise ValueError('published release asset is missing: '+missing[0].name)
    return missing


def _metadata(release,version,commit):
    marker=re.search(r'<!-- njd-release (\{[^\n]+\}) -->',release.get('body',''))
    if not marker:raise ValueError('existing release provenance metadata cannot be verified')
    metadata=json.loads(marker[1])
    if not isinstance(metadata,dict) or metadata.get('version')!=version or metadata.get('commit')!=commit or 'previous_release_tag' not in metadata:
        raise ValueError('existing release provenance metadata differs')
    previous=metadata['previous_release_tag']
    if previous is not None:validate_version(previous)
    return dict(version=version,commit=commit,previous_release_tag=previous)


def run_release(repository,repo,version,api,output_dir,*,dry_run=False,generator=create_release):
    if isinstance(version,str) and not version.startswith('v'):version='v'+version
    validate_version(version)
    root=Path(repository);out=Path(output_dir)
    commit=require_committed_inputs(root,root/'data')
    target=api.resolve_tag(version)
    if target is not None and target!=commit:raise ValueError('release tag already points to a different commit')
    release=api.find_release(version)
    if release is not None:
        previous=_metadata(release,version,commit)['previous_release_tag']
    else:previous=previous_release_tag(root,commit,api.published_tags(),version)
    changelog=generate_changelog(root,repo,version,commit,previous)
    LOG.info('Generating %s offline from %s (previous release: %s)',version,commit,previous or 'initial release')
    result=generator(root/'data',out,version,commit,changelog=changelog,previous_release_tag=previous)
    LOG.info('Generated release: %s',result['archive'])
    paths=[Path(result['dictionary_archive'])]
    source=json.loads((out/'SOURCE.json').read_text())
    if source.get('source_commit')!=commit or source.get('version')!=version or source.get('blocked_formats'):
        raise ValueError('generated release provenance or format completion is invalid')
    base=f'https://github.com/{repo}/tree/{commit}'
    totals=result['totals'];report=json.loads((out/'dictionaries/report.json').read_text())
    lines=[f'# 全国神社辞書 {version}','',
        '添付ZIPには全国版・都道府県別・確認用サンプルのIME辞書だけを収録しています。',
        '全神社を網羅したものではありません。実際のIMEへの取り込み・変換は未確認です。','',
        f'- 正本コミット: `{commit}`',f"- 施設数: {totals['facilities']}",
        f"- 出力条件を満たす施設: {totals['verified_facilities']}",
        f"- 重複除去後の辞書行数: {totals['dictionary_rows']}",'',
        '| 形式 | 全国版の出力行数 |','| --- | ---: |']
    lines.extend(f"| {name} | {item['rows']} |" for name,item in report['format_outputs'].items() if name not in ('json','csv'))
    notes='\n'.join(lines)+'\n\n## 出典・利用条件\n\n'
    notes+=f'名称・読み・所在地の原文、出典URL・版・利用条件: [正本データ]({base}/data/)、[補正根拠]({base}/data/corrections.json)、[情報源一覧]({base}/docs/SOURCES.md)。\n'
    notes+='Wikipedia由来項目はCC BY-SA 4.0に従い、カタカナ読みをひらがなへ機械変換しています。各記事・版・ライセンスは上記正本に保存しています。コードのMITは収集元データへ適用しません。\n'
    attribution=json.loads((out/'dictionaries/ATTRIBUTION.json').read_text())
    for credit in attribution.get('licensed_references',[]):
        notes+='\n'+credit.get('attribution',credit.get('title','参考資料'))
        notes+=' '+credit.get('url','')+' '+credit.get('license_url','')+' '+credit.get('processed_notice','')+'\n'
    notes+='\n辞書ZIP SHA-256: `'+_digest(paths[0]).removeprefix('sha256:')+'`\n'
    if len(notes)>55000:raise ValueError('release attribution exceeds body limit')
    body=notes+'\n'+changelog
    if len(body)>60000:
        comparison=f'https://github.com/{repo}/compare/{previous}...{version}' if previous else f'https://github.com/{repo}/commits/{commit}'
        body=notes+'\n'+changelog[:max(0,56000-len(notes))].rsplit('\n',1)[0]+f'\n\n[変更履歴の全件]({comparison})。CHANGELOG全文はWorkflowの検証用Artifactsに保存しています。\n'
    metadata=dict(version=version,commit=commit,previous_release_tag=previous)
    body+='\n<!-- njd-release '+json.dumps(metadata,sort_keys=True)+' -->\n'
    result.update(previous_release_tag=previous)
    if dry_run:
        LOG.info('Dry run complete; no tag or release created')
        return dict(result,status='dry_run')
    if target is None:api.create_tag(version,commit)
    if api.resolve_tag(version)!=commit:raise ValueError('release tag changed before publication')
    release=api.find_release(version)
    if release is not None and _metadata(release,version,commit)!=metadata:
        raise ValueError('release provenance changed during generation')
    if release is not None and not release['draft']:
        _verify_assets(api,release['id'],paths,require_all=True)
        return dict(result,status='already_published',url=release['html_url'])
    if release is None:release=api.create_draft(version,commit,body)
    for path in _verify_assets(api,release['id'],paths,require_all=False):
        LOG.info('Uploading %s',path.name);api.upload(release['id'],path)
    _verify_assets(api,release['id'],paths,require_all=True)
    if api.resolve_tag(version)!=commit:raise ValueError('release tag changed during upload')
    api.publish(release['id'],body)
    return dict(result,status='published',url=release['html_url'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',required=True)
    parser.add_argument('--dry-run',action='store_true',help='build artifacts without creating a tag or release')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    repo=os.environ.get('GH_REPO','');api=GitHub(repo,os.environ.get('GH_TOKEN',''))
    result=run_release(root,repo,args.version,api,root/'dist',dry_run=args.dry_run)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__=='__main__':main()
