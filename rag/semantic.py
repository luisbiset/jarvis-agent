"""Similaridade semântica local leve, determinística e sem dependências externas."""
from __future__ import annotations
import math
import re
import hashlib
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


class LocalEmbeddingProvider:
    """Provider local determinístico; não transmite texto nem exige dependências externas."""
    model_id = "local-chargram-v1"
    dimensions = 256

    def _embed(self, value: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for gram, count in _features(value).items():
            index = int.from_bytes(hashlib.sha256(gram.encode("utf-8")).digest()[:4], "big") % self.dimensions
            vector[index] += float(count)
        norm = math.sqrt(sum(item * item for item in vector)) or 1.0
        return [round(item / norm, 8) for item in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
