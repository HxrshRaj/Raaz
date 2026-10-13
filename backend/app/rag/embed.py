"""Local, dependency-light embeddings.

`HashingEmbedder` concatenates hashed word 1-2-grams and character 3-5-grams (L2-normalised). It is a *lexical-
morphological* embedding — robust to inflection/typos — not a learned semantic model. The `Embedder` protocol lets
a hosted embedding model be swapped in without touching retrieval (documented in docs/RAG_AND_AGENTS.md).
"""

from __future__ import annotations

import re
from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

STOP = frozenset(
    "a an the and or of to in on at for with from by is are was were be been it its this that these those i you he she they "
    "we me my your his her their our as do did does not no yes so if then than but about into over any all".split()
)

# Small domain synonym map: widens recall for paraphrased questions without a learned model.
SYNONYMS = {
    "lied": "lie false claim contradict", "lying": "lie false claim contradict", "liar": "lie false claim",
    "killer": "murder culprit", "murderer": "murder culprit", "weapon": "paperweight blow",
    "alibi": "whereabouts where time", "clock": "time watch station", "slow": "late behind lag",
    "late": "delay delayed slow", "delayed": "delay late", "train": "kosi passenger departure",
    "motive": "reason why grudge money", "money": "financial funds payment cash rupees",
    "camera": "cctv footage dvr", "cctv": "camera footage dvr", "key": "lock locked deadbolt",
    "locked": "lock key deadbolt", "ticket": "platform stub journal", "phone": "call sms message mobile",
    "message": "sms text phone", "text": "sms message phone", "email": "mail message",
    "wrong": "slow lag behind incorrect", "heart": "heartbeat pulse watch", "stop": "last flat ended",
    "stopped": "last flat ended", "died": "death heartbeat last", "death": "heartbeat last died",
}


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())
    return [t for t in toks if t not in STOP and len(t) > 1]


def expand(text: str) -> str:
    toks = tokenize(text)
    extra = [SYNONYMS[t] for t in toks if t in SYNONYMS]
    return " ".join(toks + extra)


class Embedder(Protocol):
    dim: int
    name: str

    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashingEmbedder:
    name = "hashing-word12-char35-v1"

    def __init__(self, word_dim: int = 256, char_dim: int = 256) -> None:
        self._w = HashingVectorizer(n_features=word_dim, analyzer="word", ngram_range=(1, 2), alternate_sign=False,
                                    norm=None, lowercase=True, token_pattern=r"[a-z0-9][a-z0-9'\-]+")
        self._c = HashingVectorizer(n_features=char_dim, analyzer="char_wb", ngram_range=(3, 5), alternate_sign=False,
                                    norm=None, lowercase=True)
        self.dim = word_dim + char_dim

    def embed(self, texts: list[str]) -> np.ndarray:
        prepared = [expand(t) for t in texts]
        w = self._w.transform(prepared).toarray().astype(np.float32)
        c = self._c.transform(prepared).toarray().astype(np.float32)
        w = np.log1p(w)
        c = np.log1p(c)
        m = np.hstack([w, c * 0.6])
        n = np.linalg.norm(m, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return m / n


_default: HashingEmbedder | None = None


def get_embedder() -> HashingEmbedder:
    global _default
    if _default is None:
        _default = HashingEmbedder()
    return _default
