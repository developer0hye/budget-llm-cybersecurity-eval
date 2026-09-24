#!/usr/bin/env python3
"""Re-run Qwen3.8 Flash, DeepSeek V4.1 Flash, and GPT-5.6 Luna against the
full 200-challenge test split with reasoning explicitly DISABLED (see
*_reasoningoff_config.yaml). GLM 5.3 Flash is excluded -- its reasoning is
mandatory and can't be turned off (confirmed in the CyberMetric project).
Solar Pro4 is excluded -- its default behavior already measured at 0/112
sampled turns reasoning, so its existing full-200 run already serves as its
"reasoning off" condition; run_solarpro4_reasoning.py covers its "on" side.

Why: an audit found the original full-200 run never set reasoning
explicitly, so each model ran at whatever its provider defaults to when
unspecified -- and that default varies wildly (Qwen ~100%, DeepSeek ~97%,
GLM ~83%, Luna ~36%, Solar 0%). This means even the "default" comparisons
among the other 4 models weren't apples-to-apples either. This run gives
Qwen/DeepSeek/Luna a genuine reasoning=OFF data point to pair against
their existing (mostly reasoning=ON-by-default) full-200 results, the same
way the Solar Pro4 reasoning=ON re-run paired against its reasoning=OFF
default.

Usage:
    export OPENROUTER_API_KEY=sk-or-v1-...
    python3 run_reasoning_off.py
"""
import concurrent.futures
import json
import os
import subprocess
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

from dynamic_ports import ensure_dynamic_ports
from strip_docker_sock import strip_all

ROOT = Path(__file__).parent.resolve()
NYUCTF_DIR = ROOT / "nyuctf_agents"

MODELS = {
    "qwen3.8-flash": "qwen38flash_reasoningoff_config.yaml",
    "deepseek-v4.1-flash": "deepseekv41flash_reasoningoff_config.yaml",
    "gpt-5.6-luna": "gpt56luna_reasoningoff_config.yaml",
}
NAME_KEYS = {
    "qwen3.8-flash": "qwen38flash_reasoningoff",
    "deepseek-v4.1-flash": "deepseekv41flash_reasoningoff",
    "gpt-5.6-luna": "gpt56luna_reasoningoff",
}

LOGDIR = "logs_baseline/eval_reasoning_off"
TIMEOUT_S = 900
CONCURRENCY = 6
RESULTS_PATH = ROOT / "eval_results_reasoning_off.jsonl"
SUMMARY_PATH = ROOT / "eval_summary_reasoning_off.json"
PORTS_PATH = ROOT / "challenge_ports.json"

_port_locks = defaultdict(threading.Lock)
_write_lock = threading.Lock()

MIN_FREE_GB = {"/": 5, "/Volumes/T7": 15}
DISK_CHECK_INTERVAL_S = 30


def free_gb(path):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / (1024 ** 3)


def wait_for_disk_space():
    warned = False
    while any(free_gb(p) < min_gb for p, min_gb in MIN_FREE_GB.items()):
        if not warned:
            low = {p: round(free_gb(p), 1) for p in MIN_FREE_GB}
            print(f"[disk] low free space {low}, pausing new launches until above {MIN_FREE_GB}", flush=True)
            warned = True
        time.sleep(DISK_CHECK_INTERVAL_S)
    if warned:
        ok = {p: round(free_gb(p), 1) for p in MIN_FREE_GB}
        print(f"[disk] {ok} free, resuming", flush=True)


def ensure_ctfnet():
    exists = subprocess.run(
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        capture_output=True, text=True,
    ).stdout.split()
    if "ctfnet" not in exists:
        print("[setup] ctfnet network missing, creating it", flush=True)
        subprocess.run(["docker", "network", "create", "ctfnet"], check=True)


def load_challenge_ports():
    data = json.loads(PORTS_PATH.read_text())
    return data["all_challenges"], data["challenge_ports"]


def load_done_pairs():
    if not RESULTS_PATH.exists():
        return set()
    done = set()
    for line in RESULTS_PATH.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            done.add((row["model"], row["challenge"]))
    return done


def ensure_port_free(ports, timeout_s=15):
    """Killing the `run_baseline.py` subprocess on a timeout does not tear
    down the docker-compose stack it started -- a lock released right after
    SIGKILL can hand the port to the next job while the previous challenge's
    container is still bound to it (found by codex review, 2026-09-20).
    Verify+force-free every port this job held before its lock is released.
    """
    # Every call below carries its own timeout -- without one, a hung
    # `docker ps`/`docker kill` blocks this thread forever (past `deadline`
    # entirely, since that's only checked between calls), permanently
    # deadlocking every other job waiting on this port (found live during
    # the 2026-09-20 retry batch).
    deadline = time.time() + timeout_s
    for port in ports:
        while time.time() < deadline:
            try:
                r = subprocess.run(
                    ["docker", "ps", "-q", "--filter", f"publish={port}"],
                    capture_output=True, text=True, timeout=5,
                )
            except subprocess.TimeoutExpired:
                break
            container_ids = r.stdout.split()
            if not container_ids:
                break
            try:
                subprocess.run(["docker", "kill"] + container_ids, capture_output=True, timeout=5)
            except subprocess.TimeoutExpired:
                pass
            time.sleep(1)


def run_one(model_key: str, challenge: str, ports: list) -> dict:
    wait_for_disk_space()
    ports = ensure_dynamic_ports(challenge, ports)
    config_name = MODELS[model_key]
    name_key = NAME_KEYS[model_key]
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

    # dict.fromkeys de-dupes while keeping order; acquiring the same
    # non-reentrant Lock twice would self-deadlock the worker and
    # strand every later job needing that port.
    locks = [_port_locks[p] for p in sorted(dict.fromkeys(ports))]
    for lock in locks:
        lock.acquire()
    # Started only after the lock is held, so wall_time_s doesn't include
    # time blocked on a contended port (found by codex review, 2026-09-20).
    started = time.time()
    try:
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
    finally:
        ensure_port_free(ports)
        for lock in reversed(locks):
            lock.release()

    result["wall_time_s"] = time.time() - started

    logfile = NYUCTF_DIR / LOGDIR / f"NYU_Baseline_{name_key}" / f"{challenge}.json"
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

    ensure_ctfnet()
    # 63 of the 200 test challenges bind-mount the host Docker socket as
    # shipped; a successful agent exploit in one of those containers would
    # reach the host. Re-downloading the dataset restores the mounts, so
    # strip them on every run rather than once by hand.
    strip_all()

    all_challenges, challenge_ports = load_challenge_ports()
    done = load_done_pairs()
    jobs = [(m, c) for m in MODELS for c in all_challenges if (m, c) not in done]

    print(f"reasoning-off re-run: {len(MODELS)} models x {len(all_challenges)} challenges, {len(done)} already done, {len(jobs)} remaining")

    with RESULTS_PATH.open("a") as out:
        if not jobs:
            print("Nothing left to run.")
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
                futures = {
                    pool.submit(run_one, m, c, challenge_ports.get(c, [])): (m, c)
                    for m, c in jobs
                }
                completed = 0
                for fut in concurrent.futures.as_completed(futures):
                    m, c = futures[fut]
                    try:
                        res = fut.result()
                    except Exception as e:
                        res = {"model": m, "challenge": c, "error": f"driver exception: {e}"}
                    with _write_lock:
                        out.write(json.dumps(res) + "\n")
                        out.flush()
                    completed += 1
                    status = "SOLVED" if res.get("solved") else res.get("finish_reason", res.get("error", "?"))
                    print(f"[{completed}/{len(jobs)}] {m} / {c}: {status} (cost=${res.get('cost', 0):.4f}, {res.get('wall_time_s', 0):.0f}s)", flush=True)

    results = [json.loads(l) for l in RESULTS_PATH.read_text().splitlines()]
    summary = {}
    for m in MODELS:
        rows = [r for r in results if r["model"] == m]
        attempted = [r for r in rows if "solved" in r]
        solved = [r for r in attempted if r.get("solved")]
        total_cost = sum(r.get("cost", 0) or 0 for r in rows)
        summary[m] = {
            "n": len(rows),
            "attempted": len(attempted),
            "no_log": len(rows) - len(attempted),
            "solved": len(solved),
            "solve_rate_of_attempted": len(solved) / len(attempted) if attempted else None,
            "total_cost_usd": round(total_cost, 4),
            "avg_wall_time_s_attempted": round(sum(r["wall_time_s"] for r in attempted) / len(attempted), 1) if attempted else None,
        }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
