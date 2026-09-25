#!/usr/bin/env python3
"""Agentic axis: run the MODELS from models.py on Cybench via inspect_evals.

Usage (see agentic/requirements.txt for the pinned harness):
    export OPENROUTER_API_KEY=sk-or-... CYBENCH_ACKNOWLEDGE_RISKS=1
    python3 agentic/run_cybench.py --pilot                      # 3 challenges x 1 epoch, 1 model
    python3 agentic/run_cybench.py --epochs 3 --cost-limit 2.10 # full run

Protocol follows arXiv:2607.15263 section 3.1, the published run this axis
anchors to: inspect_evals `cybench` (version 4-C, "hard" variant, 39
challenges), its default ReAct agent (bash + python tools with 180 s
timeouts, 3 submission attempts), a per-sample cost cap, 3 epochs. The one
deliberate difference: reasoning is `enabled: true` (OpenRouter medium
effort) for every model, as on the knowledge axis; the paper ran GPT-5.6 at
high effort.

Each model is pinned to the same single provider as the knowledge axis
(models.PROVIDER, fallbacks off). Solar Pro 4 and DeepSeek V4.1 Flash are not
in Inspect's model database, so every model's context length and
pinned-provider price are registered here -- `cost_limit` needs a price to
fire.

One Inspect log per model lands in <log-dir>/<model>/; re-running the same
command resumes from it (eval_retry semantics are Inspect's own).
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from models import MODELS, PROVIDER  # noqa: E402

from inspect_ai import eval as inspect_eval  # noqa: E402
from inspect_ai.model import ModelCost, ModelInfo, set_model_info  # noqa: E402
from inspect_evals.cybench import cybench  # noqa: E402

# Pinned-provider endpoint data from OpenRouter's /models/<id>/endpoints,
# fetched 2026-09-25. Prices in $ per 1M tokens.
ENDPOINTS = {
    "upstage/solar-pro4": dict(context=524288, output=131072, cost=ModelCost(
        input=0.09, output=0.36, input_cache_read=0.018, input_cache_write=0.09)),
    "openai/gpt-5.6-luna": dict(context=1050000, output=128000, cost=ModelCost(
        input=0.20, output=1.20, input_cache_read=0.02, input_cache_write=0.25)),
    "openai/gpt-6-luna": dict(context=1050000, output=128000, cost=ModelCost(
        input=0.10, output=0.50, input_cache_read=0.01, input_cache_write=0.125)),
    "deepseek/deepseek-v4.1-flash": dict(context=1024000, output=384000, cost=ModelCost(
        input=0.165, output=0.66, input_cache_read=0.0033, input_cache_write=0.165)),
    "z-ai/glm-5.3-flash": dict(context=1048576, output=131072, cost=ModelCost(
        input=0.15, output=0.50, input_cache_read=0.03, input_cache_write=0.15)),
}
PILOT_CHALLENGES = ["dynastic", "flag_command", "primary_knowledge"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="*", default=list(MODELS), choices=list(MODELS))
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--cost-limit", type=float, default=2.10, help="$ per sample (one challenge x one epoch)")
    p.add_argument("--attempt-timeout", type=int, default=300,
                   help="Abandon and retry a model call after this many seconds. The first cost pilot "
                        "(2026-09-25) had 3 of 8 Solar Pro 4 calls return HTTP 200 headers and then no body "
                        "for 10-18 min; with no timeout a sample waits forever and cost_limit never fires")
    p.add_argument("--working-limit", type=int, default=3600,
                   help="Seconds of working time per sample (model + tool time); a safety stop, not a budget")
    p.add_argument("--max-sandboxes", type=int, default=8,
                   help="Concurrent challenge sandboxes; the agent container alone has mem_limit 2g")
    p.add_argument("--challenges", nargs="*", default=None, help="Subset of Cybench eval_names")
    p.add_argument("--pilot", action="store_true", help=f"1 epoch of {PILOT_CHALLENGES} on the first model")
    p.add_argument("--log-dir", default="agentic/logs")
    args = p.parse_args()
    if not os.environ.get("OPENROUTER_API_KEY"):
        sys.exit("OPENROUTER_API_KEY environment variable is not set.")
    if args.pilot:
        args.models, args.epochs, args.challenges = args.models[:1], 1, PILOT_CHALLENGES

    for name in args.models:
        model_id = MODELS[name]
        ep = ENDPOINTS[model_id]
        set_model_info(f"openrouter/{model_id}", ModelInfo(
            model=model_id, context_length=ep["context"], output_tokens=ep["output"], cost=ep["cost"]))
        inspect_eval(
            cybench(eval_names=args.challenges, sandbox_type="docker"),
            model=f"openrouter/{model_id}",
            model_args={
                "provider": {"only": [PROVIDER[model_id]], "allow_fallbacks": False},
                "reasoning_enabled": True,
            },
            epochs=args.epochs,
            cost_limit=args.cost_limit,
            working_limit=args.working_limit,
            attempt_timeout=args.attempt_timeout,
            max_retries=5,
            max_sandboxes=args.max_sandboxes,
            max_samples=args.max_sandboxes,
            retry_on_error=3,
            fail_on_error=False,
            log_dir=str(ROOT / args.log_dir / name),
            display="plain",
        )


if __name__ == "__main__":
    main()
