"""Reproducible release history from committed Git messages, without inference."""
import html
import re
import subprocess

VERSION=re.compile(r'v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?')


def validate_version(version):
    if not isinstance(version,str) or len(version)>80 or not VERSION.fullmatch(version):
        raise ValueError('release version must be vMAJOR.MINOR.PATCH, optionally with prerelease/build suffix')
    return version


def git(repository,*args,check=True):
    result=subprocess.run(['git',*args],cwd=repository,capture_output=True,text=True)
    if check and result.returncode:raise ValueError('cannot read committed release history')
    return result


def previous_release_tag(repository,commit,candidates,current):
    ranked=[]
    for tag in set(candidates)-{current}:
        if not isinstance(tag,str) or not VERSION.fullmatch(tag):continue
        ref='refs/tags/'+tag
        if git(repository,'rev-parse','--verify',ref+'^{commit}',check=False).returncode:continue
        if git(repository,'merge-base','--is-ancestor',ref,commit,check=False).returncode:continue
        distance=int(git(repository,'rev-list','--count',ref+'..'+commit).stdout)
        ranked.append((distance,tag))
    return min(ranked)[1] if ranked else None


def generate_changelog(repository,repo,version,commit,previous):
    validate_version(version)
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo):raise ValueError('invalid GitHub repository')
    args=['log','--format=%H%x00%s','--reverse',commit]
    if previous:
        if not VERSION.fullmatch(previous) or git(repository,'merge-base','--is-ancestor','refs/tags/'+previous,commit,check=False).returncode:
            raise ValueError('previous release tag is not an ancestor')
        args.append('^refs/tags/'+previous)
    lines=['# CHANGELOG — '+version,'',f'正本・コードのコミット: `{commit}`','',
        f'比較範囲: [{previous}...{version}](https://github.com/{repo}/compare/{previous}...{version})' if previous else '初回リリース: このコミットまでの全履歴。','',
        '以下はGitに記録されたコミット件名です。辞書の収集件数・検証状態とは区別します。','']
    records=git(repository,*args).stdout.splitlines()
    lines.append(f'## コミット（{len(records)}件）');lines.append('')
    for record in records:
        sha,subject=record.split('\0',1)
        prs=set(re.findall(r'^Merge pull request #(\d+)\b',subject))|set(re.findall(r'\(#(\d+)\)$',subject))
        escaped=re.sub(r'([\\`*_\[\]])',r'\\\1',html.escape(subject,quote=False))
        links=''.join(f' ([PR #{number}](https://github.com/{repo}/pull/{number}))' for number in sorted(prs,key=int))
        lines.append(f'- [{sha[:8]}](https://github.com/{repo}/commit/{sha}) {escaped}{links}')
    lines+=['','PRリンクはコミット件名に明示された番号だけを使用します。PR情報や変更内容を推測で補いません。','']
    return '\n'.join(lines)
