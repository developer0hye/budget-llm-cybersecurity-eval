#!/usr/bin/env python3
"""Agentic axis: run the MODELS from models.py on Cybench via inspect_evals.

Usage (see agentic/requirements.txt for the pinned harness):
    export OPENROUTER_API_KEY=sk-or-... CYBENCH_ACKNOWLEDGE_RISKS=1
    python3 agentic/run_cybench.py --pilot                      # 3 challenges x 1 epoch, 1 model
    python3 agentic/run_cybench.py                              # full run: 1 epoch, $2.10 cap

Protocol follows arXiv:2607.15263 section 3.1, the published run this axis
anchors to: inspect_evals `cybench` (version 4-C, "hard" variant, 39
challenges), its default ReAct agent (bash + python tools with 180 s
timeouts, 3 submission attempts) and a $2.10 per-sample cost cap.
Differences, all disclosed in the README: 1 epoch instead of 3; reasoning
`enabled: true` (OpenRouter medium effort) for every model, where the paper
ran GPT-5.6 at high effort; the k8s sandbox's allowlist minus code hosts;
and the per-call and per-sample safety stops below.

Each model is pinned to the same single provider as the knowledge axis
(models.PROVIDER, fallbacks off). Solar Pro 4 and DeepSeek V4.1 Flash are not
in Inspect's model database, so every model's context length and
pinned-provider price are registered here -- `cost_limit` needs a price to
fire.

Each invocation writes a new Inspect log per model under <log-dir>/<model>/.
It does not resume: re-running starts a fresh eval. Re-runs of individual
challenges go in a subfolder, and agentic/analyze_cybench.py merges them,
taking the newest non-error result per challenge (never best-of-runs).
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
from inspect_ai.util import SandboxEnvironmentSpec  # noqa: E402
import yaml  # noqa: E402

# inspect-k8s-sandbox 0.13.0 (latest on PyPI, 2026-09-25) parses `helm version
# --short` without stripping the trailing newline, so every helm version fails
# its SemVer check ("3.22.0+g144ca65\n is not valid SemVer string").
import k8s_sandbox._prereqs as _k8s_prereqs  # noqa: E402

_parse_helm_version = _k8s_prereqs._parse_version
_k8s_prereqs._parse_version = lambda v: _parse_helm_version(v.strip())
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

# Removed from every challenge's k8s allow_domains list. The rest of the list
# (package mirrors) is kept, so installs behave as in the paper's k8s runs;
# only public code hosts, where challenge sources and solutions are posted,
# become unreachable. See README, "Network policy".
BLOCKED_DOMAINS = {"github.com", "raw.githubusercontent.com", "bitbucket.org"}
# Kali's http.kali.org redirects each apt request to a mirror chosen per
# request and client location (from this host: 11 different KR mirrors), so
# the upstream list's single mirror.vinehost.net does not cover it and apt
# failed in the sandbox (flag_command's reference solution, 2026-09-25). All
# mirrors from Kali's published list are allowed; they serve distro packages.
EXTRA_ALLOWED_DOMAINS = [
    ln.strip() for ln in (Path(__file__).parent / "kali_mirrors.txt").read_text().splitlines()
    if ln.strip() and not ln.startswith("#")
]


def k8s_without_code_hosts(sandbox_type: str, sample) -> SandboxEnvironmentSpec:
    """k8s sandbox spec using a copy of the challenge's compose file minus BLOCKED_DOMAINS."""
    src = Path(sample.sandbox.config)
    compose = yaml.safe_load(src.read_text())
    ext = compose.setdefault("x-inspect_k8s_sandbox", {})
    kept = [d for d in ext.get("allow_domains", []) if d not in BLOCKED_DOMAINS]
    # Cilium rejects duplicate serverNames, and kali.download is in both lists.
    ext["allow_domains"] = list(dict.fromkeys(kept + EXTRA_ALLOWED_DOMAINS))
    out = src.with_name("nocodehost-compose.yaml")  # name must end in compose.yaml for k8s_sandbox to convert it
    out.write_text(yaml.safe_dump(compose, sort_keys=False))
    return SandboxEnvironmentSpec(type="k8s", config=str(out))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="*", default=list(MODELS), choices=list(MODELS))
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--cost-limit", type=float, default=2.10, help="$ per sample (one challenge x one epoch)")
    p.add_argument("--stream-idle-timeout", type=int, default=120,
                   help="Abandon and retry a model call only after this many seconds with NO streamed "
                        "output. Replaces the 300 s total-time attempt_timeout as the hang detector: "
                        "that cap also killed calls still streaming reasoning (GLM/Solar run at ~42 "
                        "out-tok/s, so a 15k-token turn needs ~360 s; 110/113 GLM call errors were it)")
    p.add_argument("--attempt-timeout", type=int, default=900,
                   help="Abandon and retry a model call after this many seconds. The first cost pilot "
                        "(2026-09-25) had 3 of 8 Solar Pro 4 calls return HTTP 200 headers and then no body "
                        "for 10-18 min; with no timeout a sample waits forever and cost_limit never fires")
    p.add_argument("--working-limit", type=int, default=3600,
                   help="Seconds of working time per sample (model + tool time); a safety stop, not a budget")
    p.add_argument("--time-limit", type=int, default=3600,
                   help="Wall-clock seconds per sample. Needed because working_limit does not count time "
                        "spent in provider retries/backoff, so a non-terminating model (GLM 5.3 Flash) can "
                        "hang for hours of wall-clock while under the working-time cap")
    p.add_argument("--max-sandboxes", type=int, default=8,
                   help="Concurrent challenge sandboxes; the agent container alone has mem_limit 2g")
    p.add_argument("--challenges", nargs="*", default=None, help="Subset of Cybench eval_names")
    p.add_argument("--pilot", action="store_true", help=f"1 epoch of {PILOT_CHALLENGES} on the first model")
    p.add_argument("--sandbox", choices=["k8s", "docker"], default="k8s",
                   help="k8s: allowlisted egress minus code hosts (the protocol). docker: unrestricted egress")
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
            cybench(eval_names=args.challenges, sandbox_type=args.sandbox,
                    sandbox_config=k8s_without_code_hosts if args.sandbox == "k8s" else None),
            model=f"openrouter/{model_id}",
            model_args={
                "provider": {"only": [PROVIDER[model_id]], "allow_fallbacks": False},
                "reasoning_enabled": True,
            },
            epochs=args.epochs,
            cost_limit=args.cost_limit,
            working_limit=args.working_limit,
            time_limit=args.time_limit,
            attempt_timeout=args.attempt_timeout,
            stream_idle_timeout=args.stream_idle_timeout,
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
