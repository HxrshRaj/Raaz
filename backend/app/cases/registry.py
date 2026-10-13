"""Server-side registry of case packages. Never exposed through an API."""

from __future__ import annotations

from functools import lru_cache

from .base import CaseSpec


@lru_cache
def _all() -> dict[str, CaseSpec]:
    from .aakhri_gaadi import build

    cases = [build()]
    return {c.id: c for c in cases}


def get_case(case_id: str) -> CaseSpec:
    try:
        return _all()[case_id]
    except KeyError as e:
        raise KeyError(f"unknown case {case_id}") from e


def list_cases() -> list[CaseSpec]:
    return list(_all().values())
