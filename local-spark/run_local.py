#!/usr/bin/env python3
"""Run budget-llm-cybersecurity-eval's knowledge axis against a local vLLM server.

The upstream harness (knowledge/run_knowledge.py) only talks to OpenRouter:
it imports MODELS/PROVIDER/OPENROUTER_URL from models.py and sends
OpenRouter-only fields (`reasoning: {enabled}`, `provider` pins). This
wrapper keeps everything else upstream untouched -- dataset loading, prompt
templates, answer extraction, scoring, resume guard, summary -- and swaps
only two things before the harness runs:

1. a stand-in `models` module listing the locally served models, so
   run_config.json pins "local-vllm-dgx-spark" as the provider;
2. `call_model`, which translates the reasoning toggle into what vLLM's
   chat templates understand (`chat_template_kwargs.enable_thinking`, plus
   top-level `reasoning_effort` for Qwen3.8) and talks to the local
   OpenAI-compatible endpoint.

Kept from the upstream protocol: temperature 0, the same max_tokens for
every model (16000), the system prompts and templates, the empty-content
retry rule. Changed: per-call timeout is 3600 s instead of 600 s, because
on one GB10 a 16k-token reasoning trace at ~20 tok/s per stream needs
~800 s and a timeout would only throw the work away and retry it.

Usage (from the repo root, with the repo's .venv):
    BCSE_URL=http://127.0.0.1:8000/v1/chat/completions \
    .venv/bin/python local-spark/run_local.py --models gemma-4-12b \
        --reasoning off --concurrency 32 --out local-spark/work_reasoning_off
"""

import asyncio
import json
import os
import sys
import time
import types
from pathlib import Path

import aiohttp

REPO = Path(os.environ.get("BCSE_REPO", Path.home() / "budget-llm-cybersecurity-eval")).resolve()
URL = os.environ.get("BCSE_URL", "http://127.0.0.1:8000/v1/chat/completions")

# Short name -> served model name (llm-serve --served-model-name).
LOCAL_MODELS = {
    "gemma-4-12b": "gemma-4-12b-it",
    "gemma-4-26b-a4b": "gemma-4-26b-a4b-it",
    "gemma-4-31b": "gemma-4-31b-it",
    "qwen3.8-flash-next": "qwen38-flash-next-fp4-local",
    "qwen3.8-27b": "qwen38-27b",
}
# Which weights each served name was running, recorded in run_config.json so
# a resume into the same --out cannot mix quantizations.
LOCAL_PROVIDER = {
    "gemma-4-12b-it": "local-vllm-dgx-spark:RedHatAI/gemma-4-12B-it-NVFP4",
    "gemma-4-26b-a4b-it": "local-vllm-dgx-spark:nvidia/Gemma-4-26B-A4B-NVFP4",
    "gemma-4-31b-it": "local-vllm-dgx-spark:nvidia/Gemma-4-31B-IT-NVFP4",
    "qwen38-flash-next-fp4-local": "local-vllm-dgx-spark:nvidia/Qwen3.8-Flash-Next-FP4-Local",
    "qwen38-27b": "local-vllm-dgx-spark:nvidia/Qwen3.8-27B-NVFP4@482ca0f",
}

stub = types.ModuleType("models")
stub.MODELS = LOCAL_MODELS
stub.PROVIDER = LOCAL_PROVIDER
stub.OPENROUTER_URL = URL
stub.REASONING_MANDATORY = set()
stub.MODEL_CONCURRENCY_CAP = {}
sys.modules["models"] = stub

sys.path.insert(0, str(REPO / "knowledge"))
os.chdir(REPO)  # run_knowledge resolves data/ and --out relative to the repo root
os.environ.setdefault("OPENROUTER_API_KEY", "local-unused")  # upstream refuses to start without it
import run_knowledge as rk  # noqa: E402

TIMEOUT_S = int(os.environ.get("BCSE_TIMEOUT_S", "3600"))


async def call_model_local(session, model_id, system, prompt, api_key, reasoning_on, max_tokens, retries=6):
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": bool(reasoning_on)},
    }
    # BCSE_SAMPLING=card: the model card's recommended thinking sampling instead of the protocol's
    # greedy decoding, run as an extra reasoning-on condition (owner's choice, 2026-11-09). Values
    # match each checkpoint's generation_config.json; Qwen's card also sets min_p 0 and
    # presence_penalty 0. A fixed per-request seed makes the run repeatable on the same server.
    sampling = os.environ.get("BCSE_SAMPLING", "greedy")
    if sampling == "card":
        if model_id.startswith("qwen"):
            payload.update(temperature=1.0, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=0.0, seed=0)
        else:
            payload.update(temperature=1.0, top_p=0.95, top_k=64, seed=0)
    # Qwen3.8 reasoning effort. The upstream OpenRouter runs used medium
    # (OpenRouter's definition of `reasoning: {enabled: true}`); for the local
    # Qwen runs the owner chose the model's maximum, xhigh (2026-11-09), which
    # is also the chat template's default. xhigh makes the template prepend
    # "think carefully through the task, validate key assumptions, ..." to the
    # system prompt; medium adds nothing. The template reads the effort only
    # as a top-level request field (inside chat_template_kwargs it is ignored;
    # an invalid value at top level is HTTP 400). Gemma 4 has no effort control.
    effort = None
    if reasoning_on and model_id.startswith("qwen"):
        effort = os.environ.get("BCSE_QWEN_EFFORT", "xhigh")
        payload["reasoning_effort"] = effort
    last_err = None
    for attempt in range(retries):
        try:
            t0 = time.time()
            async with session.post(URL, json=payload, timeout=aiohttp.ClientTimeout(total=TIMEOUT_S)) as resp:
                body = await resp.text()
                if resp.status == 429 or resp.status >= 500:
                    last_err = f"HTTP {resp.status}: {body[:300]}"
                    await asyncio.sleep(min(3 * (2**attempt), 60))
                    continue
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}: {body[:300]}")
                data = json.loads(body)
                choice = data["choices"][0]
                msg = choice["message"]
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
                if choice.get("finish_reason") == "stop" and not content.strip():
                    last_err = "empty content with finish_reason stop"
                    await asyncio.sleep(min(3 * (2**attempt), 60))
                    continue
                usage = data.get("usage") or {}
                # vLLM reports no reasoning_tokens. Derive them as completion
                # tokens minus the tokenized final answer (off by a few
                # template tokens), so the upstream summary's reasoning_rows
                # and per-row trace lengths are meaningful.
                rt = 0
                if reasoning:
                    async with session.post(URL.replace("/v1/chat/completions", "/tokenize"),
                                            json={"model": model_id, "prompt": content,
                                                  "add_special_tokens": False}) as tr:
                        ct = (await tr.json()).get("count", 0)
                    rt = max(1, (usage.get("completion_tokens") or 0) - ct)
                usage["completion_tokens_details"] = {"reasoning_tokens": rt,
                                                      "reasoning_chars": len(reasoning)}
                usage["cost"] = 0.0
                return {
                    "response": content,
                    "finish_reason": choice.get("finish_reason"),
                    "provider": LOCAL_PROVIDER.get(model_id),
                    "usage": usage,
                    "latency_s": round(time.time() - t0, 2),
                    # Logged per row so a run's effort setting can be audited from the jsonl.
                    "reasoning_effort": effort,
                    "sampling": {k: payload[k] for k in ("temperature", "top_p", "top_k", "min_p",
                                                         "presence_penalty", "seed") if k in payload},
                }
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError, KeyError) as e:
            last_err = f"{type(e).__name__}: {e}"
            await asyncio.sleep(min(3 * (2**attempt), 60))
    raise RuntimeError(last_err or "retries exhausted")


rk.call_model = call_model_local
rk.MODELS = LOCAL_MODELS
rk.PROVIDER = LOCAL_PROVIDER
rk.REASONING_MANDATORY = set()
rk.MODEL_CONCURRENCY_CAP = {}

def _progress(t0, total, out_dir, names):
    """Line-buffered [k/N] progress with ETA every 60 s (upstream only prints \r updates)."""
    import threading

    def count():
        return sum(sum(1 for _ in open(out_dir / f"{m}.jsonl")) for m in names
                   if (out_dir / f"{m}.jsonl").exists())

    # Rows already logged by an earlier invocation (resume) are excluded from
    # the rate, otherwise the ETA would be too optimistic.
    start_rows = count()

    def loop():
        while True:
            time.sleep(60)
            n = count()
            el = time.time() - t0
            done = n - start_rows
            rate = done / el if el > 0 and done > 0 else 0
            eta = (total - n) / rate if rate else float("nan")
            print(f"\n[{n}/{total}] elapsed {el/60:.1f} min  avg/item {1/rate if rate else float('nan'):.2f} s"
                  f"  ETA {eta/60:.1f} min", flush=True)
    threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    import argparse
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--models", nargs="*")
    pre.add_argument("--sample", type=int)
    pre.add_argument("--reasoning", default="off")
    pre.add_argument("--out")
    pre.add_argument("--tasks", nargs="*", default=rk.TASKS)
    a, _ = pre.parse_known_args()
    if not a.out:
        # The upstream default writes into the repo's committed results_reasoning_* dirs.
        sys.exit("--out is required (e.g. local-spark/results_reasoning_off); never write into upstream result dirs")
    # run_config.json does not pin sampling, so keep greedy and card-sampling rows in separate dirs.
    if (os.environ.get("BCSE_SAMPLING", "greedy") == "card") != a.out.rstrip("/").endswith("_card"):
        sys.exit("BCSE_SAMPLING=card must write to an --out ending in _card, and greedy runs must not")
    per_task = {"WMDP-cyber": 996, "CTI-MCQ": 2500, "CTI-RCM": 1000}
    total = sum((a.sample or per_task[t]) for t in a.tasks) * len(a.models or LOCAL_MODELS)
    out_dir = REPO / (a.out or f"knowledge/results_reasoning_{a.reasoning}")
    print(f"total work: {total} items x 1 call = {total} calls", flush=True)
    t0 = time.time()
    _progress(t0, total, out_dir, a.models or list(LOCAL_MODELS))
    rk.main()
    print(f"wall-clock {time.time() - t0:.0f} s", flush=True)
