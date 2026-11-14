"""Validate independent reading proposals before atomically updating overlays."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from njd.corrections import apply_corrections, correction_problems, _reference_matches
from njd.locations import apply_locations
from njd.nationwide import ensure_public_metadata, merge_collections
from njd.reviews import apply_reviews
from njd.normalize import normalize_reading
from njd.storage import apply_decisions, load_dataset, write_json
from njd.validation import blocking_problems, eligible
from njd.source_aliases import apply_saved_source_aliases


def _inputs(root):
    paths=list((root/'sources').glob('*.json'))
    paths += [root/name for name in ('locations.json','corrections.json','reviews.json','decisions.json','manifest.json','identities.json','source_aliases.json') if (root/name).exists()]
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def _agency_reading_refs(correction,facility):
    found=[]
    host=urlsplit(facility['listing_url']).hostname
    native=facility.get('native_source_id') or ''
    for ref in correction.get('references',[]):
        try:
            if ref.get('source_kind') not in ('agency','official_agency') or urlsplit(ref.get('url','')).hostname!=host:continue
            if urlsplit(native).scheme in ('http','https') and ref['url']!=native:continue
            if normalize_reading(ref.get('reading_raw',''))!=correction['changes']['reading']:continue
            if not _reference_matches(ref,facility,dict(surface=facility['listed_name']),correction['changes']):continue
            if not all(ref.get(k) and ref[k] in ref.get('excerpt','') for k in ('name_raw','reading_raw','address_raw')):continue
            found.append(ref)
        except (ValueError,TypeError,KeyError):continue
    return found


def import_proposals(data_dir,document,*,apply=False,prefer_agency=False):
    """All-or-nothing; never replace prior corrections, exclusions or reviews."""
    from njd.canonical import is_canonical, update_repository, _merged_raw
    if is_canonical(data_dir):
        def change(legacy):
            raw=_merged_raw(legacy)
            if 'locations.json' in legacy:raw=apply_locations(raw,legacy['locations.json'])
            corrections=copy.deepcopy(legacy.get('corrections.json',dict(schema_version=1,entries={})))
            result=_review_proposals(raw,corrections,
                legacy.get('reviews.json',dict(schema_version=1,entries={})),
                legacy.get('decisions.json',{}),document,prefer_agency,
                aliases=legacy.get('source_aliases.json'))
            legacy['corrections.json']=corrections
            result['applied']=bool(apply)
            return result
        return update_repository(data_dir,change,apply=apply)
    return _import_legacy_proposals(data_dir,document,apply=apply,prefer_agency=prefer_agency)


def _import_legacy_proposals(data_dir,document,*,apply=False,prefer_agency=False):
    root=Path(data_dir);initial=_inputs(root);raw=merge_collections(root)
    if (root/'locations.json').exists():raw=apply_locations(raw,load_dataset(root/'locations.json'))
    destination=root/'corrections.json'
    corrections=load_dataset(destination) if destination.exists() else dict(schema_version=1,entries={})
    reviews=load_dataset(root/'reviews.json') if (root/'reviews.json').exists() else dict(schema_version=1,entries={})
    decisions=load_dataset(root/'decisions.json') if (root/'decisions.json').exists() else {}
    aliases=load_dataset(root/'source_aliases.json') if (root/'source_aliases.json').exists() else None
    result=_review_proposals(raw,corrections,reviews,decisions,document,prefer_agency,aliases=aliases)
    if _inputs(root)!=initial:raise ValueError('canonical inputs changed during proposal review; retry')
    if apply and (result['added'] or result['replaced']):write_json(destination,corrections)
    return dict(result,applied=bool(apply))


def _review_proposals(raw,corrections,reviews,decisions,document,prefer_agency,*,aliases=None):
    if not isinstance(document,dict) or document.get('schema_version')!=1 or not isinstance(document.get('entries'),dict):
        raise ValueError('unsupported reading proposal document')
    ensure_public_metadata(document)
    facilities={f['id']:f for f in raw['facilities']};entries={e['id']:e for e in raw['entries']}
    added=[];unchanged=[];replaced=[]
    for eid,proposal in sorted(document['entries'].items()):
        if eid not in entries:raise ValueError(f'{eid}: proposal target is absent from canonical source data')
        if eid in reviews['entries'] or eid in decisions:raise ValueError(f'{eid}: existing manual judgment is protected')
        entry=entries[eid];facility=facilities[entry['facility_id']]
        if entry.get('reading_raw') or entry.get('reading') or entry.get('identity_review_required') or entry['status']!='pending' or facility['status']!='verified' or facility.get('source_conflicts') or facility.get('review_reason'):
            raise ValueError(f'{eid}: target is not an eligible missing-reading record')
        source=raw['collection'].get('sources',{}).get(facility['source_key'],{})
        problems=correction_problems(proposal,facility,entry,source)
        if problems:raise ValueError(f'{eid}: '+ '; '.join(problems))
        if set(proposal['changes'])!={'reading'}:raise ValueError(f'{eid}: reading research must preserve the acquired dictionary surface')
        if eid in corrections['entries']:
            old=corrections['entries'][eid]
            if old==proposal:unchanged.append(eid);continue
            if (not prefer_agency or not _agency_reading_refs(proposal,facility) or old.get('status')!='verified'
                or set(old.get('changes',{}))!={'reading'} or old.get('original')!=proposal['original']
                or old.get('expected_source_hash')!=proposal['expected_source_hash']):
                raise ValueError(f'{eid}: existing correction is protected')
            old_reading=old['changes']['reading'];new_reading=proposal['changes']['reading']
            if old_reading!=new_reading and _agency_reading_refs(old,facility):
                raise ValueError(f'{eid}: conflicting primary agency readings require review')
            combined=copy.deepcopy(proposal)
            combined['references'] += [r for r in old['references'] if r not in combined['references']]
            if old_reading!=new_reading:combined['superseded_secondary_reading']=old_reading
            elif old.get('superseded_secondary_reading'):combined['superseded_secondary_reading']=old['superseded_secondary_reading']
            combined['reason']+=' Primary agency reading takes precedence; previous inspected secondary references are retained.'
            if combined==old:unchanged.append(eid)
            else:corrections['entries'][eid]=combined;replaced.append(eid)
        else:
            corrections['entries'][eid]=proposal;added.append(eid)
    effective=apply_reviews(apply_corrections(raw,corrections),reviews)
    if decisions:effective=apply_decisions(effective,decisions)
    if aliases is not None:
        from njd.source_aliases import apply_source_aliases
        protected={e['id'] for e in effective['entries'] if decisions.get(e['id'],{}).get('status')=='pending'
            and decisions[e['id']].get('expected_source_hash')==e.get('source_hash')}
        effective=apply_source_aliases(effective,aliases,protected_pending_entry_ids=protected)
    problems=blocking_problems(effective)
    if problems:raise ValueError('proposed overlays fail canonical validation: '+str(problems[:5]))
    accepted={e['id'] for e in eligible(effective)}
    if set(added+unchanged+replaced)-accepted:raise ValueError('some proposed readings would remain ineligible after all judgments')
    return dict(added=len(added),replaced=len(replaced),unchanged=len(unchanged),entry_ids=sorted(added+unchanged+replaced))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('data'))
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--apply',action='store_true',help='write only after the complete proposal set passes validation')
    parser.add_argument('--prefer-agency',action='store_true',help='prefer bound primary agency readings to existing secondary reading corrections; preserve prior references')
    args=parser.parse_args(argv)
    result=import_proposals(args.data_dir,load_dataset(args.input),apply=args.apply,prefer_agency=args.prefer_agency)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
