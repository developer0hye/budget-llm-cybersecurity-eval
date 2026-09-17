#!/usr/bin/env python3
"""Compare OpenRouter models' cybersecurity knowledge using the CyberMetric benchmark.

Usage:
    export OPENROUTER_API_KEY=sk-or-...
    python3 run_eval.py --dataset data/CyberMetric-2000-v1.json

All questions across all selected models are scheduled onto a single asyncio
event loop and run concurrently (bounded by --concurrency), so wall-clock
time no longer scales with "models x questions run sequentially" -- it scales
with total_calls / concurrency.

Results are written incrementally under results/ as each call completes:
one <model>.jsonl per-question log (append, flushed per line) and
summary.json (rewritten every 50 completions). Watch progress live with:
    tail -f results/<model>.jsonl
    watch -n2 cat results/summary.json
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import aiohttp

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = {
    "solar-pro4": "upstage/solar-pro4",
    "gpt-5.6-luna": "openai/gpt-5.6-luna",
    "deepseek-v4.1-flash": "deepseek/deepseek-v4.1-flash",
    "glm-5.3-flash": "z-ai/glm-5.3-flash",
    "qwen3.8-flash": "qwen/qwen3.8-flash",
}

# Models whose endpoint rejects `reasoning: {enabled: false}` with
# "Reasoning is mandatory for this endpoint and cannot be disabled."
# For these we leave reasoning on and rely on a larger max_tokens budget
# instead, so the hidden reasoning tokens don't eat the whole cap.
REASONING_MANDATORY = {"z-ai/glm-5.3-flash"}

# Some providers' rate limits are much tighter than others. Sharing one
# global --concurrency across all 5 models starves these: observed 18/20
# calls failing with 429 for qwen/qwen3.8-flash at concurrency=30 shared
# across 5 models, vs 0/2000 errors when it ran alone at concurrency=6.
# Cap these specific models regardless of --concurrency; everyone else
# still shares the global limit.
MODEL_CONCURRENCY_CAP = {"qwen/qwen3.8-flash": 6}

ANSWER_RE = re.compile(r"\b([ABCD])\b")


def build_prompt(q: dict) -> str:
    choices = "\n".join(f"{k}. {v}" for k, v in q["answers"].items())
    return (
        "Answer the following cybersecurity multiple-choice question. "
        "Reply with ONLY the single letter of the correct answer (A, B, C, or D). "
        "Do not explain.\n\n"
        f"Question: {q['question']}\n{choices}\n\nAnswer:"
    )


def extract_letter(text: str) -> str | None:
    m = ANSWER_RE.search(text.upper())
    return m.group(1) if m else None


async def call_model(
    session: aiohttp.ClientSession,
    model_id: str,
    prompt: str,
    api_key: str,
    reasoning_on: bool,
    retries: int = 6,
) -> tuple[str, dict]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # Several of the compared models (DeepSeek V4.1 Flash, Qwen3.8 Flash,
    # GLM 5.3 Flash) default to reasoning mode. With a small max_tokens
    # budget, the hidden reasoning tokens consume the whole budget and
    # content comes back null (finish_reason "length"). GLM 5.3 Flash's
    # endpoint rejects `reasoning: {enabled: false}` outright ("Reasoning
    # is mandatory for this endpoint and cannot be disabled"), so it always
    # runs with reasoning on regardless of --reasoning. For the rest,
    # --reasoning on/off explicitly sets it so we can compare both.
    want_reasoning = reasoning_on or model_id in REASONING_MANDATORY
    if want_reasoning:
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 4000,
            "reasoning": {"enabled": True},
        }
    else:
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 16,
            "reasoning": {"enabled": False},
        }
    last_err = None
    for attempt in range(retries):
        try:
            async with session.post(
                OPENROUTER_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 429:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else min(3 * (2**attempt), 30)
                    last_err = RuntimeError("429 Too Many Requests")
                    await asyncio.sleep(wait + random.uniform(0, 1))
                    continue
                resp.raise_for_status()
                data = await resp.json()
                content = data["choices"][0]["message"].get("content")
                if content is None:
                    raise RuntimeError(
                        f"empty content, finish_reason={data['choices'][0].get('finish_reason')}"
                    )
                usage = data.get("usage", {})
                return content.strip(), {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "cost": usage.get("cost"),
                }
        except Exception as e:  # noqa: BLE001
            last_err = e
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{model_id} call failed: {last_err}")


class Progress:
    """Simple single-line progress counter, safe on a single event loop thread."""

    def __init__(self, total: int):
        self.total = total
        self.done = 0
        self.start = time.time()

    def tick(self):
        self.done += 1
        elapsed = time.time() - self.start
        rate = self.done / elapsed if elapsed > 0 else 0
        eta = (self.total - self.done) / rate if rate > 0 else 0
        print(
            f"\r{self.done}/{self.total} calls  ({rate:.1f}/s, ETA {eta:.0f}s)   ",
            end="",
            flush=True,
        )


async def run_one(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    api_key: str,
    model_name: str,
    model_id: str,
    idx: int,
    q: dict,
    progress: Progress,
    reasoning_on: bool,
) -> tuple[str, int, str | None, str | None, str | None, dict | None]:
    async with sem:
        prompt = build_prompt(q)
        usage = None
        try:
            raw, usage = await call_model(session, model_id, prompt, api_key, reasoning_on)
            letter = extract_letter(raw)
            err = None
        except Exception as e:  # noqa: BLE001
            raw, letter, err = None, None, str(e)
    progress.tick()
    return model_name, idx, letter, raw, err, usage


async def main_async(args):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    with open(args.dataset) as f:
        questions = json.load(f)["questions"]
    if args.limit:
        questions = questions[: args.limit]

    targets = {k: MODELS[k] for k in args.models} if args.models else MODELS

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_calls = len(questions) * len(targets)
    print(f"Scheduling {total_calls} calls across {len(targets)} models, concurrency={args.concurrency}")
    progress = Progress(total_calls)

    # One semaphore per model, so a globally shared --concurrency doesn't
    # starve/overload individual providers with tighter rate limits.
    sems = {
        name: asyncio.Semaphore(min(args.concurrency, MODEL_CONCURRENCY_CAP.get(model_id, args.concurrency)))
        for name, model_id in targets.items()
    }
    capped = {n: MODEL_CONCURRENCY_CAP[mid] for n, mid in targets.items() if mid in MODEL_CONCURRENCY_CAP}
    if capped:
        print(f"Per-model concurrency caps in effect: {capped}")

    # Open one log file per model up front and write each result the moment
    # it comes back, instead of buffering everything in memory until the
    # whole run finishes. This lets you `tail -f results/<model>.jsonl` (or
    # `watch cat results/summary.json`) to see real progress mid-run.
    log_files = {name: (out_dir / f"{name}.jsonl").open("w") for name in targets}
    stats = {
        name: {
            "total": 0, "answered": 0, "correct": 0, "errors": 0,
            "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0,
        }
        for name in targets
    }

    def write_summary():
        summary = {}
        total_cost = 0.0
        for name, s in stats.items():
            summary[name] = {
                "model_id": targets[name],
                **s,
                "cost_usd": round(s["cost_usd"], 6),
                "accuracy": round(s["correct"] / s["total"] * 100, 2) if s["total"] else 0.0,
            }
            total_cost += s["cost_usd"]
        summary["_total_cost_usd"] = round(total_cost, 6)
        with (out_dir / "summary.json").open("w") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return summary

    try:
        connector = aiohttp.TCPConnector(limit=args.concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                run_one(session, sems[name], api_key, name, model_id, idx, q, progress, args.reasoning == "on")
                for name, model_id in targets.items()
                for idx, q in enumerate(questions)
            ]
            for coro in asyncio.as_completed(tasks):
                model_name, idx, letter, raw, err, usage = await coro
                q = questions[idx]
                is_correct = letter == q["solution"] if letter else False

                s = stats[model_name]
                s["total"] += 1
                if err:
                    s["errors"] += 1
                elif letter:
                    s["answered"] += 1
                    if is_correct:
                        s["correct"] += 1
                if usage:
                    s["prompt_tokens"] += usage.get("prompt_tokens") or 0
                    s["completion_tokens"] += usage.get("completion_tokens") or 0
                    s["cost_usd"] += usage.get("cost") or 0.0

                log_files[model_name].write(
                    json.dumps(
                        {
                            "question": q["question"],
                            "solution": q["solution"],
                            "model_letter": letter,
                            "model_raw": raw,
                            "correct": is_correct,
                            "error": err,
                            "usage": usage,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                log_files[model_name].flush()

                if progress.done % 50 == 0:
                    write_summary()
    finally:
        for f in log_files.values():
            f.close()
    print()

    summary = write_summary()
    model_rows = {k: v for k, v in summary.items() if not k.startswith("_")}
    print("=== Results ===")
    for name, s in sorted(model_rows.items(), key=lambda x: -x[1]["accuracy"]):
        print(
            f"{name:24s} {s['accuracy']:6.2f}%  (correct {s['correct']}/{s['total']}, errors {s['errors']}, "
            f"cost ${s['cost_usd']:.4f})"
        )
    print(f"\nTotal cost this run: ${summary['_total_cost_usd']:.4f}")
    print(f"Detailed results: {out_dir}/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/CyberMetric-2000-v1.json")
    parser.add_argument("--limit", type=int, default=None, help="Cap number of questions, e.g. 20 for a smoke test")
    parser.add_argument("--concurrency", type=int, default=30, help="Total in-flight requests across all models")
    parser.add_argument("--models", nargs="*", default=None, help="Subset of MODELS keys to run")
    parser.add_argument(
        "--reasoning",
        choices=["off", "on"],
        default="off",
        help="Force reasoning on/off for models that support toggling it. "
        "GLM 5.3 Flash ignores this -- its endpoint mandates reasoning on.",
    )
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
