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


def sensitivity_flips(cond):
    """Pairs involving a local model whose verdict differs between all items and both-answered items."""
    a = load(cond)
    if not a:
        return
    k = len(a["per_model"])
    alpha = 0.05 / (k * (k - 1) / 2)
    flips = []
    for t in TASKS:
        for pair, r in a["pairwise"][t].items():
            if not any(m in pair.split(" vs ") for m in LOCAL):
                continue
            prim, both = r["primary"], r["both_answered"]
            if (prim["p"] < alpha) != (both["p"] < alpha):
                flips.append(f"- {t}, {pair}: all items p = {prim['p']:.4f}, both answered p = {both['p']:.4f} "
                             f"(n = {both['n']:,})")
    print(f"Verdicts that change on both-answered items (reasoning {cond}, alpha = {alpha:.4f}):")
    print("\n".join(flips) if flips else "- none")
    print()


def runs_table():
    p = HERE / "runs.json"
    if not p.exists():
        return
    runs = json.loads(p.read_text())
    print("| Model | Reasoning | Box | Wall-clock | Server sequences | Client concurrency |")
    print("|---|---|---|---|---|---|")
    for r in runs:
        print(f"| {r['model']} | {r['reasoning']} | {r.get('host', 'spark-1')} | {r['wall_s'] / 3600:.2f} h | "
              f"{r['server_seqs']} | {r['client_concurrency']} |")
    print()


def within_model_table(cond, key, title, left, right):
    """Within-model McNemar tables stored by analyze_spark.py (off vs on, greedy vs card)."""
    a = load(cond)
    if not a or key not in a:
        return
    res = a[key]
    models = sorted({m for t in res.values() for m in t if m in LOCAL})
    if not models:
        return
    print(f"{title}\n")
    print(f"| Model | Task | {left} | {right} | b / c | p | Truncated ({right}) |")
    print("|---|---|---|---|---|---|---|")
    for m in models:
        for t in TASKS:
            r = res.get(t, {}).get(m)
            if not r:
                continue
            ptxt = "<0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"
            print(f"| {m} | {t} | {r['acc_off']:.1f}% | {r['acc_on']:.1f}% | {r['b']} / {r['c']} | {ptxt} | "
                  f"{r['truncated_on']} |")
    print(f"\nb = right only under {left}, c = right only under {right}; n = all items of the task.\n")


def block(name):
    """Markdown for one README block, captured from the printers above."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        if name in ("off", "on", "on_card"):
            accuracy_table(name)
            pairs_table(name)
            sensitivity_flips(name)
        elif name == "within":
            within_model_table("on", "reasoning_off_vs_on", "Reasoning off vs on (greedy), local models",
                               "off", "on (greedy)")
            within_model_table("on_card", "greedy_vs_card_sampling",
                               "Greedy vs model-card sampling, reasoning on", "greedy", "card sampling")
            within_model_table("on_card", "reasoning_off_vs_on",
                               "Reasoning off vs on (card sampling), local models", "off", "on (card)")
        elif name == "runs":
            runs_table()
    return buf.getvalue().rstrip() + "\n"


BLOCKS = ("off", "on", "on_card", "within", "runs")


def update_readme():
    """Rewrite every <!-- tables:NAME --> ... <!-- /tables:NAME --> block in README.md in place."""
    import re
    p = HERE / "README.md"
    s = p.read_text(encoding="utf-8")
    for name in BLOCKS:
        pat = re.compile(rf"(<!-- tables:{name} -->\n).*?(<!-- /tables:{name} -->)", re.S)
        if not pat.search(s):
            raise SystemExit(f"README.md has no tables:{name} block")
        s = pat.sub(lambda m: m.group(1) + block(name) + m.group(2), s)
    p.write_text(s, encoding="utf-8", newline="\n")
    print(f"updated {len(BLOCKS)} blocks in {p}")


if __name__ == "__main__":
    import sys
    if "--update-readme" in sys.argv:
        update_readme()
    else:
        for name in BLOCKS:
            print(block(name))
