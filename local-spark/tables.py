#!/usr/bin/env python3
"""Print the local-spark README tables from analysis_reasoning_{off,on}.json and runs.json.

Every number in local-spark/README.md's results section comes from this output, so the README
can be regenerated after each run instead of hand-copying figures.

Usage: python3 local-spark/tables.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = ["WMDP-cyber", "CTI-MCQ", "CTI-RCM"]
LOCAL = ["gemma-4-12b", "gemma-4-26b-a4b", "gemma-4-31b", "qwen3.8-27b", "qwen3.8-flash-next"]


def load(cond):
    p = HERE / f"analysis_reasoning_{cond}.json"
    return json.loads(p.read_text()) if p.exists() else None


def accuracy_table(cond):
    a = load(cond)
    if not a:
        print(f"(no reasoning-{cond} analysis yet)\n")
        return
    pm = a["per_model"]
    order = sorted(pm, key=lambda n: -sum(pm[n][t]["accuracy"] for t in TASKS))
    print(f"| Model (reasoning {cond}) | Where | WMDP-cyber | CTI-MCQ | CTI-RCM | Non-answers (trunc / unparsed) |")
    print("|---|---|---|---|---|---|")
    for n in order:
        where = "**Spark**" if n in LOCAL else "OpenRouter"
        cells = " | ".join(f"{pm[n][t]['accuracy']:.1f}%" for t in TASKS)
        trunc = sum(pm[n][t]["no_answer_truncated"] for t in TASKS)
        unp = sum(pm[n][t]["no_answer_unparsed"] for t in TASKS)
        name = f"**{n}**" if n in LOCAL else n
        print(f"| {name} | {where} | {cells} | {trunc} / {unp} |")
    alpha = None
    k = len(pm)
    if k > 1:
        alpha = 0.05 / (k * (k - 1) / 2)
    print(f"\nn = 996 / 2,500 / 1,000 per model. Accuracy = correct / all items. "
          f"{k} models, Bonferroni alpha = 0.05/{k * (k - 1) // 2} = {alpha:.4f} per task.\n")


def pairs_table(cond):
    a = load(cond)
    if not a:
        return
    print(f"Local model vs each OpenRouter model, reasoning {cond}: p (primary) and who is ahead; "
          f"** = below the Bonferroni alpha.\n")
    pm = a["per_model"]
    alpha = 0.05 / (len(pm) * (len(pm) - 1) / 2)
    present = [n for n in LOCAL if n in pm]
    others = sorted(n for n in pm if n not in LOCAL)
    print("| Local model | Task | " + " | ".join(others + [n for n in present]) + " |")
    print("|---|---|" + "---|" * (len(others) + len(present)))
    for m in present:
        for t in TASKS:
            cells = []
            for o in others + present:
                if o == m:
                    cells.append("—")
                    continue
                key = f"{m} vs {o}" if f"{m} vs {o}" in a["pairwise"][t] else f"{o} vs {m}"
                r = a["pairwise"][t][key]["primary"]
                # b counts items the left-hand model got right and the right-hand model got wrong.
                left = key.split(" vs ")[0]
                m_ahead = (r["b"] > r["c"]) == (left == m)
                sign = "+" if m_ahead else "−"
                star = "**" if r["p"] < alpha else ""
                ptxt = "<0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"
                cells.append(f"{sign} {ptxt}{star}")
            print(f"| {m} | {t} | " + " | ".join(cells) + " |")
    print("\n`+` = the local model got more of the discordant items right, `−` = fewer.\n")


def runs_table():
    p = HERE / "runs.json"
    if not p.exists():
        return
    runs = json.loads(p.read_text())
    print("| Model | Reasoning | Wall-clock | Server sequences | Client concurrency |")
    print("|---|---|---|---|---|")
    for r in runs:
        print(f"| {r['model']} | {r['reasoning']} | {r['wall_s'] / 3600:.2f} h | {r['server_seqs']} | {r['client_concurrency']} |")
    print()


if __name__ == "__main__":
    for c in ("on", "off"):
        accuracy_table(c)
        pairs_table(c)
    runs_table()
