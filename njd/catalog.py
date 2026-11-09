"""Code-only registry of explicit official-source adapters."""
import importlib
from njd.adapters import gunma

def collect_gunma(client,limit=None):
    page=client.fetch(gunma.URL)
    data=gunma.parse(page.text,page.fetched_at,page.sha256,limit=limit)
    data['collection']['source_key']='gunma'
    for f in data['facilities']: f['source_key']='gunma'
    return data

def registry():
    result={'gunma':dict(code='10',prefecture='群馬県',agency='群馬県神社庁',collect=collect_gunma)}
    for name in ('north','central','south','mie','niigata','gifu','hyogo'):
        try: module=importlib.import_module('njd.adapters.'+name)
        except ModuleNotFoundError as exc:
            if exc.name=='njd.adapters.'+name: continue
            raise
        for key,spec in module.REGISTRY.items():
            if key in result: raise ValueError('duplicate registered source: '+key)
            result[key]=spec
    return result
