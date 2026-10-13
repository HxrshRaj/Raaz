"""Operational commands.

    python -m app.cli seed          create tables (SQLite dev only), seed the case catalog + RAG corpus
    python -m app.cli train-ml      train + evaluate every ML component (writes artifacts, records experiments)
    python -m app.cli validate-case static integrity checks of every case package
    python -m app.cli rag-eval      retrieval quality on the hand-labelled query set
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="raaz")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed")
    t = sub.add_parser("train-ml")
    t.add_argument("--seed", type=int, default=7)
    t.add_argument("--no-torch", action="store_true")
    sub.add_parser("validate-case")
    sub.add_parser("rag-eval")
    a = ap.parse_args(argv)

    if a.cmd == "validate-case":
        from .cases.registry import list_cases
        from .cases.validate import validate_case

        bad = False
        for c in list_cases():
            errs = validate_case(c)
            print(f"{c.id}@{c.version}: {'OK' if not errs else errs}")
            bad |= bool(errs)
        return 1 if bad else 0

    from .main import init_database

    init_database()
    if a.cmd == "seed":
        print("catalog and RAG corpus are up to date")
    elif a.cmd == "train-ml":
        from .ml.train_all import _print, train_everything

        _print(train_everything(a.seed, include_torch=not a.no_torch))
    elif a.cmd == "rag-eval":
        from .db import SessionLocal
        from .rag.evaluate import evaluate

        with SessionLocal() as db:
            print(json.dumps(evaluate(db).as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
