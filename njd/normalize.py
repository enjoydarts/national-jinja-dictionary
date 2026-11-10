"""Mechanical reading normalization. Never infer pronunciations."""
import re
import unicodedata


def compare_address_units(value: str) -> str:
    """Comparison only: explicit 0–99 Japanese numerals before address units.

    Do not touch locality names without these units or partially convert a
    larger/financial/nonstandard numeral. Stored addresses are never changed.
    """
    digits={c:i for i,c in enumerate('〇一二三四五六七八九')};digits['零']=0
    def number(match):
        raw,unit=match.groups()
        if raw.count('十')==1:
            tens,ones=raw.split('十')
            if (len(tens)>1 or len(ones)>1 or (tens and digits.get(tens,0)==0)
                or (ones and digits.get(ones,0)==0)):return match[0]
            result=(digits[tens] if tens else 1)*10+(digits[ones] if ones else 0)
        elif len(raw)==1 and raw in digits:result=digits[raw]
        else:return match[0]
        return str(result)+unit
    return re.sub(r'(?<![0-9０-９〇零一二三四五六七八九十百千万億兆壱弐参拾])([〇零一二三四五六七八九十]+)(丁目|条|番地|番|号)',number,value)


def normalize_reading(raw: str) -> str:
    # NFKC applies ONLY to readings, never names/addresses or dictionary surfaces.
    value = unicodedata.normalize('NFKC', raw)
    value = ''.join(chr(ord(c)-0x60) if '\u30a1' <= c <= '\u30f6' else c for c in value)
    if not value or not re.fullmatch(r'[ぁ-ゖゝゞー]+', value):
        raise ValueError('reading must contain full-width hiragana only; no inferred repairs')
    return value
