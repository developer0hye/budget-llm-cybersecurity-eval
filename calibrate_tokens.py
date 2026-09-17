#!/usr/bin/env python3
"""Find the smallest max_tokens budget that avoids truncation (finish_reason
"length" with empty content) for each model, with reasoning on.

For each model, runs a probe set of questions at each candidate budget in
--budgets (ascending) and records, per budget: how many probe questions got
truncated, and the actual completion_tokens used (including the hidden
reasoning_tokens portion) for the ones that succeeded. This gives both a
recommended max_tokens (the smallest budget with zero truncations) and the
underlying token-usage distribution, so the choice is documented instead of
guessed.

Usage:
    export OPENROUTER_API_KEY=sk-or-...
    python3 calibrate_tokens.py --probe-size 30 --budgets 250 500 1000 2000 4000 8000

Writes a full record to calibration/report.json and a human-readable
calibration/report.md.
"""

import argparse
import asyncio
import json
import os
import random
import sys
import time
from pathlib import Path

import aiohttp

from run_eval import MODELS, REASONING_MANDATORY, OPENROUTER_URL, build_prompt, extract_letter

DEFAULT_BUDGETS = [250, 500, 1000, 2000, 4000, 8000]


async def probe_call(session: aiohttp.ClientSession, model_id: str, prompt: str, api_key: str, max_tokens: int):
    """Single call at a fixed max_tokens. Returns a dict with outcome + usage.
    Does its own light retrying only for 429/network errors -- a truncation
    at this budget is a real data point, not something to retry away.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "reasoning": {"enabled": True},
    }
    last_err = "exhausted retries"
    for attempt in range(5):
        try:
            async with session.post(
                OPENROUTER_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=90)
            ) as resp:
                if resp.status == 429:
                    last_err = "429 Too Many Requests"
                    await asyncio.sleep(3 * (attempt + 1) + random.uniform(0, 1))
                    continue
                resp.raise_for_status()
                data = await resp.json()
                choice = data["choices"][0]
                content = choice["message"].get("content")
                usage = data.get("usage", {})
                letter = extract_letter(content) if content else None
                return {
                    "truncated": content is None and choice.get("finish_reason") == "length",
                    "finish_reason": choice.get("finish_reason"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens"),
                    "letter": letter,
                    "error": None,
                }
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            await asyncio.sleep(1.5 * (attempt + 1))
    return {"truncated": None, "finish_reason": None, "completion_tokens": None,
            "reasoning_tokens": None, "letter": None, "error": last_err}


async def calibrate_model(session, sem, api_key, model_name, model_id, probe_qs, budgets, log_fh):
    results = {}
    for budget in budgets:
        async def run_one(q):
            async with sem:
                return await probe_call(session, model_id, build_prompt(q), api_key, budget)

        outcomes = await asyncio.gather(*(run_one(q) for q in probe_qs))
        truncated = sum(1 for o in outcomes if o["truncated"])
        errors = sum(1 for o in outcomes if o["error"])
        tokens = sorted(o["completion_tokens"] for o in outcomes if o["completion_tokens"] is not None)
        record = {
            "budget": budget,
            "probe_size": len(probe_qs),
            "truncated": truncated,
            "errors": errors,
            "completion_tokens_observed": tokens,
            "max_tokens_used": max(tokens) if tokens else None,
            "p50_tokens_used": tokens[len(tokens) // 2] if tokens else None,
        }
        results[budget] = record
        line = (
            f"[{model_name}] budget={budget:5d}  truncated={truncated}/{len(probe_qs)}  "
            f"errors={errors}  max_used={record['max_tokens_used']}  p50_used={record['p50_tokens_used']}"
        )
        print(line)
        log_fh.write(line + "\n")
        log_fh.flush()
        if truncated == 0 and errors == 0:
            # Found a clean budget for this model; no need to test larger ones.
            break
    return results


async def main_async(args):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    with open(args.dataset) as f:
        all_questions = json.load(f)["questions"]
    rng = random.Random(args.seed)
    probe_qs = rng.sample(all_questions, args.probe_size)

    targets = {k: MODELS[k] for k in args.models} if args.models else MODELS

    out_dir = Path("calibration")
    out_dir.mkdir(exist_ok=True)
    log_path = out_dir / "calibration.log"

    sem = asyncio.Semaphore(args.concurrency)
    full_report = {
        "probe_size": args.probe_size,
        "seed": args.seed,
        "budgets_tried": args.budgets,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "models": {},
    }

    with log_path.open("a") as log_fh:
        log_fh.write(f"\n=== Calibration run {full_report['started_at']} (probe_size={args.probe_size}) ===\n")
        connector = aiohttp.TCPConnector(limit=args.concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            for name, model_id in targets.items():
                if model_id in REASONING_MANDATORY:
                    note = f"[{name}] reasoning is mandatory for this endpoint regardless of budget"
                    print(note)
                    log_fh.write(note + "\n")
                per_budget = await calibrate_model(session, sem, api_key, name, model_id, probe_qs, args.budgets, log_fh)
                recommended = next(
                    (b for b, r in per_budget.items() if r["truncated"] == 0 and r["errors"] == 0),
                    None,
                )
                full_report["models"][name] = {
                    "model_id": model_id,
                    "reasoning_mandatory": model_id in REASONING_MANDATORY,
                    "per_budget": per_budget,
                    "recommended_max_tokens": recommended,
                }

    with (out_dir / "report.json").open("w") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)

    with (out_dir / "report.md").open("w") as f:
        f.write(f"# Token budget calibration ({full_report['started_at']})\n\n")
        f.write(f"Probe set: {args.probe_size} random questions (seed={args.seed}) from {args.dataset}\n\n")
        f.write("| Model | Recommended max_tokens | Max reasoning tokens observed | p50 tokens used |\n")
        f.write("|---|---|---|---|\n")
        for name, m in full_report["models"].items():
            rec = m["recommended_max_tokens"]
            last_budget = rec if rec is not None else max(m["per_budget"])
            r = m["per_budget"][last_budget]
            mandatory_note = " (reasoning mandatory)" if m["reasoning_mandatory"] else ""
            f.write(
                f"| {name}{mandatory_note} | {rec if rec is not None else 'NOT FOUND within tested budgets'} "
                f"| {r['max_tokens_used']} | {r['p50_tokens_used']} |\n"
            )

    print(f"\nWrote {out_dir}/report.json and {out_dir}/report.md")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/CyberMetric-2000-v1.json")
    parser.add_argument("--probe-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budgets", type=int, nargs="+", default=DEFAULT_BUDGETS)
    parser.add_argument("--concurrency", type=int, default=5, help="Kept low to avoid competing with other runs")
    parser.add_argument("--models", nargs="*", default=None)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
