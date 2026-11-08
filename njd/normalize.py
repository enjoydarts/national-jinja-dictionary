"""Mechanical reading normalization. Never infer pronunciations."""
import re
import unicodedata

def normalize_reading(raw: str) -> str:
    # NFKC applies ONLY to readings, never names/addresses or dictionary surfaces.
    value = unicodedata.normalize('NFKC', raw)
    value = ''.join(chr(ord(c)-0x60) if '\u30a1' <= c <= '\u30f6' else c for c in value)
    if not value or not re.fullmatch(r'[ぁ-ゖゝゞー]+', value):
        raise ValueError('reading must contain full-width hiragana only; no inferred repairs')
    return value
