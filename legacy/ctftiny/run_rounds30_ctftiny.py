#!/usr/bin/env python3
"""Round-budget sensitivity check: rerun CTFTiny's 50 challenges at
max_rounds=30 instead of 12, for Solar Pro 4 and DeepSeek V4.1 Flash.

Why: at max_rounds=12 Solar Pro 4 solves 14% of CTFTiny where DeepSeek V4.1
Flash solves 54%, and trajectory analysis says a large part of that gap is
not CTF skill but shell-command batching. DeepSeek chains 93.4% of its
commands (`cmd && cmd && cmd`, one round doing five things); Solar Pro 4
chains 48.1%, issuing `ls`, then `cat`, then `file` as separate rounds. With
a fixed round budget that difference alone costs Solar roughly half the
shell work per run -- it ends 90% of its runs on max_rounds, against 62% for
DeepSeek.

So the headline comparison may be measuring "solves within 12 agent turns"
rather than "solves". This run tests that directly: same models, same
challenges, same reasoning condition (Solar's provider default is a verified
0% reasoning rate; DeepSeek is explicitly forced off), only the round budget
changes. If Solar's deficit largely closes at 30 rounds, the 12-round
ranking is budget-dependent and must be reported as such. If it does not,
the deficit is about capability rather than turn efficiency.

Usage:
    export OPENROUTER_API_KEY=sk-or-v1-...
    python3 run_rounds30_ctftiny.py
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
    "solar-pro4": ("solarpro4_rounds30_config.yaml", "solarpro4_rounds30"),
    "deepseek-v4.1-flash": ("deepseekv41flash_reasoningoff_rounds30_config.yaml",
                            "deepseekv41flash_reasoningoff_rounds30"),
}

LOGDIR = "logs_baseline/eval_rounds30"
TIMEOUT_S = 1800          # 30 rounds needs more wall clock than 12
CONCURRENCY = 3
BUDGET_USD = 3.00         # hard stop: this key is near its monthly cap
RESULTS_PATH = ROOT / "eval_results_rounds30.jsonl"
SUMMARY_PATH = ROOT / "eval_summary_rounds30.json"
PORTS_PATH = ROOT / "challenge_ports.json"
CHALLENGES_PATH = ROOT / "ctftiny_challenges.json"

_port_locks = defaultdict(threading.Lock)
_write_lock = threading.Lock()
_spent_lock = threading.Lock()
_spent = 0.0
_stopped = False

MIN_FREE_GB = {"/": 5, "/Volumes/T7": 15}


def free_gb(path):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / (1024 ** 3)


def wait_for_disk_space():
    while any(free_gb(p) < g for p, g in MIN_FREE_GB.items()):
        time.sleep(30)


def ensure_ctfnet():
    nets = subprocess.run(["docker", "network", "ls", "--format", "{{.Name}}"],
                          capture_output=True, text=True).stdout.split()
    if "ctfnet" not in nets:
        subprocess.run(["docker", "network", "create", "ctfnet"], check=True)


def ensure_port_free(ports, timeout_s=15):
    deadline = time.time() + timeout_s
    for port in ports:
        while time.time() < deadline:
            try:
                r = subprocess.run(["docker", "ps", "-q", "--filter", f"publish={port}"],
                                   capture_output=True, text=True, timeout=5)
            except subprocess.TimeoutExpired:
                break
            ids = r.stdout.split()
            if not ids:
                break
            try:
                subprocess.run(["docker", "kill"] + ids, capture_output=True, timeout=5)
            except subprocess.TimeoutExpired:
                pass
            time.sleep(1)


def run_one(model_key: str, challenge: str, ports: list) -> dict:
    global _stopped
    if _stopped:
        return {"model": model_key, "challenge": challenge, "error": "skipped: budget stop"}
    wait_for_disk_space()
    ports = ensure_dynamic_ports(challenge, ports)
    config_name, name_key = MODELS[model_key]
    cmd = [sys.executable, "run_baseline.py", "--challenge", challenge, "-s", "test",
           "-c", f"configs/baseline/{config_name}", "-L", LOGDIR, "-d"]
    result = {"model": model_key, "challenge": challenge}

    locks = [_port_locks[p] for p in sorted(dict.fromkeys(ports))]
    for lock in locks:
        lock.acquire()
    started = time.time()
    try:
        try:
            proc = subprocess.run(cmd, cwd=str(NYUCTF_DIR), env=dict(os.environ),
                                  capture_output=True, text=True, timeout=TIMEOUT_S)
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
            result["rounds"] = traj.get("rounds")
            result["finish_reason"] = traj.get("finish_reason", "unknown")
            result["logfile"] = str(logfile.relative_to(ROOT))
        except Exception as e:
            result["error"] = result.get("error", "") + f" | log parse error: {e}"
    else:
        result.setdefault("error", "no logfile written (crash or timeout)")
    return result


def main():
    global _spent, _stopped
    if "OPENROUTER_API_KEY" not in os.environ:
        print("ERROR: export OPENROUTER_API_KEY first", file=sys.stderr)
        sys.exit(1)

    ensure_ctfnet()
    strip_all()

    challenge_ports = json.loads(PORTS_PATH.read_text())["challenge_ports"]
    challenges = json.loads(CHALLENGES_PATH.read_text())
    done = set()
    if RESULTS_PATH.exists():
        for line in RESULTS_PATH.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                done.add((row["model"], row["challenge"]))
                _spent += row.get("cost", 0) or 0
    jobs = [(m, c) for m in MODELS for c in challenges if (m, c) not in done]
    print(f"round-budget check: {len(MODELS)} models x {len(challenges)} CTFTiny challenges, "
          f"{len(done)} done (${_spent:.2f} spent), {len(jobs)} remaining, budget ${BUDGET_USD}")

    with RESULTS_PATH.open("a") as out:
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            futures = {pool.submit(run_one, m, c, challenge_ports.get(c, [])): (m, c)
                       for m, c in jobs}
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
                with _spent_lock:
                    _spent += res.get("cost", 0) or 0
                    if _spent >= BUDGET_USD and not _stopped:
                        _stopped = True
                        print(f"[budget] ${_spent:.2f} >= ${BUDGET_USD}; no further jobs will start", flush=True)
                completed += 1
                status = "SOLVED" if res.get("solved") else res.get("finish_reason", res.get("error", "?"))
                print(f"[{completed}/{len(jobs)}] {m} / {c}: {status} "
                      f"(rounds={res.get('rounds')}, ${res.get('cost', 0):.4f}, "
                      f"{res.get('wall_time_s', 0):.0f}s, total ${_spent:.2f})", flush=True)

    rows = [json.loads(l) for l in RESULTS_PATH.read_text().splitlines() if l.strip()]
    summary = {}
    for m in MODELS:
        sub = [r for r in rows if r["model"] == m]
        att = [r for r in sub if "solved" in r]
        solved = [r for r in att if r.get("solved")]
        summary[m] = {
            "attempted": len(att),
            "solved": len(solved),
            "solve_rate_of_attempted": len(solved) / len(att) if att else None,
            "avg_rounds": round(sum(r.get("rounds") or 0 for r in att) / len(att), 1) if att else None,
            "total_cost_usd": round(sum(r.get("cost", 0) or 0 for r in sub), 4),
        }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    print("\n=== SUMMARY (max_rounds=30, CTFTiny 50) ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
