#!/usr/bin/env python3
"""Run all 5 budget-tier models against a fixed, stratified-by-category
sample of NYU CTF Bench (test split) challenges via nyuctf_agents' baseline
agent, and collect solve rate / cost / time into a summary JSON.

Challenge sample: 2 per category (crypto/forensics/misc/pwn/rev/web),
selected with `random.seed(42)` over the full 200-challenge test split
(see README.md for the exact selection code). Fixed, not cherry-picked.

Usage:
    export OPENROUTER_API_KEY=sk-or-v1-...
    python3 run_all_models.py
"""
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
NYUCTF_DIR = ROOT / "nyuctf_agents"

MODELS = {
    "qwen3.8-flash": ("qwen/qwen3.8-flash", "qwen38flash_config.yaml"),
    "solar-pro4": ("upstage/solar-pro4", "solarpro4_config.yaml"),
    "gpt-5.6-luna": ("openai/gpt-5.6-luna", "gpt56luna_config.yaml"),
    "deepseek-v4.1-flash": ("deepseek/deepseek-v4.1-flash", "deepseekv41flash_config.yaml"),
    "glm-5.3-flash": ("z-ai/glm-5.3-flash", "glm53flash_config.yaml"),
}

CHALLENGES = [
    "2017f-cry-ecxor", "2021q-cry-ecc_pop_quiz",
    "2017q-for-missed_registration", "2021f-for-no_time_to_register",
    "2022q-msc-cattheflag", "2022q-msc-ezmaze",
    "2020q-pwn-slithery", "2022f-pwn-salt_server",
    "2018f-rev-1nsayne", "2020f-rev-rap",
    "2017q-web-orange", "2021q-web-securinotes",
]

LOGDIR = "logs_baseline/eval"
TIMEOUT_S = 900  # per (model, challenge) run
CONCURRENCY = 3
RESULTS_PATH = ROOT / "eval_results.jsonl"
SUMMARY_PATH = ROOT / "eval_summary.json"


def run_one(model_key: str, challenge: str) -> dict:
    model_id, config_name = MODELS[model_key]
    started = time.time()
    cmd = [
        sys.executable, "run_baseline.py",
        "--challenge", challenge,
        "-s", "test",
        "-c", f"configs/baseline/{config_name}",
        "-L", LOGDIR,
        "-d",
    ]
    env = dict(os.environ)
    result = {"model": model_key, "challenge": challenge}
    try:
        proc = subprocess.run(
            cmd, cwd=str(NYUCTF_DIR), env=env,
            capture_output=True, text=True, timeout=TIMEOUT_S,
        )
        result["returncode"] = proc.returncode
        if proc.returncode != 0:
            result["error"] = proc.stderr[-4000:]
    except subprocess.TimeoutExpired:
        result["error"] = f"timed out after {TIMEOUT_S}s"
        result["returncode"] = None

    result["wall_time_s"] = time.time() - started

    # nyuctf_agents only writes the trajectory log on clean __exit__, so a
    # timeout or crash leaves no file -- that's a real "infrastructure
    # failure" outcome, recorded as such rather than retried silently.
    # config "name" fields use the short keys defined when the configs were
    # generated (qwen38flash, solarpro4, gpt56luna, deepseekv41flash, glm53flash)
    name_map = {
        "qwen3.8-flash": "qwen38flash", "solar-pro4": "solarpro4",
        "gpt-5.6-luna": "gpt56luna", "deepseek-v4.1-flash": "deepseekv41flash",
        "glm-5.3-flash": "glm53flash",
    }
    logfile = NYUCTF_DIR / LOGDIR / f"NYU_Baseline_{name_map[model_key]}" / f"{challenge}.json"
    if logfile.exists():
        try:
            traj = json.loads(logfile.read_text())
            result["solved"] = traj.get("solved", False)
            result["cost"] = traj.get("cost", 0)
            result["finish_reason"] = traj.get("finish_reason", "unknown")
            result["runtime_total"] = (traj.get("runtime") or {}).get("total", 0)
            result["logfile"] = str(logfile.relative_to(ROOT))
        except Exception as e:
            result["error"] = result.get("error", "") + f" | log parse error: {e}"
    else:
        result.setdefault("error", "no logfile written (crash or timeout)")

    return result


def main():
    if "OPENROUTER_API_KEY" not in os.environ:
        print("ERROR: export OPENROUTER_API_KEY first", file=sys.stderr)
        sys.exit(1)

    jobs = [(m, c) for m in MODELS for c in CHALLENGES]
    print(f"Running {len(jobs)} (model, challenge) pairs, concurrency={CONCURRENCY}")

    with RESULTS_PATH.open("w") as out:
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            futures = {pool.submit(run_one, m, c): (m, c) for m, c in jobs}
            done = 0
            for fut in concurrent.futures.as_completed(futures):
                m, c = futures[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = {"model": m, "challenge": c, "error": f"driver exception: {e}"}
                out.write(json.dumps(res) + "\n")
                out.flush()
                done += 1
                status = "SOLVED" if res.get("solved") else res.get("finish_reason", res.get("error", "?"))
                print(f"[{done}/{len(jobs)}] {m} / {c}: {status} (cost=${res.get('cost', 0):.4f}, {res.get('wall_time_s', 0):.0f}s)")

    # Aggregate summary. "attempted" = rows that produced a real trajectory
    # (a "solved" key means run_baseline.py's __exit__ wrote a logfile);
    # anything else (crash, timeout, environment failure like a dead
    # challenge server) never ran the agent to completion and must not be
    # silently folded into "didn't solve" -- solve_rate is reported over
    # both n (the full sample) and attempted (excluding infra failures),
    # since those two denominators tell different stories.
    results = [json.loads(l) for l in RESULTS_PATH.read_text().splitlines()]
    summary = {}
    for m in MODELS:
        rows = [r for r in results if r["model"] == m]
        attempted = [r for r in rows if "solved" in r]
        solved = sum(1 for r in rows if r.get("solved"))
        total_cost = sum(r.get("cost", 0) or 0 for r in rows)
        errors = sum(1 for r in rows if r.get("error") and not r.get("solved"))
        summary[m] = {
            "n": len(rows),
            "attempted": len(attempted),
            "no_log": len(rows) - len(attempted),
            "solved": solved,
            "solve_rate_of_n": solved / len(rows) if rows else 0,
            "solve_rate_of_attempted": solved / len(attempted) if attempted else None,
            "total_cost_usd": total_cost,
            "avg_wall_time_s": sum(r.get("wall_time_s", 0) for r in rows) / len(rows) if rows else 0,
            "errors": errors,
        }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
