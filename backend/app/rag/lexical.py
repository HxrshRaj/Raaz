from __future__ import annotations

import math
from collections import Counter

from .embed import tokenize


class BM25:
    """Okapi BM25 over a small candidate set (built per query after ACL filtering)."""

    def __init__(self, docs: list[str], k1: float = 1.4, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.tokens = [tokenize(d) for d in docs]
        self.avg = (sum(len(t) for t in self.tokens) / len(self.tokens)) if self.tokens else 0.0
        df: Counter[str] = Counter()
        for t in self.tokens:
            df.update(set(t))
        n = len(self.tokens)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.tf = [Counter(t) for t in self.tokens]

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for i, tf in enumerate(self.tf):
            dl = len(self.tokens[i]) or 1
            s = 0.0
            for w in q:
                f = tf.get(w, 0)
                if not f:
                    continue
                s += self.idf.get(w, 0.0) * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avg or 1)))
            out.append(s)
        return out
