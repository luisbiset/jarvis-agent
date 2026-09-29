"""Similaridade semântica local leve, determinística e sem dependências externas."""
from __future__ import annotations
import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-zà-ÿ0-9_]{2,}", re.I)
def _features(value: str) -> Counter[str]:
    normalized = " ".join(TOKEN.findall(value.casefold()))
    grams = [normalized[index:index + 3] for index in range(max(0, len(normalized) - 2))]
    return Counter(grams)
def cosine(left: str, right: str) -> float:
    a, b = _features(left), _features(right)
    if not a or not b: return 0.0
    dot = sum(value * b.get(key, 0) for key, value in a.items())
    denominator = math.sqrt(sum(value * value for value in a.values()) * sum(value * value for value in b.values()))
    return round(dot / denominator, 6) if denominator else 0.0
