"""Tiny in-process metrics registry with Prometheus text exposition.

These are *measured* values from this process only (reset on restart); they are not estimates.
"""

from __future__ import annotations

import threading
from collections import defaultdict

_lock = threading.Lock()
_counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
_hist: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = defaultdict(lambda: [0.0, 0.0])  # [count, sum]
BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
_buckets: dict[tuple[str, tuple[tuple[str, str], ...]], list[int]] = defaultdict(lambda: [0] * len(BUCKETS))


def _k(name: str, labels: dict[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
    return name, tuple(sorted(labels.items()))


def inc(name: str, value: float = 1.0, **labels: str) -> None:
    with _lock:
        _counters[_k(name, labels)] += value


def observe(name: str, value: float, **labels: str) -> None:
    key = _k(name, labels)
    with _lock:
        h = _hist[key]
        h[0] += 1
        h[1] += value
        b = _buckets[key]
        for i, edge in enumerate(BUCKETS):
            if value <= edge:
                b[i] += 1


def _fmt(labels: tuple[tuple[str, str], ...], extra: str = "") -> str:
    parts = [f'{k}="{v}"' for k, v in labels]
    if extra:
        parts.append(extra)
    return "{" + ",".join(parts) + "}" if parts else ""


def render() -> str:
    lines: list[str] = []
    with _lock:
        for (name, labels), v in sorted(_counters.items()):
            lines.append(f"{name}{_fmt(labels)} {v}")
        for (name, labels), (count, total) in sorted(_hist.items()):
            for edge, n in zip(BUCKETS, _buckets[(name, labels)], strict=True):
                le = 'le="' + str(edge) + '"'
                lines.append(f"{name}_bucket{_fmt(labels, le)} {n}")
            inf = 'le="+Inf"'
            lines.append(f"{name}_bucket{_fmt(labels, inf)} {count}")
            lines.append(f"{name}_count{_fmt(labels)} {count}")
            lines.append(f"{name}_sum{_fmt(labels)} {total}")
    return "\n".join(lines) + "\n"


def reset() -> None:
    with _lock:
        _counters.clear()
        _hist.clear()
        _buckets.clear()
