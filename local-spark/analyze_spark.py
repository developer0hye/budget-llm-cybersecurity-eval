#!/usr/bin/env python3
"""Knowledge-axis analysis with the five local DGX Spark models added to the five OpenRouter models.

Runs the unchanged knowledge/analyze.py (same outcome rules, same McNemar exact test, same
both-answered sensitivity check) on the union of the two result sets. Two things differ from a
plain `analyze.py` call, both by construction rather than by editing analyze.py:

- models.MODELS is extended with the local models before analyze.py is imported, so its
  Bonferroni alpha covers the whole 10-model family: 45 pairs per task, alpha = 0.05/45 = 0.0011.
  The OpenRouter-only results in the main README keep their own 10-pair family.
- load_rows() reads each model from whichever directory holds its jsonl: the committed
  knowledge/results_reasoning_{off,on}/ for OpenRouter models, local-spark/results_reasoning_*/
  for local ones.

Usage (repo root):
    python3 local-spark/analyze_spark.py off --json local-spark/analysis_reasoning_off.json
    python3 local-spark/analyze_spark.py on  --json local-spark/analysis_reasoning_on.json --compare-off
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "knowledge"))

import models  # noqa: E402

# Short name -> served model name, same keys as local-spark/run_local.py.
LOCAL_MODELS = {
    "gemma-4-12b": "gemma-4-12b-it",
    "gemma-4-26b-a4b": "gemma-4-26b-a4b-it",
    "gemma-4-31b": "gemma-4-31b-it",
    "qwen3.8-27b": "qwen38-27b",
    "qwen3.8-flash-next": "qwen38-flash-next-fp4-local",
}
# Only models whose run is complete for the requested condition take part; a partial run would
# change the family size and the per-model denominators.
models.MODELS.update(LOCAL_MODELS)

import analyze  # noqa: E402  (computes ALPHA from the extended MODELS at import)

UPSTREAM = {"off": ROOT / "knowledge/results_reasoning_off", "on": ROOT / "knowledge/results_reasoning_on"}
LOCAL = {"off": ROOT / "local-spark/results_reasoning_off", "on": ROOT / "local-spark/results_reasoning_on"}

_orig_load_rows = analyze.load_rows


def load_rows_union(run: Path) -> dict:
    cond = "on" if run.name.endswith("_on") else "off"
    rows = _orig_load_rows(UPSTREAM[cond])
    rows.update(_orig_load_rows(LOCAL[cond]))
    return rows


analyze.load_rows = load_rows_union


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cond", choices=["off", "on"])
    p.add_argument("--json", default=None)
    p.add_argument("--compare-off", action="store_true",
                   help="With cond=on: also run the within-model off vs on test for every model with both runs")
    args = p.parse_args()
    present = [n for n in LOCAL_MODELS if (LOCAL[args.cond] / f"{n}.jsonl").exists()]
    missing = [n for n in LOCAL_MODELS if n not in present]
    for n in missing:
        del models.MODELS[n]
    # analyze.ALPHA was fixed at import with all 10 models; recompute it for the models present.
    from math import comb
    analyze.ALPHA = 0.05 / comb(len(models.MODELS), 2)
    print(f"local models in this analysis ({args.cond}): {present}; not yet run: {missing}")
    sys.argv = ["analyze.py", str(UPSTREAM[args.cond])] + (["--json", args.json] if args.json else [])
    analyze.main()
    if args.compare_off and args.cond == "on":
        # analyze.main only runs this test when called on the off directory; call it directly so the
        # tables above stay the reasoning-on ones. Models lacking either run are skipped inside.
        res = analyze.compare_reasoning(UPSTREAM["off"], UPSTREAM["on"])
        if args.json:
            out = json.loads(Path(args.json).read_text())
            out["reasoning_off_vs_on"] = res
            Path(args.json).write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
