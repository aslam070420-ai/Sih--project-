"""Shared IVR product dictionary for the India-wide FarmDirect catalogue.

Every canonical crop from :mod:`india_catalog` is recognised by its English
name. Common Indian aliases/transliterations stored in the catalogue are also
accepted. This keeps web marketplace, database seeding and IVR on one source
of truth instead of maintaining a tiny hand-written crop list.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

from india_catalog import CROP_CATALOG


def _clean(value: str) -> str:
    value = (value or "").casefold().strip()
    value = re.sub(r"[^\w\s\-\u0080-\uffff]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


PRODUCT_SYNONYMS: Dict[str, str] = {}
for _spec in CROP_CATALOG:
    PRODUCT_SYNONYMS[_clean(_spec.name)] = _spec.name
    for _alias in _spec.aliases:
        PRODUCT_SYNONYMS[_clean(_alias)] = _spec.name

# Longest aliases first prevents a generic token such as "rice" from winning
# before "basmati rice" or "red rice".
_SORTED_SYNONYMS = sorted(PRODUCT_SYNONYMS.items(), key=lambda kv: len(kv[0]), reverse=True)


def normalize_product(spoken: str) -> Optional[str]:
    """Return the canonical catalogue crop name, or ``None`` if unrecognised."""
    if not spoken:
        return None
    s = _clean(spoken)
    if not s:
        return None
    direct = PRODUCT_SYNONYMS.get(s)
    if direct:
        return direct
    padded = f" {s} "
    for syn, canon in _SORTED_SYNONYMS:
        if len(syn) >= 3 and f" {syn} " in padded:
            return canon
        # Native-script crop names can be attached to surrounding spoken text
        # without reliable whitespace from browser STT.
        if any(ord(ch) > 127 for ch in syn) and syn in s:
            return canon
    return None


def all_canonical_crops() -> list[str]:
    return sorted(spec.name for spec in CROP_CATALOG)
