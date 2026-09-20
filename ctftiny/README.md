# CTF-Solving Agent Evaluation (Phase 2)

Companion evaluation to the [CyberMetric budget-model comparison](../README.md)
in this repo. CyberMetric measures cybersecurity *knowledge* (multiple-choice
QA); this directory measures practical CTF-*solving* skill for the same 5
budget-tier models, using an autonomous tool-using agent against real CTF
challenges in a Docker sandbox — built on two existing open-source projects
from NYU's LLM-CTF group rather than a harness written from scratch.

All 5 models were run on the full 200-challenge NYU CTF Bench test split, and
4 of them (all but GLM 5.3 Flash, whose reasoning is mandatory) were re-run
with reasoning explicitly controlled after an audit found the original run
never set it. Read [Limitations](#limitations) before citing any ranking
from this project.

## Key findings

- **The reasoning-controlled comparison (the correct one to cite) is n=80,
  all-4-models-attempted, reasoning uniformly off**: DeepSeek V4.1 Flash
  solves significantly more challenges than the other 3 models (p ≤ 0.023
  against each); Solar Pro 4 is *not* significantly different from Qwen3.8
  Flash (p=0.070) or GPT-5.6 Luna (p=0.109); Qwen3.8 Flash and GPT-5.6 Luna
  are statistically tied (p=1.000). See [Results](#results-reasoning-controlled-comparison-n80).
- **Reasoning significantly improves CTF-solving for 3 of 4 testable
  models** (Qwen3.8 Flash p=0.0001, DeepSeek V4.1 Flash p=0.0003, GPT-5.6
  Luna p<0.0001) but has no measurable effect on Solar Pro 4 (p=0.125),
  even though its forced-on reasoning was verified to actually engage.
- **An earlier, uncontrolled full-200 run found Solar Pro 4 significantly
  worse than all 4 other models.** That finding does not fully replicate
  once reasoning is held constant — it was partly an artifact of each
  model defaulting to a different, unset reasoning rate (0%–100%,
  measured). The DeepSeek advantage does replicate under control; the
  Solar Pro 4 deficit against Qwen3.8 Flash and GPT-5.6 Luna does not.
- **Absolute solve rates (10–39% of attempted) exceed 2024's tool-enhanced
  SOTA (EnIGMA, 13.5%) and approach a CTF-specialized fine-tune (CTF-Dojo,
  31.9%)**, despite a weaker harness and a harsher 1-attempt/12-round
  protocol. Read as a likely training-data-contamination signal (these are
  public 2017–2023 challenges with public writeups), not a capability
  claim — see [Comparison to published literature](#comparison-to-published-literature).
- **Data quality**: three distinct operational incidents during the
  original run (disk exhaustion, a missing Docker network, and orphaned
  processes from a mid-run Docker restart) produced an uneven
  "attempted" count per model (83–175 of 200); all three are diagnosed,
  documented, and corrected for — see [Limitations](#limitations) and
  [Appendix B](#appendix-b-operational-incident-log).

## Methodology

- **Harness**: [nyuctf_agents][nyuctf-agents]' baseline single-agent tool-use
  loop (official NYU CTF Bench baseline, not the more complex D-CIPHER
  planner/executor variant), routed through OpenRouter so all 5 models run
  through identical code. See [Architecture](#architecture--implementation)
  for what was modified and why.
- **Challenge set**: the full 200-challenge NYU CTF Bench test split
  ([arXiv:2406.05590](https://arxiv.org/abs/2406.05590), NeurIPS'24 D&B) —
  real CSAW-derived pwn/rev/web/crypto/misc/forensics challenges in a
  Docker sandbox with radare2, sqlmap, apktool, jadx, Ghidra, etc.
- **Protocol**: 1 attempt per (model, challenge), `max_rounds=12`,
  `max_cost=$1.5`, single flag submission — harsher than most published
  baselines (see [literature comparison](#comparison-to-published-literature)).
- **Reasoning conditions**: OpenRouter's `reasoning` parameter was not set
  explicitly in the original run, so each model used its provider default.
  Trajectory sampling found this defaulted to 0% (Solar Pro 4) up to 100%
  (Qwen3.8 Flash) reasoning usage across models — a confound for any
  cross-model comparison. A follow-up run adds explicit reasoning control
  (`extra_body: {"reasoning": {"enabled": true|false}}`) and re-runs Solar
  Pro 4 with reasoning forced on, and Qwen3.8 Flash / DeepSeek V4.1 Flash /
  GPT-5.6 Luna with reasoning forced off (GLM 5.3 Flash excluded — cannot
  disable reasoning, confirmed in the CyberMetric project).
- **Statistical approach**: every model attempts the same challenge pool,
  so pairwise comparisons use **McNemar's exact test** on the challenges
  both models in a pair actually attempted, not a raw solve-rate gap. See
  [Limitations](#limitations) for the multiple-comparisons and
  attempted-count caveats that apply to every result below.

## Results: reasoning-controlled comparison (n=80)

This is the **primary, citable comparison** in this project — the only one
where reasoning is held constant across models. It restricts to the **80
challenges all 4 non-GLM models attempted with reasoning uniformly off**
(Solar Pro 4's provider default is a verified 0% reasoning rate; Qwen3.8
Flash, DeepSeek V4.1 Flash, and GPT-5.6 Luna were re-run with reasoning
explicitly forced off — GLM 5.3 Flash is excluded, its reasoning cannot be
disabled).

| Model | Solved (of 80) | Solve rate |
|---|---|---|
| DeepSeek V4.1 Flash | 24 | 30.0% |
| Qwen3.8 Flash | 15 | 18.8% |
| GPT-5.6 Luna | 15 | 18.8% |
| Solar Pro 4 | 9 | 11.3% |

Pairwise McNemar exact test within this fixed n=80:

| Pair | b, c | p |
|---|---|---|
| DeepSeek V4.1 Flash vs Solar Pro 4 | 15, 0 | **0.0001** |
| DeepSeek V4.1 Flash vs Qwen3.8 Flash | 11, 2 | **0.0225** |
| DeepSeek V4.1 Flash vs GPT-5.6 Luna | 11, 2 | **0.0225** |
| Qwen3.8 Flash vs Solar Pro 4 | 7, 1 | 0.070 |
| GPT-5.6 Luna vs Solar Pro 4 | 8, 2 | 0.109 |
| Qwen3.8 Flash vs GPT-5.6 Luna | 6, 6 | 1.000 |

**Interpretation**: DeepSeek V4.1 Flash has a significant, reasoning-
independent CTF-solving advantage over all 3 other testable models. Solar
Pro 4 is *not* significantly worse than Qwen3.8 Flash or GPT-5.6 Luna once
reasoning is controlled — it is only significantly worse than DeepSeek.
This revises the uncontrolled full-run finding below, where Solar Pro 4
appeared significantly worse than all 4 other models: 2 of those 4 pairwise
differences (vs. Qwen, vs. Luna) do not survive reasoning control; the
difference vs. DeepSeek does (and remains similarly strong). GLM 5.3 Flash
cannot be placed in this comparison at all, since its reasoning cannot be
disabled to match the other 4.

This comparison inherits the attempted-count caveat from the uncontrolled
run below — it uses each model's *attempted* subset (not the full 200) —
see [Limitations](#limitations).

## Results: does reasoning help, per model

Paired McNemar's test, same challenges, reasoning on vs. off:

| Model | n (common attempted) | b, c | p | Verdict |
|---|---|---|---|---|
| Solar Pro 4 (off→on) | 81 | 1, 6 | 0.125 | not significant |
| Qwen3.8 Flash (on→off) | 131 | 21, 2 | **0.0001** | reasoning helps |
| DeepSeek V4.1 Flash (on→off) | 162 | 23, 4 | **0.0003** | reasoning helps |
| GPT-5.6 Luna (on→off) | 156 | 22, 2 | **<0.0001** | reasoning helps |

Full per-condition solve rates:

| Model | Condition | Attempted | Solved | Solve rate | Cost |
|---|---|---|---|---|---|
| Solar Pro 4 | default (0% reasoning) | 83 | 9 | 10.8% | $0.70 |
| Solar Pro 4 | reasoning forced **on** | 147 | 19 | 12.9% | $1.74 |
| Qwen3.8 Flash | default (~100% reasoning) | 134 | 40 | 29.9% | $1.55 |
| Qwen3.8 Flash | reasoning forced **off** | 172 | 22 | 12.8% | $1.27 |
| DeepSeek V4.1 Flash | default (~97% reasoning) | 169 | 59 | 34.9% | $1.62 |
| DeepSeek V4.1 Flash | reasoning forced **off** | 163 | 39 | 23.9% | $1.21 |
| GPT-5.6 Luna | default (~36% reasoning) | 175 | 40 | 22.9% | $3.38 |
| GPT-5.6 Luna | reasoning forced **off** | 156 | 19 | 12.2% | $1.91 |

**Reasoning meaningfully helps CTF-solving for 3 of 4 models; Solar Pro 4
is the outlier.** A manipulation check (sampled 15 trajectory files per
re-run) confirms the forced settings actually took effect: Solar Pro 4's
forced-on run reasoned on 171/171 (100%) sampled turns; the three
forced-off re-runs reasoned on 0/175, 1/184, and 0/186 sampled turns
(Qwen/DeepSeek/Luna) — so Solar Pro 4's null result is a genuine finding,
not a broken flag. This contrasts with [Part 1's CyberMetric
result](../README.md#does-reasoning-help-accuracy), where reasoning has no
measurable effect for *any* model — reasoning helps on this agentic,
multi-step task in a way it doesn't on closed-book MCQ.

Total cost of the reasoning-controlled re-runs: $1.74 + $1.27 + $1.21 +
$1.91 = **$6.13**, on top of the original $8.27 full-run cost.

## Results: uncontrolled full-200 run (2026-09-19)

The original run, before reasoning was controlled. Included for its larger
per-model sample (up to 200 vs. the 80 above) and because it's the source
of the "attempted" imbalance discussed in [Limitations](#limitations); the
[reasoning-controlled comparison](#results-reasoning-controlled-comparison-n80)
above is the one to cite for cross-model claims.

| Model | Attempted/200 | Solved | Solve rate (of attempted) | Avg wall time | Total cost |
|---|---|---|---|---|---|
| DeepSeek V4.1 Flash | 169 | 59 | 34.9% | 322s | $1.62 |
| GLM 5.3 Flash | 118 | 46 | 39.0% | 263s | $1.03 |
| Qwen3.8 Flash | 134 | 40 | 29.9% | 219s | $1.55 |
| GPT-5.6 Luna | 175 | 40 | 22.9% | 164s | $3.38 |
| Solar Pro 4 | 83 | 9 | 10.8% | 86s | $0.70 |

Total cost across all 5 models, 1000 jobs: **$8.27**. Full per-run data:
[`eval_results_full.jsonl`](eval_results_full.jsonl) (1000 rows),
aggregated in [`eval_summary_full.json`](eval_summary_full.json).

**Attempted counts are not a clean denominator** (83–175 of 200) — the
imbalance correlates with which incident windows each model's job queue
passed through (see [Appendix B](#appendix-b-operational-incident-log)),
not random noise or model capability. Restricting to the **61 challenges
all 5 models actually attempted** controls for this directly:

| Model | Solved (of 61) | Solve rate |
|---|---|---|
| DeepSeek V4.1 Flash | 29 | 47.5% |
| GLM 5.3 Flash | 25 | 41.0% |
| Qwen3.8 Flash | 24 | 39.3% |
| GPT-5.6 Luna | 22 | 36.1% |
| Solar Pro 4 | 8 | 13.1% |

Pairwise McNemar within this n=61 set:

| Pair | b, c | p |
|---|---|---|
| Solar Pro 4 vs DeepSeek V4.1 Flash | 0, 21 | **<0.0001** |
| Solar Pro 4 vs GLM 5.3 Flash | 0, 17 | **<0.0001** |
| Solar Pro 4 vs GPT-5.6 Luna | 1, 15 | **0.0005** |
| Qwen3.8 Flash vs Solar Pro 4 | 17, 1 | **0.0001** |
| GPT-5.6 Luna vs DeepSeek V4.1 Flash | 2, 9 | 0.065 |
| Qwen3.8 Flash vs DeepSeek V4.1 Flash | 2, 7 | 0.180 |
| every other pair | — | ≥0.29 |

At the time this was the headline result: Solar Pro 4 significantly worse
than every other model (this includes GLM 5.3 Flash, which is not part of
the reasoning-controlled comparison above), the other 4 statistically
indistinguishable from each other. **As established in
[Results: reasoning-controlled comparison](#results-reasoning-controlled-comparison-n80),
this was confounded by uncontrolled reasoning settings** — 2 of the 3
significant pairs against Solar Pro 4 that involve a reasoning-controllable
model (vs. Qwen, vs. Luna) do not survive once reasoning is held constant;
the comparison against DeepSeek does. GLM 5.3 Flash cannot be re-tested
under reasoning control at all, so its significant pairing against Solar
Pro 4 here neither replicates nor is contradicted — it's simply untested
under control.

## Comparison to published literature

| Source | Model | Method | Solve rate on NYU CTF Bench (200) |
|---|---|---|---|
| [Original paper](https://arxiv.org/html/2406.05590v2) (2024) | GPT-4 | Same baseline harness, 5 attempts/challenge, 48h budget | ~3.7% (best of the paper's models) |
| [EnIGMA](https://arxiv.org/html/2409.16165) (2024) | Claude 3.5 Sonnet | Enhanced tool-use agent, pass@1, $3 budget | 13.5% (SOTA at publication) |
| [CTF-Dojo](https://arxiv.org/pdf/2508.18370) (2025) | 32B, fine-tuned on 486 execution-verified CTF trajectories | pass@1 | 31.9% |
| This project | 5 budget-tier models | Same baseline harness as the original paper, 1 attempt, 12 rounds | 10.8%–39.0% |

**Read this as a caveat about the numbers in this project, not a
capability claim.** Every model here scores at or above the 2024
SOTA-with-better-tooling (EnIGMA), and most score near or above CTF-Dojo's
number — a model *specifically fine-tuned* on CTF-solving trajectories —
despite using the *weaker* plain baseline harness (no tool-use
enhancements) and a *harsher* protocol (1 attempt / 12 rounds vs. the
original paper's 5 attempts / 48 hours). That combination is hard to
explain by "these models got better at reasoning" alone. The more likely
explanation is **training-data contamination**: these are real 2017–2023
CTF competition challenges with public writeups, and a 2026-era model has
had far more opportunity to see them during training than GPT-4/Claude 3
(2023–2024 training cutoffs). Treat the absolute solve-rate numbers in
this project as upper bounds on genuine problem-solving capability, not
clean measurements of it.

## Limitations

- **The "attempted" denominator is uneven across models** (83–175 of 200
  in the uncontrolled run; 83–172 in the reasoning-controlled comparison)
  because of three operational incidents during data collection, not
  model capability — see [Appendix B](#appendix-b-operational-incident-log).
  Every headline comparison in this project restricts to a fixed common
  subset (n=61 or n=80) to control for this directly, but neither subset
  is guaranteed to be a representative (vs. easier- or harder-than-average)
  sample of the full 200; only a uniform re-run of all jobs under identical
  conditions would fully resolve this, and that hasn't been done.
- **GLM 5.3 Flash cannot be included in any reasoning-controlled
  comparison** — its reasoning is mandatory and cannot be disabled via the
  API. It remains in the uncontrolled full-run numbers only.
- **Multiple comparisons.** The n=61 and n=80 tables each run 6 pairwise
  tests; treat p-values in the 0.01–0.05 range as suggestive. Unlike the
  CyberMetric side of this project, a formal Bonferroni correction is not
  applied here — apply your own correction before citing a specific pair
  as significant in a downstream context.
- **Training-data contamination risk** likely inflates absolute solve
  rates for all 5 models roughly equally (all trained on similar-vintage
  web data) — see [Comparison to published literature](#comparison-to-published-literature).
  This affects the credibility of absolute numbers more than relative
  model-to-model comparisons.
- **CTFJudge/CCI trajectory-quality scoring has not been run** on any
  trajectory from either run — the results above are solve-rate only
  (binary flag capture), not a measure of solution quality or efficiency.
  See [Status & future work](#status--future-work).
- **Small-sample pilot (n=10, see Appendix A) is retained for provenance
  only** — no pair in that sample reaches p<0.10; do not cite its ranking.

## Architecture & implementation

- [`nyuctf_agents/`](nyuctf_agents/) — vendored, modified copy of
  [NYU-LLM-CTF/nyuctf_agents][nyuctf-agents] (MIT, upstream commit
  `612190f`). Runs an LLM agent against real CTF challenges inside a Docker
  container (radare2, sqlmap, nikto, apktool, jadx, Ghidra, etc.) and logs
  the full tool-call trajectory. Chosen as the official baseline/D-CIPHER
  harness for NYU CTF Bench — actively maintained, 163★.
- [`CTFJudge/`](CTFJudge/) — vendored, modified copy of
  [NYU-LLM-CTF/CTFJudge](https://github.com/NYU-LLM-CTF/CTFJudge) (upstream
  commit `1eef031`), an LLM-as-judge scorer purpose-built for grading CTF
  *trajectories* (not just final-flag correctness) against a reference
  writeup, producing a CCI ("competency/completeness index") score — a
  process-quality metric that a pure solve-rate number misses. Upstream
  has no `LICENSE` file as of this fork; treated as source-available for
  evaluation purposes only, not redistributed under a stated license. Both
  vendored projects' own `.git` history was dropped on import (no local
  commits existed in either, verified before deletion); this repo tracks
  modifications as plain diffs against the upstream commits noted above.
- [`adapt_baseline_trajectory.py`](adapt_baseline_trajectory.py) — format
  adapter between the two projects' incompatible trajectory shapes (see
  below).
- [`run_full_eval.py`](run_full_eval.py) / [`run_solarpro4_reasoning.py`](run_solarpro4_reasoning.py) /
  [`run_reasoning_off.py`](run_reasoning_off.py) — drivers for the
  full-200, reasoning-on, and reasoning-off runs respectively.

**What was modified in the vendored code, and why:**

1. **OpenRouter routing (both projects).** Both projects hard-code the
   Anthropic/OpenAI SDKs against their default endpoints. All calls in this
   fork route through OpenRouter so the same code runs any of the 5
   budget-tier models — including non-OpenAI/non-Anthropic ones — without a
   separate backend per provider. `openai_backend.py` points `base_url` at
   `https://openrouter.ai/api/v1` when `OPENROUTER_API_KEY` is set (falls
   back to real OpenAI if only `OPENAI_API_KEY` is set). `CTFJudge`'s
   agents were ported from the Anthropic SDK to the OpenAI SDK pointed at
   OpenRouter, with the judge model set to `anthropic/claude-sonnet-5` per
   the original CTFJudge paper's choice of a Claude Sonnet judge.
2. **Explicit reasoning control.** `openai_backend.py` and
   `run_baseline.py` now support a tri-state `reasoning_enabled` (`None` =
   untouched upstream behavior — provider default; `True`/`False` = forced
   via OpenRouter's `extra_body: {"reasoning": {"enabled": ...}}`). This is
   what enabled the reasoning-controlled re-run above; upstream has no such
   parameter at all.
3. **Real cost tracking.** Upstream's local cost estimate only counted
   tokens in the current turn's new message, silently ignoring that every
   round resends the full conversation history — undercounting real spend
   by roughly two orders of magnitude in a multi-round conversation. Cost
   now reads OpenRouter's authoritative `response.usage.cost` (server-side,
   computed from real token counts) as the primary source, falling back to
   the old local estimate only when `.cost` isn't present.
4. **Upstream bug fixes**: a `keys.cfg`-missing crash (catches the wrong
   exception type — worked around rather than patched, since it doesn't
   affect OpenRouter runs); several imported-but-not-declared dependencies
   in `requirements.txt`; a Docker build that fails on Apple Silicon
   without an explicit `--platform linux/amd64` (arm64 resolves i386
   packages against a mirror that doesn't carry them).

**Format adapter.** nyuctf_agents (baseline) and CTFJudge (built for
D-CIPHER) use incompatible trajectory shapes:

| | baseline output | CTFJudge/D-CIPHER expects |
|---|---|---|
| top-level fields | `solved`, `cost`, `runtime.total`, `finish_reason` | `success`, `total_cost`, `time_taken`, `exit_reason` |
| conversation | flat `messages: [[timestamp, {role, content, tool_calls: [...]}], ...]`, OpenAI chat format | `planner`/`executors` lists of `{role: "MessageRole.X", index, content, tool_call: {...} \| tool_result: {...}}` |
| tool calls per turn | plural `tool_calls` (OpenAI parallel tool calling) | singular `tool_call` — one per entry |
| tool results | `role: "tool"` messages, JSON-stringified `content` | separate `MessageRole.OBSERVATION` entries with a nested `tool_result.result` dict |

`adapt_baseline_trajectory.py` converts one into the other: the whole
baseline conversation goes into CTFJudge's `"planner"` list (baseline has
no planner/executor split; `"executors"` is left `[]`, confirmed safe since
CTFJudge's config marks it optional with no code indexing into it); a
single baseline turn with multiple tool calls splits into multiple
synthetic entries (only the first keeps the turn's reasoning text, to
avoid duplicating it once per tool call); tool output is stripped of ANSI
color codes before being passed to the judge LLM. Required zero changes to
CTFJudge's own code — verified by loading adapted output through
CTFJudge's own `TrajectoryDecomposer` and confirming correct metadata, a
correctly rendered conversation, no duplicated reasoning, and no stray
executor-agent section.

```bash
python3 adapt_baseline_trajectory.py \
  nyuctf_agents/logs_baseline/<user>/<experiment>/<challenge>.json \
  CTFJudge/trajs/<challenge>.json
```

## Setup

```bash
cd nyuctf_agents
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install "ToolDefGenerator @ git+https://github.com/moyix/ToolDefGenerator@main" \
  jinja2 bs4 lxml ruamel.yaml   # missing from requirements.txt upstream
touch keys.cfg                  # works around an upstream FileExistsError/FileNotFoundError bug

# Ghidra (not vendored, ~1GB download):
wget https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.0.1_build/ghidra_11.0.1_PUBLIC_20240130.zip
unzip ghidra_11.0.1_PUBLIC_20240130.zip && rm ghidra_11.0.1_PUBLIC_20240130.zip

# Docker CTF environment (needs --platform on Apple Silicon, see above)
cd docker/baseline
docker build --platform linux/amd64 --build-arg HOST_UID=$(id -u) -t ctfenv .

export OPENROUTER_API_KEY=sk-or-v1-...
python3 run_baseline.py --config configs/baseline/qwen38flash_config.yaml --challenge <name>
```

```bash
cd ../CTFJudge
uv venv && source .venv/bin/activate
uv pip install openai python-dotenv
export OPENROUTER_API_KEY=sk-or-v1-...
python3 run_evaluation.py --trajectory trajs/<challenge>.json --writeup writeups/<challenge>.txt
```

**Reproducing the full-200 run**: `python3 run_full_eval.py` (concurrency
6, ~several hours wall clock, port-locked so challenges sharing a
docker-compose host port don't race each other). **Reproducing the
reasoning-controlled re-run**: `python3 run_solarpro4_reasoning.py` and
`python3 run_reasoning_off.py`.

## Status & future work

Complete: full-200 run (all 5 models), reasoning-controlled re-run (4 of 5
models), n=10 pilot sample, format adapter (verified against CTFJudge's own
parsing code). **Total cost across all phase 2 runs: $14.85** ($8.27
full-200 + $0.45 n=10 pilot + $6.13 reasoning-controlled).

Not yet done:

- **A uniform full re-run of all 1000 jobs under identical
  post-stabilization conditions** — the only fix that would fully resolve
  the attempted-count caveat rather than control for it on a fixed subset.
- **End-to-end CCI scoring via CTFJudge** on any of the ~1200 trajectories
  produced across all runs — needs a challenge with both a trajectory and
  an existing reference writeup (`2023q-web-smug_dino` qualifies and is the
  natural next challenge to score); blocked on writeups not existing for
  most challenges in `CTFJudge/writeups/`.
- **Token/cost calibration for the agent harness itself** — the
  CyberMetric project's `calibrate_tokens.py` has no agentic-harness
  equivalent yet.

## Appendix A: preliminary pilot sample (n=10, superseded)

An earlier 10-challenge pilot run (2 per category, `random.seed(42)`, 12
sampled minus 2 symmetrically excluded for a port-5000 conflict — see
below), kept for provenance. **Superseded by the full-200 and
reasoning-controlled results above for any ranking claim** — no pairwise
comparison in this sample reaches even p<0.10.

| Model | Solved | Solve rate | Avg wall time/run | Total cost (10 runs) |
|---|---|---|---|---|
| Qwen3.8 Flash | 4/10 | 40% | 133s | $0.0834 |
| DeepSeek V4.1 Flash | 3/10 | 30% | 226s | $0.0857 |
| GLM 5.3 Flash | 3/10 | 30% | 298s | $0.0930 |
| GPT-5.6 Luna | 2/10 | 20% | 108s | $0.0927 |
| Solar Pro 4 | 0/10 | 0% | 111s | $0.0934 |

Total cost, all 5 models, 60 jobs: $0.4482. Pairwise McNemar: largest gap
(Qwen3.8 Flash vs. Solar Pro 4, 40% vs. 0%) gives b=4, c=0, p=0.125; every
other pair p≥0.25. Two of the 12 sampled challenges
(`2021q-cry-ecc_pop_quiz`, `2021f-for-no_time_to_register`) hardcode host
port 5000, which macOS's AirPlay Receiver occupies by default — excluded
symmetrically for all 5 models, leaving n=10. Full data:
[`eval_results.jsonl`](eval_results.jsonl) (60 rows),
[`eval_summary.json`](eval_summary.json). Reproduce: `python3
run_all_models.py` (~60–90 min wall clock, concurrency 3).

## Appendix B: operational incident log

Data-quality detail behind the "attempted" imbalance in the uncontrolled
full-200 run — included for transparency and reproducibility, not required
reading to use the results above.

1. **Disk exhaustion (ENOSPC), 2 crashes.** Docker Desktop's VM disk
   (`Docker.raw`) grew unboundedly from challenge-image pulls and didn't
   reliably shrink when images were deleted inside it. Fixed by relocating
   Docker's data directory to external SSD storage with far more headroom.
2. **Missing Docker network.** The `ctfnet` bridge network the agent's
   container joins doesn't persist across a fresh Docker VM (upstream
   creates it once, by hand, via a setup script). After the disk-relocation
   restart, this silently failed the base environment container for every
   model until caught; the driver now creates it automatically if missing.
3. **Orphaned processes from a mid-run Docker force-restart.** The
   `docker kill -9` used to force-restart Docker Desktop as part of fixing
   (1) killed 5 in-flight Solar Pro 4 conversations mid-tool-call. Because
   the run configuration had a `skip_exist` safety flag set (added for
   resumability after the disk crash), the next attempt at those exact
   (model, challenge) pairs silently reused the broken partial log instead
   of running fresh. Detected via a wall-time signature (all 5 clustered at
   0.84–0.88s, impossible for a real Docker-based run) cross-checked
   against every `finish_reason: unknown` row in the dataset (19 total;
   only these 5 matched the signature — the other 14 are genuine API-level
   failures). These 5 rows were reclassified from "attempted" to
   infra-failure and **deliberately not retried** — retrying only failures
   would be selection on the outcome (an unequal "second, easier attempt"
   across models), a new confound in itself. The same `skip_exist` flag
   also produced a separate, fully bogus re-run of the n=10 pilot sample
   (silently reused a prior run's logs, caught by a `wall_time_s` /
   `runtime_total` mismatch) before being disabled for good.

Rows corrupted by incidents 1 and 2 (8 + 71 rows) were identified by error
signature and given a real retry, since those failures were transient
infrastructure issues unrelated to model behavior. Rows corrupted by
incident 3 (5 rows, all Solar Pro 4) were reclassified but not retried, per
the reasoning above. Full detection logic is in the commit history
(`8820d01`, `a8b2c41`).

A post-incident spot-check (re-running one of Solar Pro 4's failed
challenges by hand, cache warm, no concurrent load) succeeded — meaning at
least some of the remaining `no_log` count per model is recoverable
transient failure rather than a permanently broken challenge environment,
which is the basis for the "uniform full re-run" item in
[Status & future work](#status--future-work).

[nyuctf-agents]: https://github.com/NYU-LLM-CTF/nyuctf_agents
