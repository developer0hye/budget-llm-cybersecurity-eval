# CyberMetric Budget-Tier Model Comparison (KR / US / CN)

Compares the cybersecurity knowledge of 5 similarly-priced OpenRouter models
(anchored to Upstage Solar Pro 4's price tier) using the [CyberMetric][cybermetric]
benchmark, spanning Korea, the US, and China.

[cybermetric]: https://github.com/cybermetric/CyberMetric

## Results (CyberMetric-2000)

### Reasoning off (except GLM, which can't disable it) — run 2026-09-17

| Rank | Country | Model | Accuracy | Correct/Total |
|---|---|---|---|---|
| 1 | 🇨🇳 CN | GLM 5.3 Flash | 95.10% | 1902/2000 |
| 2 | 🇰🇷 KR | Solar Pro 4 | 94.75% | 1895/2000 |
| 3 | 🇨🇳 CN | Qwen3.8 Flash | 94.05% | 1881/2000 |
| 4 | 🇺🇸 US | GPT-5.6 Luna | 93.85% | 1877/2000 |
| 5 | 🇨🇳 CN | DeepSeek V4.1 Flash | 93.55% | 1871/2000 |

Gap between rank 1 and rank 5: 1.55pp.

### Reasoning explicitly on for all 5 — run 2026-09-18

| Rank | Country | Model | Accuracy | Correct/Total |
|---|---|---|---|---|
| 1 | 🇰🇷 KR | Solar Pro 4 | 94.85% | 1897/2000 |
| 1 | 🇨🇳 CN | GLM 5.3 Flash | 94.85% | 1897/2000 |
| 3 | 🇨🇳 CN | Qwen3.8 Flash | 94.35% | 1887/2000 |
| 4 | 🇨🇳 CN | DeepSeek V4.1 Flash | 94.25% | 1885/2000 |
| 5 | 🇺🇸 US | GPT-5.6 Luna | 94.10% | 1882/2000 |

Gap between rank 1 and rank 5: 0.75pp.

**Bottom line: all 5 models are statistically tied, in both conditions.**
Both gaps (1.55pp, 0.75pp) are below the ~2.2pp threshold needed for a
95%-confidence difference at n=2000 (see [Statistical notes](#statistical-notes)).
Don't read either table as "model X beats model Y" — read it as "these 5
similarly-priced models perform indistinguishably on cybersecurity knowledge
MCQs, whether or not they're allowed to reason," which is itself the finding.

### Does reasoning help? (per-model, off → on)

| Model | Reasoning off | Reasoning on | Delta |
|---|---|---|---|
| Solar Pro 4 | 94.75% | 94.85% | +0.10pp |
| GPT-5.6 Luna | 93.85% | 94.10% | +0.25pp |
| DeepSeek V4.1 Flash | 93.55% | 94.25% | +0.70pp |
| GLM 5.3 Flash | 95.10%\* | 94.85% | -0.25pp |
| Qwen3.8 Flash | 94.05% | 94.35% | +0.30pp |

\* GLM's "off" run still had reasoning on (mandatory) — its delta is test-retest
noise, not an on/off effect, and usefully shows run-to-run variance is ~0.25pp
at this sample size.

**No model shows a statistically meaningful effect from reasoning** — every
delta is under 1pp, far below the ~2-3pp needed for significance at n=2000
per arm. On a pure-knowledge MCQ benchmark like CyberMetric, letting these
models "think longer" doesn't measurably change the outcome.

## Phase 2: CTF-solving agent evaluation

CyberMetric above measures pure cybersecurity *knowledge* (MCQs). A companion
project in [`ctftiny/`](ctftiny/) measures practical CTF-*solving* skill for
the same 5 models, using NYU's [nyuctf_agents][nyuctf-agents] baseline agent
harness against real CTF challenges in a Docker sandbox, plus
[CTFJudge][ctfjudge] for trajectory grading. Full methodology, setup, and
results: [`ctftiny/README.md`](ctftiny/README.md).

[nyuctf-agents]: https://github.com/NYU-LLM-CTF/nyuctf_agents
[ctfjudge]: https://github.com/NYU-LLM-CTF/CTFJudge

### Full 200-challenge run, all 5 models, run 2026-09-19 (1000 jobs, $8.27 total)

`attempted` counts differ sharply by model (88-175/200) for reasons tied to
two operational incidents during the run (documented in `ctftiny/README.md`)
— the raw table below should **not** be read as a ranking. The clean
comparison is the 63 challenges all 5 models actually completed: there,
**Solar Pro4 solves significantly fewer than every other model**
(McNemar p<0.001 in all 4 pairwise tests against it); the other 4 models are
statistically indistinguishable from each other.

| Model | Attempted/200 | Solve rate (of attempted) | Solve rate (n=63 all-attempted) | Total cost |
|---|---|---|---|---|
| DeepSeek V4.1 Flash | 169 | 34.9% | 47.6% | $1.62 |
| GLM 5.3 Flash | 118 | 39.0% | 41.3% | $1.03 |
| Qwen3.8 Flash | 134 | 29.9% | 38.1% | $1.55 |
| GPT-5.6 Luna | 175 | 22.9% | 36.5% | $3.38 |
| Solar Pro4 | 88 | 10.2% | 12.7% | $0.70 |

**Every model here scores at or above 2024's tool-enhanced SOTA (EnIGMA +
Claude 3.5 Sonnet: 13.5%), and most score near or above a model
specifically fine-tuned for CTF-solving (CTF-Dojo: 31.9%)** — using the
*plain, weaker* baseline harness and a *harsher* protocol (1 attempt, 12
rounds) than either. That's more consistent with training-data
contamination (these are real, public 2017-2023 CTF challenges with public
writeups) than with genuine capability gains — see
[`ctftiny/README.md`](ctftiny/README.md#how-this-compares-to-the-published-literature)
for the full literature comparison and the caveats behind both tables.

## Status

- ✅ **Baseline (reasoning off, GLM mandatory-on)** — complete, 2026-09-17.
- ✅ **Reasoning-on (all 5 models)** — complete, 2026-09-18.
- ✅ **Token-budget calibration** — complete, 2026-09-18, see
  [Token budget calibration](#token-budget-calibration).
- ✅ **Phase 2 (CTF-solving agent eval)** — full 200-challenge run (1000
  jobs) complete, 2026-09-19, see above. Full CCI/CTFJudge scoring not yet
  run.

## Models under test

| Country | Model | OpenRouter ID | Released (per OpenRouter) |
|---|---|---|---|
| KR | Solar Pro 4 | `upstage/solar-pro4` | 2026-08-10 |
| US | GPT-5.6 Luna | `openai/gpt-5.6-luna` | 2026-07 |
| CN | DeepSeek V4.1 Flash | `deepseek/deepseek-v4.1-flash` | 2026-09 |
| CN | GLM 5.3 Flash | `z-ai/glm-5.3-flash` | 2026-08-28 |
| CN | Qwen3.8 Flash | `qwen/qwen3.8-flash` | 2026-08-26 |

Selection criterion: all 5 sit in roughly the same OpenRouter weighted-average
price band as Solar Pro 4 (~$0.03-0.10 input / ~$0.4-1.3 output per 1M
tokens at the time of the run — see git history of this README for the exact
numbers checked on 2026-09-17). Prices and "latest budget-tier model per
provider" drift on the order of days to weeks; re-verify before trusting an
old run's model selection.

## Benchmark: CyberMetric

[CyberMetric](https://github.com/cybermetric/CyberMetric) (Tihanyi et al.,
arXiv:2402.07688, Computer Science Symposium in Russia, 2024 — 120 citations /
13 influential citations on Semantic Scholar as of 2026-09). Multiple-choice
Q&A generated via RAG from NIST standards, RFCs, and cybersecurity textbooks,
covering 9 domains (pentest, cryptography, network/IoT security, information
security governance, compliance, cloud security, etc.), human-validated.

We use the **2000-question tier**: narrower margin of error than the
80/500-question tiers (±1.6pp vs ±3.1pp at 500) while still finishing in
~10-15 minutes, and unlike the 10000-question tier it isn't flagged by the
authors as having an estimated 2-3% label-error rate.

The dataset is **not vendored in this repo** — the upstream repo has no
LICENSE file, so redistribution rights are unclear. `download_data.sh` fetches
it fresh from `github.com/cybermetric/CyberMetric` at setup time.

## Statistical notes

When reporting results publicly: the gap between two models needs to be
roughly **2.2 percentage points or more** to be statistically meaningful at
95% confidence (this combines both models' standard errors — each model's own
accuracy has ~±1.6pp margin of error at n=2000, and comparing two adds those
in quadrature). Smaller gaps should be reported as "statistically tied," not
as one model beating another.

## Setup

```bash
git clone <this-repo>
cd cybersecurity_eval
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
./download_data.sh
cp .env.example .env   # then fill in your own OPENROUTER_API_KEY
```

## Run

The script runs all questions for all models on a single asyncio event loop,
bounded by `--concurrency` in-flight requests at a time (default 30). Results
are written incrementally as each call completes — `tail -f
results/<model>.jsonl` or `watch -n2 cat results/summary.json` to watch a run
live.

```bash
source .venv/bin/activate
export OPENROUTER_API_KEY=sk-or-...

# Smoke test: 20 questions across all 5 models (~100 calls)
python3 run_eval.py --limit 20

# Full run, reasoning off (except GLM, which can't disable it)
python3 run_eval.py

# Full run, reasoning explicitly on for all 5 models
python3 run_eval.py --reasoning on --out results_reasoning_on --concurrency 20

# Only specific models
python3 run_eval.py --models solar-pro4 glm-5.3-flash

# Push concurrency higher if you're not hitting 429s
python3 run_eval.py --concurrency 50
```

**Reproducing this run exactly**: `python3 run_eval.py --dataset
data/CyberMetric-2000-v1.json` with the `MODELS` dict as it stands in this
commit, no `--reasoning` flag (defaults to off), `--concurrency 30`. Run on
2026-09-17. Re-running later will hit whatever weights OpenRouter currently
routes those model IDs to — point releases can change silently.

## Token budget calibration

`calibrate_tokens.py` finds the smallest `max_tokens` that avoids truncated
answers (reasoning eating the whole budget, leaving `content: null`) for each
model with reasoning on, by testing a random probe sample at increasing
budgets (250 → 500 → 1000 → 2000 → 4000 → 8000) and recording actual
`completion_tokens` / `reasoning_tokens` usage at each step:

```bash
python3 calibrate_tokens.py --probe-size 30 --budgets 250 500 1000 2000 4000 8000
```

Writes `calibration/report.md` (human-readable table: recommended
`max_tokens` per model, observed max/p50 token usage) and
`calibration/report.json` (full per-budget results) plus an append-only
`calibration/calibration.log`. Kept at low concurrency (default 5) by design
so it doesn't compete for rate limit with a concurrent `run_eval.py` run.

### Results (probe_size=30, seed=42, run 2026-09-18)

| Model | Recommended `max_tokens` | Max reasoning tokens seen | p50 tokens used |
|---|---|---|---|
| Solar Pro 4 | **8000** | 4816 | 683 |
| GPT-5.6 Luna | **500** | 221 | 5 |
| DeepSeek V4.1 Flash | **2000** | 1921 | 54 |
| GLM 5.3 Flash (reasoning mandatory) | **1000** | 250 | 111 |
| Qwen3.8 Flash | **8000** | 706 | 108 |

Two clear clusters: **GPT-5.6 Luna barely reasons at all** on these questions
(p50 of 5 tokens — its default reasoning effort seems to treat simple MCQs as
not worth thinking about), while **Solar Pro 4 has a long tail** — most
questions need well under 1000 tokens (p50 683) but a handful spike past
4800, which is exactly why the full reasoning-on run above still logged 4
truncation errors at `max_tokens=4000`. Qwen3.8 Flash has the same pattern at
a smaller scale (p50 108, one outlier needing >4000). DeepSeek and GLM are
comfortably bounded (2000 and 1000 respectively cover the full probe with
zero truncations).

**Practical takeaway**: if re-running with reasoning on, use `max_tokens=8000`
for Solar Pro 4 and Qwen3.8 Flash specifically rather than one shared value
for all 5 — a single global budget either wastes headroom on the
cheap-to-reason models or still occasionally truncates the expensive ones.

## Output

- `results/<model>.jsonl` — per-question log (question, correct answer, model's answer, raw response, correctness, error, token usage)
- `results/summary.json` — per-model accuracy + token usage + `cost_usd`, plus a `_total_cost_usd` grand total; updated every 50 completions during a run
- `results_reasoning_on/summary.json` — same, for the `--reasoning on` run
- `calibration/report.md` / `report.json` — token-budget calibration results

## Cost

`run_eval.py` now records real per-call cost from OpenRouter's `usage.cost`
field (added 2026-09-18) into each `results*/summary.json` as `cost_usd` per
model plus a `_total_cost_usd` grand total, and prints it at the end of a run.
Earlier runs (both tables above) predate this and don't have per-run cost
broken out.

**Actual total spend on this project's API key as of 2026-09-18: $2.62**
(checked via `GET /api/v1/auth/key`, field `usage`). This is the key's
lifetime total, **not** just the two documented 10,000-call runs — it
includes every smoke test (`--limit 20/40/10/60` during development),
ad-hoc debugging `curl` calls, the Qwen 429 investigation, and the
`calibrate_tokens.py` probing, on top of the two full runs. Don't read $2.62
as "cost of the documented results" — read it as "total cost of building and
running this whole project." Any run from this point forward reports its own
precise cost in its `summary.json`.

Rough scale for a single full run: 2000 questions x 5 models = 10,000 calls,
~200 input tokens/question, output capped at 16 tokens for reasoning-off
(1000-8000 for reasoning-on, see [calibration](#token-budget-calibration)) —
each full run costs well under $1 at reasoning off, a few dollars at
reasoning on.

## Known failure modes

Two distinct causes produce the same symptom (`429 Too Many Requests`) and
need different fixes — check the response body, not just the status code.

**1. Our own concurrency overwhelming a provider's per-key rate limit.**
Symptom: consistent 429s for one model when run alongside others at high
shared `--concurrency`. Fix: `MODEL_CONCURRENCY_CAP` in `run_eval.py` caps
specific models below the global `--concurrency` regardless of what's
passed on the command line (currently `qwen/qwen3.8-flash: 6`, found by
comparing a mixed 5-model run at concurrency=30, which threw errors on 18/20
Qwen calls, against a solo Qwen run at concurrency=6, which had 0/2000
errors).

**2. OpenRouter's upstream shared pool for a model being saturated —
external, transient, and outside this script's control.** Symptom: 429s on
*every* call to one model, even fully sequential with no concurrency at all.
The error body's `error.metadata.limit_source` says
`"upstream_provider_shared_pool"` and `error.metadata.raw` explicitly says
the model "is temporarily rate-limited upstream" (observed for
`qwen/qwen3.8-flash` on 2026-09-18, while `deepseek/deepseek-v4.1-flash`
succeeded at the same moment on the same key). No amount of retry/backoff
tuning fixes this — it means OpenRouter's free/shared routing capacity for
that model is exhausted account-wide, not just for this key. Wait and retry
later, or add your own upstream provider key under
[openrouter.ai/settings/integrations](https://openrouter.ai/settings/integrations)
to get a dedicated quota instead of the shared pool.

If a model that worked cleanly in an earlier run starts erroring, check
`error.metadata.limit_source` in the failing response before assuming the
script regressed.
