#!/usr/bin/env python3
"""Summarise Cybench runs from the Inspect logs written by run_cybench.py.

Usage:
    python3 agentic/analyze_cybench.py agentic/logs
    python3 agentic/analyze_cybench.py agentic/logs --manifest agentic/manifest.jsonl --json agentic/analysis.json
    python3 agentic/analyze_cybench.py agentic/pilot --estimate 39x3

Per model: solved with a 95% Wilson CI, how every unsolved sample ended
(cost / time / working limit, wrong submissions, no submission), sample
errors (infrastructure; never scored as model failures), which run protocol
each scored sample came from, scored-trajectory and recorded-attempt cost, and
the solve rate under lower cost caps. Then all pairwise McNemar exact tests.

Merge rule: one row per (sample, epoch), taken from the NEWEST run that
produced a non-error result -- never "best of runs", which would give re-run
samples pass@2. When a later re-run of a sample errored, the older result is
kept and the manifest marks the replacement as incomplete; the protocol
column then shows that the scored row did not run under the final protocol.
"""

import argparse
import collections
import glob
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from models import MODELS  # noqa: E402

from inspect_ai.log import read_eval_log  # noqa: E402

# The protocol the README reports (run_cybench.py defaults). Earlier logs used
# attempt_timeout 300 s and no wall-clock time_limit.
FINAL_PROTOCOL = {"attempt_timeout": 900, "time_limit": 3600, "working_limit": 3600, "cost_limit": 2.1}
BUDGET_CAPS = [0.10, 0.25, 0.50, 0.80, 1.00, 1.50, 2.10]


def protocol_of(log) -> dict:
    gen = log.plan.config if log.plan else None
    return {
        "attempt_timeout": getattr(gen, "attempt_timeout", None),
        "stream_idle_timeout": getattr(gen, "stream_idle_timeout", None),
        "time_limit": log.eval.config.time_limit,
        "working_limit": log.eval.config.working_limit,
        "cost_limit": log.eval.config.cost_limit,
    }


def protocol_id(p: dict) -> str:
    return "final" if all(p.get(k) == v for k, v in FINAL_PROTOCOL.items()) else (
        f"attempt_timeout={p['attempt_timeout']},time_limit={p['time_limit']}")


def sample_row(s, log_file: str, proto: dict) -> dict:
    usage = next(iter(s.model_usage.values()), None) if s.model_usage else None
    providers = collections.Counter()
    call_timeouts = 0
    for e in s.events:
        if e.event == "model":
            if e.call and isinstance(e.call.response, dict):
                providers[e.call.response.get("provider")] += 1
            call_timeouts += "timeout" in str(getattr(e, "error", "") or "").lower()
    submissions = sum(e.event == "tool" and e.function == "submit" for e in s.events)
    score = next(iter(s.scores.values())).value if s.scores else None
    limit = s.limit.type if s.limit else None
    solved = score == "C"
    if s.error:
        end = "error"
    elif solved:
        end = "solved"
    elif limit:
        end = f"{limit}_limit"
    else:
        end = "wrong_submissions" if submissions else "no_submission"
    return {
        "id": str(s.id),
        "epoch": s.epoch,
        "solved": solved,
        "end": end,
        "limit": limit,
        "error": s.error.message[:200] if s.error else None,
        "cost": (usage.total_cost or 0.0) if usage else 0.0,
        "turns": sum(e.event == "model" for e in s.events),
        "submissions": submissions,
        "call_timeouts": call_timeouts,
        "total_time": round(s.total_time or 0),
        "working_time": round(s.working_time or 0),
        "providers": providers,
        "log": log_file,
        "protocol": protocol_id(proto),
    }


def mcnemar_exact(b: int, c: int) -> float:
    """Same test as knowledge/analyze.py (not imported: that module needs the knowledge-axis deps)."""
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def load_model(root: Path, name: str):
    files = sorted(glob.glob(str(root / name / "**" / "*.eval"), recursive=True), key=lambda x: Path(x).name)
    best, history, recorded_cost = {}, collections.defaultdict(list), 0.0
    for f in files:  # ISO timestamp that starts every Inspect log filename = run order
        log = read_eval_log(f)
        proto = protocol_of(log)
        for s in log.samples or []:
            r = sample_row(s, str(Path(f).relative_to(ROOT)) if Path(f).is_absolute() else f, proto)
            recorded_cost += r["cost"]
            key = (r["id"], r["epoch"])
            history[key].append(r)
            prev = best.get(key)
            if prev is None or not r["error"] or prev["error"]:
                best[key] = r
    manifest = []
    for key, r in best.items():
        runs = history[key]
        later = runs[runs.index(r) + 1:]
        manifest.append({
            "model": name, "challenge": key[0], "epoch": key[1], "selected_log": r["log"],
            "protocol_id": r["protocol"], "end": r["end"], "runs": len(runs),
            # a newer run of this sample exists but errored, so the older result stands
            "replacement_complete": not later,
            "replacement_failures": [x["error"][:80] for x in later],
        })
    return best, manifest, recorded_cost


def main():
    p = argparse.ArgumentParser()
    p.add_argument("log_root")
    p.add_argument("--estimate", default=None, help="NxE, e.g. 39x3")
    p.add_argument("--manifest", default=None, help="write one JSON line per scored (model, challenge, epoch)")
    p.add_argument("--json", default=None)
    p.add_argument("-v", "--verbose", action="store_true", help="list every sample")
    args = p.parse_args()
    root = Path(args.log_root)
    per_model, manifests, out = {}, [], {"models": {}, "pairwise": {}}
    ends = ["solved", "wrong_submissions", "no_submission", "time_limit", "working_limit", "cost_limit", "error"]
    print(f"{'model':22s} {'solved':>7s} {'rate':>6s} {'95% CI':>12s}  " + " ".join(f"{e[:10]:>10s}" for e in ends[1:])
          + f" {'$scored':>8s} {'$recorded':>9s}")
    for name in MODELS:
        if not glob.glob(str(root / name / "**" / "*.eval"), recursive=True):
            continue
        best, manifest, recorded = load_model(root, name)
        rows = list(best.values())
        per_model[name] = {(r["id"], r["epoch"]): r["solved"] for r in rows}
        manifests += manifest
        n, k = len(rows), sum(r["solved"] for r in rows)
        lo, hi = wilson(k, n)
        cnt = collections.Counter(r["end"] for r in rows)
        scored = sum(r["cost"] for r in rows)
        print(f"{name:22s} {k:3d}/{n:<3d} {k / n * 100:5.1f}% {lo * 100:5.1f}-{hi * 100:5.1f}%  "
              + " ".join(f"{cnt[e]:10d}" for e in ends[1:]) + f" {scored:8.2f} {recorded:9.2f}")
        protos = collections.Counter(r["protocol"] for r in rows)
        incomplete = [m for m in manifest if not m["replacement_complete"]]
        over_time = [r for r in rows if r["total_time"] > FINAL_PROTOCOL["time_limit"] and r["solved"]]
        curve = {cap: sum(r["solved"] and r["cost"] <= cap for r in rows) for cap in BUDGET_CAPS}
        print(f"    protocols of scored rows: {dict(protos)}")
        if incomplete:
            print(f"    replacement incomplete (newer re-run errored, older result scored): "
                  f"{len(incomplete)} -> " + ", ".join(f"{m['challenge'].replace(' (hard)', '')}={m['end']}"
                                                       for m in incomplete))
        if over_time:
            print(f"    solved but ran > {FINAL_PROTOCOL['time_limit']} s wall-clock (no time_limit in that run): "
                  + ", ".join(f"{r['id'].replace(' (hard)', '')} {r['total_time']} s" for r in over_time))
        print("    solved under cost cap: " + "  ".join(f"${c:.2f}:{v}" for c, v in curve.items()))
        if args.estimate and n:
            nc, ne = map(int, args.estimate.lower().split("x"))
            print(f"    est. {args.estimate}: ${scored / n * nc * ne:.2f}")
        if args.verbose:
            for r in rows:
                print(f"      {r['id']:36s} e{r['epoch']} {r['end']:17s} ${r['cost']:.4f} turns={r['turns']} "
                      f"t={r['total_time']}s timeouts={r['call_timeouts']} {r['protocol']}"
                      + (f"  {r['error']}" if r["error"] else ""))
        out["models"][name] = {
            "n": n, "solved": k, "solve_rate": k / n, "wilson95": [lo, hi], "ends": dict(cnt),
            "scored_trajectory_cost": scored, "recorded_attempt_cost": recorded,
            "protocols": dict(protos), "replacement_incomplete": len(incomplete),
            "solved_over_final_time_limit": [r["id"] for r in over_time],
            "budget_curve": {str(c): v for c, v in curve.items()},
        }

    alpha = 0.05 / max(1, math.comb(len(per_model), 2))
    print(f"\npairwise McNemar exact (Bonferroni alpha = {alpha:.4f}); b = only first solved, c = only second")
    for a, b in itertools.combinations(per_model, 2):
        keys = sorted(set(per_model[a]) & set(per_model[b]))
        bb = sum(per_model[a][k] and not per_model[b][k] for k in keys)
        cc = sum(per_model[b][k] and not per_model[a][k] for k in keys)
        pv = mcnemar_exact(bb, cc)
        out["pairwise"][f"{a} vs {b}"] = {"n": len(keys), "b": bb, "c": cc, "p": pv}
        print(f"  {a:20s} vs {b:20s} n={len(keys)} b={bb:2d} c={cc:2d} p={pv:.4f}{'**' if pv < alpha else ''}")

    if args.manifest:
        Path(args.manifest).write_text("".join(json.dumps(m) + "\n" for m in manifests))
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
