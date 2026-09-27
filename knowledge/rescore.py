#!/usr/bin/env python3
"""Re-extract every logged response with the current extractor and rewrite the rows.

Usage:
    python3 knowledge/rescore.py knowledge/results_reasoning_off knowledge/results_reasoning_on

No model is called: `pred`, `outcome` and `correct` are recomputed from the
stored `response` and `finish_reason`. A row whose outcome or pred changes
keeps the previous values as `pred_v1` / `outcome_v1` (set once, on the first
rescore), so the v1 -> v2 transitions stay recomputable from the committed
logs. summary.json is regenerated from the rewritten rows.
"""

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "knowledge"))
from run_knowledge import MODELS, extract_answer, outcome, summarize  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_dirs", nargs="+")
    args = p.parse_args()
    for run in map(Path, args.run_dirs):
        for name in MODELS:
            path = run / f"{name}.jsonl"
            if not path.exists():
                continue
            rows, moves = [], collections.Counter()
            for r in map(json.loads, path.open()):
                if not r["error"]:
                    pred = extract_answer(r["task"], r["response"])
                    oc = outcome(pred, r["gold"], r["finish_reason"])
                    if (pred, oc) != (r["pred"], r["outcome"]):
                        r.setdefault("pred_v1", r["pred"])
                        r.setdefault("outcome_v1", r["outcome"])
                        moves[(r["task"], r["outcome"], oc)] += 1
                        r["pred"], r["outcome"], r["correct"] = pred, oc, oc == "correct"
                rows.append(r)
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            for (task, a, b), n in sorted(moves.items()):
                print(f"{run.name:24s} {name:20s} {task:10s} {a} -> {b}: {n}")
        summarize(run, [n for n in MODELS if (run / f"{n}.jsonl").exists()])


if __name__ == "__main__":
    main()
