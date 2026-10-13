"""Explicit time rules. The clock offset is encoded in the case package — never improvised by an LLM."""

from __future__ import annotations

import re

from ..cases.base import CaseSpec

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")


def parse_seconds(t: str) -> int:
    m = _TIME_RE.match(t.strip())
    if not m:
        raise ValueError(f"bad time {t!r}")
    h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    if not (0 <= h < 24 and 0 <= mi < 60 and 0 <= s < 60):
        raise ValueError(f"bad time {t!r}")
    return h * 3600 + mi * 60 + s


def fmt_seconds(sec: int, with_seconds: bool = False) -> str:
    sec %= 86400
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if with_seconds or s else f"{h:02d}:{m:02d}"


def clock_known(case: CaseSpec, held: set[str] | frozenset[str]) -> bool:
    return any(k in held for k in case.clock.discovered_by)


def to_rt_seconds(case: CaseSpec, clock: str, time_str: str) -> int:
    """Convert a time on `clock` ('RT' or 'ST') to real-time seconds. ST + offset = RT."""
    sec = parse_seconds(time_str)
    if clock == "ST":
        sec += case.clock.st_to_rt_minutes * 60
    return sec


def effective_held(case: CaseSpec, held: set[str] | frozenset[str]) -> set[str]:
    """Treat the clock rule as 'held' (ev_clock_slow) when any independent source revealed it."""
    out = set(held)
    if clock_known(case, held):
        out.add("ev_clock_slow")
    return out
