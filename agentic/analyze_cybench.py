#!/usr/bin/env python3
"""Summarise Cybench runs from the Inspect logs written by run_cybench.py.

Usage:
    python3 agentic/analyze_cybench.py agentic/pilot
    python3 agentic/analyze_cybench.py agentic/logs --estimate 39x3

Per model: samples, solved, cost-cap hits, sample errors (infrastructure;
never scored as model failures), providers seen, and spend. With
--estimate NxE, extrapolates a full run of N challenges x E epochs from the
mean cost per sample -- a lower bound when the cap truncated samples.
"""

import argparse
import collections
import glob
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from models import MODELS  # noqa: E402

from inspect_ai.log import read_eval_log  # noqa: E402


def sample_row(s) -> dict:
    usage = next(iter(s.model_usage.values()), None) if s.model_usage else None
    providers = collections.Counter()
    for e in s.events:
        if e.event == "model" and e.call and isinstance(e.call.response, dict):
            providers[e.call.response.get("provider")] += 1
    score = next(iter(s.scores.values())).value if s.scores else None
    return {
        "id": str(s.id),
        "epoch": s.epoch,
        "solved": score == "C",
        "limit": s.limit.type if s.limit else None,
        "error": s.error.message[:200] if s.error else None,
        "cost": (usage.total_cost or 0.0) if usage else 0.0,
        "turns": sum(e.event == "model" for e in s.events),
        "providers": providers,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("log_root")
    p.add_argument("--estimate", default=None, help="NxE, e.g. 39x3")
    args = p.parse_args()
    root = Path(args.log_root)
    total = 0.0
    print(f"{'model':22s} {'n':>3s} {'solved':>7s} {'cap':>4s} {'err':>4s} {'$/sample':>9s} {'$ total':>8s}  providers")
    for name in MODELS:
        files = sorted(glob.glob(str(root / name / "**" / "*.eval"), recursive=True))
        if not files:
            continue
        # Merge across log files (infra-error and timeout re-runs): one row per
        # (sample, epoch), taken from the NEWEST run that produced a non-error
        # result. Never "best of runs" -- preferring a solved attempt would give
        # re-run samples pass@2. Files are ordered by the ISO timestamp that
        # starts every Inspect log filename.
        best = {}
        for f in sorted(files, key=lambda x: Path(x).name):
            for s in (read_eval_log(f).samples or []):
                r = sample_row(s)
                key = (r["id"], r["epoch"])
                prev = best.get(key)
                if prev is None or not r["error"] or prev["error"]:
                    best[key] = r
        rows = list(best.values())
        cost = sum(r["cost"] for r in rows)
        total += cost
        provs = sum((r["providers"] for r in rows), collections.Counter())
        n = len(rows)
        line = (f"{name:22s} {n:3d} {sum(r['solved'] for r in rows):7d} "
                f"{sum(r['limit'] == 'cost' for r in rows):4d} {sum(bool(r['error']) for r in rows):4d} "
                f"{cost / n if n else 0:9.4f} {cost:8.3f}  {dict(provs)}")
        if args.estimate:
            nc, ne = map(int, args.estimate.lower().split("x"))
            line += f"  -> est. {args.estimate}: ${cost / n * nc * ne:.2f}" if n else ""
        print(line)
        for r in rows:
            flag = "SOLVED" if r["solved"] else ("CAP" if r["limit"] == "cost" else ("ERROR" if r["error"] else "fail"))
            print(f"    {r['id']:36s} e{r['epoch']} {flag:6s} ${r['cost']:.4f} turns={r['turns']}"
                  + (f"  {r['error']}" if r["error"] else ""))
    print(f"total spend in {root}: ${total:.3f}")


if __name__ == "__main__":
    main()
