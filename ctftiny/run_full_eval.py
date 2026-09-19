#!/usr/bin/env python3
"""Run all 5 budget-tier models against the FULL NYU CTF Bench test split
(200 challenges) via nyuctf_agents' baseline agent. Extends run_all_models.py
(which covered a fixed 12-challenge stratified sample) to the full dataset.

Two things the smaller run didn't need:

1. Port-locking. ~95 of the 200 challenges expose a docker-compose host
   port, and many challenges SHARE a port (28 challenges alone hardcode
   host port 8000) -- including, trivially, the same challenge run by two
   different models at once. Running those concurrently makes docker
   compose's port bind race and fail nondeterministically, which would
   silently corrupt results (a "didn't solve" that's actually "lost a port
   race", indistinguishable from a real non-solve). Every job acquires a
   lock for each host port its challenge needs (sorted, held for the whole
   subprocess -- run_baseline.py leaves the compose stack up for the full
   run, not just at startup) before running, so port-sharing jobs serialize
   against each other while everything else runs at full concurrency.

2. Resumability. This run is long enough (~10+ hours) that losing all
   progress to a crash partway through isn't acceptable. Results are
   appended (not overwritten), and any (model, challenge) pair already
   present in the output file -- including the 60 rows carried over from
   the original 12-challenge run_all_models.py sample -- is skipped.

Usage:
    export OPENROUTER_API_KEY=sk-or-v1-...
    python3 run_full_eval.py
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

ROOT = Path(__file__).parent.resolve()
NYUCTF_DIR = ROOT / "nyuctf_agents"

MODELS = {
    "qwen3.8-flash": ("qwen/qwen3.8-flash", "qwen38flash_config.yaml", "qwen38flash"),
    "solar-pro4": ("upstage/solar-pro4", "solarpro4_config.yaml", "solarpro4"),
    "gpt-5.6-luna": ("openai/gpt-5.6-luna", "gpt56luna_config.yaml", "gpt56luna"),
    "deepseek-v4.1-flash": ("deepseek/deepseek-v4.1-flash", "deepseekv41flash_config.yaml", "deepseekv41flash"),
    "glm-5.3-flash": ("z-ai/glm-5.3-flash", "glm53flash_config.yaml", "glm53flash"),
}

LOGDIR = "logs_baseline/eval_full"
TIMEOUT_S = 900
CONCURRENCY = 6
RESULTS_PATH = ROOT / "eval_results_full.jsonl"
SUMMARY_PATH = ROOT / "eval_summary_full.json"
PORTS_PATH = ROOT / "challenge_ports.json"
SEED_RESULTS_PATH = ROOT / "eval_results.jsonl"  # the 12-challenge sample, carried forward

_port_locks = defaultdict(threading.Lock)
_write_lock = threading.Lock()


def load_challenge_ports():
    data = json.loads(PORTS_PATH.read_text())
    return data["all_challenges"], data["challenge_ports"]


def load_done_pairs():
    """(model, challenge) pairs that already have a result, from either the
    seed file (original 12-challenge run) or a prior partial run of this
    script -- so re-running after a crash or Ctrl-C doesn't redo work."""
    done = {}
    for path in (SEED_RESULTS_PATH, RESULTS_PATH):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            done[(row["model"], row["challenge"])] = row
    return done


# Docker's VM disk (Docker.raw) now lives on /Volumes/T7 (symlinked in from
# ~/Library/Containers/com.docker.docker/Data/vms/0/data), not the internal
# disk, after two ENOSPC crashes on internal-only storage. Both still need a
# floor: T7 against Docker growth, "/" for the project's own small writes.
MIN_FREE_GB = {"/": 5, "/Volumes/T7": 15}
DISK_CHECK_INTERVAL_S = 30


def free_gb(path):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / (1024 ** 3)


def wait_for_disk_space():
    """Each challenge's docker-compose pull/build can add several GB; a run
    that started this project already had little headroom, and Docker's own
    disk usage outpaced a naive per-job cleanup once enough unique
    multi-GB challenge images piled up (this is exactly what crashed the
    first attempt at this run with ENOSPC -- Docker's daemon itself hung,
    and several in-flight jobs got a corrupted false "failure" from Python's
    own tempfile module having nowhere to write). Block new subprocess
    launches (not already-running ones) until a companion cleanup process
    catches up, rather than plow forward into a repeat crash.
    """
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


def run_one(model_key: str, challenge: str, ports: list) -> dict:
    wait_for_disk_space()
    model_id, config_name, name_key = MODELS[model_key]
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

    locks = [_port_locks[p] for p in sorted(ports)]
    for lock in locks:
        lock.acquire()
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


def ensure_ctfnet():
    """The agent's base container joins a `ctfnet` bridge network that
    upstream's setup_baseline.sh creates once, by hand -- it isn't baked
    into any image, so a fresh/reset Docker daemon (e.g. after relocating
    Docker's VM disk) silently drops it, and every job then fails at
    `docker run --network ctfnet` before ever reaching a challenge. This bit
    us once already (71 rows falsely marked as failures); check for it on
    every launch instead of relying on remembering to re-run setup."""
    exists = subprocess.run(
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        capture_output=True, text=True,
    ).stdout.split()
    if "ctfnet" not in exists:
        print("[setup] ctfnet network missing, creating it", flush=True)
        subprocess.run(["docker", "network", "create", "ctfnet"], check=True)


def main():
    if "OPENROUTER_API_KEY" not in os.environ:
        print("ERROR: export OPENROUTER_API_KEY first", file=sys.stderr)
        sys.exit(1)

    ensure_ctfnet()

    all_challenges, challenge_ports = load_challenge_ports()
    done = load_done_pairs()

    jobs = []
    for m in MODELS:
        for c in all_challenges:
            if (m, c) in done:
                continue
            jobs.append((m, c))

    print(f"{len(all_challenges)} challenges x {len(MODELS)} models = {len(all_challenges) * len(MODELS)} total")
    print(f"{len(done)} already done (seeded from {SEED_RESULTS_PATH.name} / prior run), {len(jobs)} remaining")
    print(f"concurrency={CONCURRENCY}, port-locked ports: {sorted(p for p in {p for ps in challenge_ports.values() for p in ps})}")

    # carry forward already-done rows into the full results file first, if
    # this is the first time run_full_eval writes it (RESULTS_PATH doesn't
    # yet contain the seed rows)
    already_in_results_file = set()
    if RESULTS_PATH.exists():
        for line in RESULTS_PATH.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                already_in_results_file.add((row["model"], row["challenge"]))

    with RESULTS_PATH.open("a") as out:
        for (m, c), row in done.items():
            if (m, c) not in already_in_results_file:
                out.write(json.dumps(row) + "\n")
        out.flush()

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

    # Aggregate
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
