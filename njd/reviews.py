"""Explicit human decisions, bound to immutable acquired facility snapshots.

These are approvals, not automatically established website facts. No pronunciation
or name segmentation is inferred by this module.
"""
import copy
from datetime import datetime
import re
from uuid import NAMESPACE_URL, uuid5
from njd.corrections import _url, _reference_matches
from njd.normalize import normalize_reading


def _plain(value):
    return isinstance(value,str) and bool(value) and not any(ord(c)<32 or ord(c)==127 for c in value) and '<' not in value and '>' not in value


def review_problems(review, facility, entry, source=None):
    problems=[]
    if not isinstance(review,dict):return ['invalid human review']
    if review.get('confirmation')!='user_confirmation' or not review.get('case_id') or not review.get('reason'):
        problems.append('missing explicit human confirmation')
    try:datetime.fromisoformat(review.get('recorded_at',''))
    except (ValueError,TypeError):problems.append('missing human confirmation date')
    expected=dict(name_raw=facility.get('name_raw'),reading_raw=entry.get('reading_raw'),address=facility.get('address'),listing_url=facility.get('listing_url'))
    if review.get('facility_id')!=facility['id'] or review.get('expected_source_hash')!=entry.get('source_hash') or review.get('original')!=expected:
        problems.append('human review is stale or targets another source snapshot')
    if (source or {}).get('authority_status') in ('pending','unconfirmed'):
        problems.append('official agency listing authority remains unconfirmed')
    if entry.get('identity_review_required') or facility.get('review_reason'):
        problems.append('unresolved facility identity review')
    if not _plain(facility.get('address')) or not facility.get('municipality'):
        problems.append('unresolved facility location')
    conflicts=facility.get('source_conflicts',[])
    if conflicts:
        if review.get('resolved_reading_conflicts')!=conflicts or any(c.get('name_raw')!=facility['name_raw'] or c.get('address')!=facility['address'] for c in conflicts):
            problems.append('source conflicts not limited to explicitly reviewed readings')
    allowed_reasons={'','source name uses an external glyph; Unicode correction requires references',
        'control or layout characters in source name; explicit review required',
        'conflicting source rows for the same source identity'}
    if facility.get('status')!='verified' and facility.get('reason') not in allowed_reasons:
        problems.append('unresolved facility condition')
    outputs=review.get('outputs')
    if not isinstance(outputs,list) or not outputs or any(not isinstance(o,dict) for o in outputs):
        return problems+['missing approved output records']
    if not review.get('split') and len(outputs)!=1:problems.append('multiple outputs require explicit split approval')
    if len({(o.get('surface'),o.get('reading')) for o in outputs})!=len(outputs):problems.append('duplicate approved outputs')
    refs=review.get('references',[])
    if not isinstance(refs,list) or any(not isinstance(r,dict) for r in refs):return problems+['invalid human review references']
    for ref in refs:
        if not all(ref.get(k) for k in ('title','source_kind','name_raw','excerpt')) or not _url(ref.get('url')):
            problems.append('incomplete inspected reference')
        try:datetime.fromisoformat(ref.get('checked_at',''))
        except (ValueError,TypeError):problems.append('missing reference inspection date')
    def bound(ref,output):
        if _reference_matches(ref,facility,entry,dict(surface=output['surface'])):return True
        # An explicit judgment accepts only this exact observed discrepancy.
        item=dict(url=ref.get('url'),agency_name=facility['name_raw'],agency_address=facility['address'],
            reference_name=ref.get('name_raw'),reference_address=ref.get('address_raw'))
        return item in review.get('accepted_identity_differences',[]) and bool(ref.get('address_raw'))
    if review.get('split'):
        name=facility['name_raw'];raw=entry['reading_raw']
        for field,value in [('excluded_name_prefix',name),('excluded_reading_prefix',raw)]:
            prefix=review.get(field,'')
            if not isinstance(prefix,str) or not value.startswith(prefix):problems.append('split alias prefix differs from source')
        name=name.removeprefix(review.get('excluded_name_prefix','')).strip()
        raw=raw.removeprefix(review.get('excluded_reading_prefix','')).strip()
        if re.sub(r'\s+','',name)!=''.join(o.get('surface','') for o in outputs):problems.append('approved split does not account for source names')
        try:
            if [normalize_reading(r) for r in raw.split()]!=[o.get('reading') for o in outputs]:raise ValueError()
        except ValueError:problems.append('split readings do not match whole source tokens')
    for output in outputs:
        surface=output.get('surface');reading=output.get('reading');basis=output.get('basis');url=output.get('reading_url')
        if not _plain(surface):problems.append('invalid approved surface');continue
        try:
            if normalize_reading(reading)!=reading:raise ValueError()
        except (ValueError,TypeError):problems.append('invalid approved reading');continue
        if surface!=facility['name_raw'] and not review.get('split') and not any(r.get('name_raw')==surface and surface in r.get('excerpt','') and bound(r,output) for r in refs):
            problems.append('approved name absent from bound reference')
        if basis=='user_confirmation':
            if url!='':problems.append('human-only reading must not claim a confirming page')
        elif basis=='agency_component':
            if not review.get('split') or url!=facility['listing_url']:problems.append('invalid agency component evidence')
        elif basis=='agency_selected':
            candidates=[dict(url=facility['listing_url'],reading_raw=entry['reading_raw'])]+conflicts
            if not any(c.get('url')==url and _normal(c.get('reading_raw'))==reading for c in candidates):problems.append('selected reading absent from agency sources')
        elif basis in ('reference','editorial_normalization'):
            matched=False
            for ref in refs:
                raw=ref.get('reading_raw','')
                if ref.get('url')!=url or not raw or raw not in ref.get('excerpt','') or ref.get('name_raw','') not in ref.get('excerpt','') or not bound(ref,output):continue
                value=_normal(raw)
                if basis=='editorial_normalization':
                    if raw!=output.get('source_reading_raw') or not output.get('edits'):continue
                    try:
                        for edit in output['edits']:
                            i=edit['index']
                            if not isinstance(i,int) or i<0 or value[i]!=edit['old'] or len(edit['new'])!=1:raise ValueError()
                            value=value[:i]+edit['new']+value[i+1:]
                    except (KeyError,TypeError,ValueError,IndexError):continue
                if value==reading:matched=True
            if not matched:problems.append('reading not supported by bound literal reference and approved edits')
        else:problems.append('unsupported human review reading basis')
    return problems


def _normal(raw):
    try:return normalize_reading(raw)
    except (ValueError,TypeError):return None


def reviewed_output(review,facility,entry,source=None):
    return (not review_problems(review,facility,entry,source) and entry.get('reading_source_kind')=='user_review'
        and any(all(entry.get(k)==o.get(k) for k in ('surface','reading','reading_url')) for o in review['outputs']))


def apply_reviews(data,document):
    if document.get('schema_version')!=1 or not isinstance(document.get('entries'),dict):raise ValueError('unsupported human review document')
    result=copy.deepcopy(data);fs={f['id']:f for f in result['facilities']};applied=[];pending=[];seen=set();children=[]
    for entry in result['entries']:
        review=document['entries'].get(entry['id'])
        if review is None:continue
        seen.add(entry['id']);f=fs[entry['facility_id']]
        source=result['collection'].get('sources',{}).get(f.get('source_key'),result['collection'])
        problems=review_problems(review,f,entry,source)
        if problems:
            entry['status']='pending';entry['reason']='; '.join(problems);entry['human_review']=copy.deepcopy(review)
            pending.append(entry['id']);continue
        f['status']='verified';f['reason']=''
        original=copy.deepcopy(entry)
        for output in review['outputs']:
            target=copy.deepcopy(original) if review.get('split') else entry
            target.pop('correction',None)
            if review.get('split'):
                target['id']=str(uuid5(NAMESPACE_URL,f"{f['id']}|formal-name|{output['surface']}"))
                target['parent_entry_id']=original['id'];children.append(target)
            target.update(surface=output['surface'],reading=output['reading'],reading_url=output['reading_url'],
                reading_source_kind='user_review',status='verified',reason='',checked_at=review['recorded_at'],
                evidence=review['reason'],human_review=copy.deepcopy(review))
        if review.get('split'):
            entry['status']='excluded';entry['reason']='Composite caption superseded by explicitly reviewed individual formal names'
            entry['superseded_by_review']=review['case_id']
        applied.append(original['id'])
    result['entries'].extend(children)
    result['collection']['human_reviews']=dict(applied=sorted(applied),pending=sorted(pending),unmatched=sorted(set(document['entries'])-seen))
    return result
