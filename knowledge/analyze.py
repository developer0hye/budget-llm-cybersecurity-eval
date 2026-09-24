#!/usr/bin/env python3
"""Recompute every knowledge-axis number from the per-item jsonl logs.

Usage:
    python3 knowledge/analyze.py knowledge/results_reasoning_off
    python3 knowledge/analyze.py knowledge/results_reasoning_on
    python3 knowledge/analyze.py knowledge/results_reasoning_off \
        --compare-on knowledge/results_reasoning_on --json knowledge/analysis.json

Per model x task, every item has one outcome: correct, wrong (answered
incorrectly), no_answer_truncated (hit max_tokens -- never an answer), or
no_answer_unparsed (finished without an extractable answer). Primary
accuracy = correct / all items (pre-registered); accuracy_of_answered =
correct / (correct + wrong). Also: reasoning-engaged row counts. Per task: all 10 pairwise
McNemar exact tests on the items both models were logged for, with a
Bonferroni threshold of 0.05/10 (the family is one task). Sensitivity: the
same tests restricted to items where both models produced an answer.
"""

import argparse
import itertools
import json
import sys
from collections import Counter
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from models import MODELS, REASONING_MANDATORY  # noqa: E402
sys.path.insert(0, str(ROOT / "knowledge"))
from run_knowledge import OUTCOMES, outcome  # noqa: E402

TASKS = ["WMDP-cyber", "CTI-MCQ", "CTI-RCM"]
ALPHA = 0.05 / comb(len(MODELS), 2)


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


def reasoning_tokens(r) -> int:
    return (((r.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens")) or 0


def load_rows(run: Path) -> dict:
    rows = {}
    for name in MODELS:
        path = run / f"{name}.jsonl"
        if path.exists():
            rows[name] = {}
            for r in map(json.loads, path.open()):
                if r["error"]:
                    continue
                # Rows logged before `outcome` existed (the pilot) are re-derived
                # with the same rule, so a truncated row is never an answer.
                r["outcome"] = r.get("outcome") or outcome(r["pred"], r["gold"], r["finish_reason"])
                r["correct"] = r["outcome"] == "correct"
                rows[name][(r["task"], r["item"])] = r
    return rows


def compare_reasoning(off_dir: Path, on_dir: Path) -> dict:
    """Within-model off vs on, paired on the items both runs logged.

    Family: every model whose endpoint allows reasoning off (GLM 5.3 Flash
    does not) x 3 tasks; Bonferroni over that family.
    """
    off, on = load_rows(off_dir), load_rows(on_dir)
    toggleable = [n for n in MODELS if MODELS[n] not in REASONING_MANDATORY and n in off and n in on]
    alpha = 0.05 / (len(toggleable) * len(TASKS))
    print(f"\n=== reasoning off vs on, within model (Bonferroni alpha = {alpha:.4f}, "
          f"{len(toggleable)} models x {len(TASKS)} tasks) ===")
    print("b = right only with reasoning off, c = right only with reasoning on")
    res = {}
    for task in TASKS:
        for n in toggleable:
            common = sorted(k for k in off[n] if k[0] == task and k in on[n])
            if not common:
                continue
            b = sum(off[n][k]["correct"] and not on[n][k]["correct"] for k in common)
            c = sum(on[n][k]["correct"] and not off[n][k]["correct"] for k in common)
            acc_off = sum(off[n][k]["correct"] for k in common) / len(common) * 100
            acc_on = sum(on[n][k]["correct"] for k in common) / len(common) * 100
            trunc_on = sum(on[n][k]["outcome"] == "no_answer_truncated" for k in common)
            p = mcnemar_exact(b, c)
            flag = "**" if p < alpha else ("*" if p < 0.05 else "")
            res.setdefault(task, {})[n] = {"n": len(common), "acc_off": round(acc_off, 2), "acc_on": round(acc_on, 2),
                                          "b": b, "c": c, "p": p, "truncated_on": trunc_on}
            print(f"  {task:11s} {n:20s} n={len(common):4d} off {acc_off:5.1f}% -> on {acc_on:5.1f}% "
                  f"b={b:3d} c={c:3d} p={p:.4f}{flag:2s} (on truncated: {trunc_on})")
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_dir")
    p.add_argument("--compare-on", default=None, help="Reasoning-on run dir for the within-model off vs on test")
    p.add_argument("--json", default=None)
    args = p.parse_args()
    rows = load_rows(Path(args.run_dir))
    out = {"per_model": {}, "pairwise": {}, "baselines": {}}

    for task in TASKS:
        task_rows = {n: {k[1]: r for k, r in rs.items() if k[0] == task} for n, rs in rows.items()}
        task_rows = {n: rs for n, rs in task_rows.items() if rs}
        if not task_rows:
            continue
        print(f"\n=== {task} ===")
        golds = Counter(r["gold"] for rs in task_rows.values() for r in rs.values())
        top, top_n = golds.most_common(1)[0]
        base = top_n / sum(golds.values()) * 100
        out["baselines"][task] = {"majority_label": top, "majority_accuracy": round(base, 2)}
        print(f"majority-label baseline: always '{top}' = {base:.1f}%")
        print(f"{'model':22s} {'n':>5s} {'acc':>7s} {'acc|ans':>8s} {'correct':>8s} {'wrong':>6s} "
              f"{'trunc':>6s} {'unparsed':>9s} {'reason>0':>9s}")
        for n, rs in sorted(task_rows.items(), key=lambda kv: -sum(r["correct"] for r in kv[1].values()) / len(kv[1])):
            v = list(rs.values())
            counts = {o: sum(r["outcome"] == o for r in v) for o in OUTCOMES}
            n_ans = counts["correct"] + counts["wrong"]
            acc = counts["correct"] / len(v) * 100
            acc_ans = counts["correct"] / n_ans * 100 if n_ans else float("nan")
            stats = {
                "n": len(v), "accuracy": round(acc, 2), "accuracy_of_answered": round(acc_ans, 2), **counts,
                "reasoning_rows": sum(reasoning_tokens(r) > 0 for r in v),
                "cost_usd": round(sum((r.get("usage") or {}).get("cost") or 0 for r in v), 4),
                "providers": dict(Counter(r.get("provider") for r in v)),
            }
            out["per_model"].setdefault(n, {})[task] = stats
            print(f"{n:22s} {stats['n']:5d} {acc:6.1f}% {acc_ans:7.1f}% {counts['correct']:8d} {counts['wrong']:6d} "
                  f"{counts['no_answer_truncated']:6d} {counts['no_answer_unparsed']:9d} {stats['reasoning_rows']:9d}")

        print(f"pairwise McNemar (Bonferroni alpha = {ALPHA:.4f}); b = A right & B wrong, c = reverse")
        for a, b_ in itertools.combinations(sorted(task_rows), 2):
            common = sorted(set(task_rows[a]) & set(task_rows[b_]))
            answered = ("correct", "wrong")
            both_ans = [i for i in common
                        if task_rows[a][i]["outcome"] in answered and task_rows[b_][i]["outcome"] in answered]

            def test(items):
                b = sum(task_rows[a][i]["correct"] and not task_rows[b_][i]["correct"] for i in items)
                c = sum(task_rows[b_][i]["correct"] and not task_rows[a][i]["correct"] for i in items)
                return {"n": len(items), "b": b, "c": c, "p": mcnemar_exact(b, c)}

            prim, sens = test(common), test(both_ans)
            out["pairwise"].setdefault(task, {})[f"{a} vs {b_}"] = {"primary": prim, "both_answered": sens}
            flag = "**" if prim["p"] < ALPHA else ("*" if prim["p"] < 0.05 else "")
            print(f"  {a:20s} vs {b_:20s} n={prim['n']:4d} b={prim['b']:3d} c={prim['c']:3d} "
                  f"p={prim['p']:.4f}{flag:2s} | both-answered n={sens['n']} p={sens['p']:.4f}")

    if args.compare_on:
        out["reasoning_off_vs_on"] = compare_reasoning(Path(args.run_dir), Path(args.compare_on))

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
