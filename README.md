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

**Corrected finding: "all tied" only holds for the reasoning-on condition**
(see [Statistical notes](#statistical-notes) — an earlier version of this
section used a rank-gap threshold that doesn't hold up under review). All 5
models answer the *same* 2000 questions each run, which makes this matched
data — the statistically correct comparison is McNemar's paired test per
question pair, not the gap between rank 1 and rank 5:

- **Reasoning off**: 3 of 10 pairwise McNemar tests are significant at
  p<0.05 — DeepSeek V4.1 Flash vs GLM 5.3 Flash (p=0.008), GPT-5.6 Luna vs
  GLM 5.3 Flash (p=0.027), Solar Pro 4 vs DeepSeek V4.1 Flash (p=0.035). The
  other 7 pairs are not significant. GLM's mandatory reasoning (see \* below)
  makes its "reasoning off" row not truly apples-to-apples, which plausibly
  explains why GLM drives 2 of these 3 pairs.
- **Reasoning on**: all 10 pairs are not significant (p≥0.15) — "statistically
  tied" holds cleanly here.
- **Multiple-comparisons caveat**: 10 pairwise tests were run per condition;
  none of the 3 nominally-significant reasoning-off pairs survive a
  Bonferroni correction (α=0.05/10=0.005). Treat them as suggestive, not
  conclusive.

Don't read either table as "model X beats model Y" outright — the
reasoning-on table supports "these 5 similarly-priced models perform
indistinguishably," but the reasoning-off table has real (if
multiple-comparisons-fragile) daylight between a few pairs.

### Does reasoning help? (per-model, off → on)

| Model | Reasoning off | Reasoning on | Delta | McNemar p (paired, off vs on) |
|---|---|---|---|---|
| Solar Pro 4 | 94.75% | 94.85% | +0.10pp | 0.912 |
| GPT-5.6 Luna | 93.85% | 94.10% | +0.25pp | 0.645 |
| DeepSeek V4.1 Flash | 93.55% | 94.25% | +0.70pp | 0.211 |
| GLM 5.3 Flash | 95.10%\* | 94.85% | -0.25pp | 0.568 |
| Qwen3.8 Flash | 94.05% | 94.35% | +0.30pp | 0.617 |

\* GLM's "off" run still had reasoning on (mandatory) — its delta is test-retest
noise, not an on/off effect, and usefully shows run-to-run variance is ~0.25pp
at this sample size.

**No model shows a statistically meaningful effect from reasoning** — paired
McNemar's test (matched per-question, off vs on) gives p≥0.21 for every
model. This isn't just "the deltas look small," it's a proper non-significant
result on matched data. On a pure-knowledge MCQ benchmark like CyberMetric,
letting these models "think longer" doesn't measurably change the outcome.

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

`attempted` counts differ sharply by model (83-175/200) for reasons tied to
three operational incidents during the run (documented in `ctftiny/README.md`,
including one — orphaned processes killed mid-conversation during a Docker
restart — caught only in a later audit) — the raw table below should
**not** be read as a ranking. The clean comparison is the 61 challenges all
5 models actually completed: there, **Solar Pro4 solves significantly
fewer than every other model** (McNemar p<0.001 in all 4 pairwise tests
against it); the other 4 models are statistically indistinguishable from
each other.

**Superseded in part, see below**: this run never set an explicit
reasoning on/off parameter, so each model ran at whatever its provider
defaults to (0% to 100%, measured) — a confound. A follow-up
reasoning-controlled re-run found DeepSeek V4.1 Flash's edge survives, but
2 of Solar Pro4's 4 "significantly worse" pairings (vs Qwen3.8 Flash, vs
GPT-5.6 Luna) do not — see [Reasoning-controlled re-run](#reasoning-controlled-re-run-2026-09-20)
below.

| Model | Attempted/200 | Solve rate (of attempted) | Solve rate (n=61 all-attempted) | Total cost |
|---|---|---|---|---|
| DeepSeek V4.1 Flash | 169 | 34.9% | 47.5% | $1.62 |
| GLM 5.3 Flash | 118 | 39.0% | 41.0% | $1.03 |
| Qwen3.8 Flash | 134 | 29.9% | 39.3% | $1.55 |
| GPT-5.6 Luna | 175 | 22.9% | 36.1% | $3.38 |
| Solar Pro4 | 83 | 10.8% | 13.1% | $0.70 |

**Every model here scores at or above 2024's tool-enhanced SOTA (EnIGMA +
Claude 3.5 Sonnet: 13.5%), and most score near or above a model
specifically fine-tuned for CTF-solving (CTF-Dojo: 31.9%)** — using the
*plain, weaker* baseline harness and a *harsher* protocol (1 attempt, 12
rounds) than either. That's more consistent with training-data
contamination (these are real, public 2017-2023 CTF challenges with public
writeups) than with genuine capability gains — see
[`ctftiny/README.md`](ctftiny/README.md#how-this-compares-to-the-published-literature)
for the full literature comparison and the caveats behind both tables.

### Reasoning-controlled re-run, 2026-09-20

A statistical audit found `nyuctf_agents`' baseline harness never sets an
explicit `reasoning` on/off parameter, so the run above let each model
default to its provider's own behavior — measured (by sampling raw
trajectory logs) at 0% (Solar Pro 4) to 100% (Qwen3.8 Flash). Fixed by
adding explicit reasoning control and re-running: Solar Pro 4 with
reasoning forced **on** (200 more jobs), and Qwen3.8 Flash / DeepSeek
V4.1 Flash / GPT-5.6 Luna with reasoning forced **off** (600 more jobs;
GLM 5.3 Flash excluded — its reasoning is mandatory). $6.13 additional
cost. Full data, methodology, and manipulation checks:
[`ctftiny/README.md`](ctftiny/README.md#reasoning-confound-models-never-got-an-explicit-onoff-setting).

**Two findings**:

1. **Reasoning helps 3 of 4 models, not Solar Pro 4.** Paired McNemar
   (same challenges, on vs off): Qwen3.8 Flash (p=0.0001), DeepSeek V4.1
   Flash (p=0.0003), and GPT-5.6 Luna (p<0.0001) all solve significantly
   *fewer* challenges with reasoning off. Solar Pro 4's own on-vs-off
   comparison is not significant (p=0.125), even though its forced-on
   reasoning was verified to actually engage (100% of sampled turns).
2. **The original "Solar Pro4 worse than everyone" finding was partly a
   reasoning-confound artifact.** Restricting to the 80 challenges all 4
   non-GLM models attempted with reasoning uniformly **off** — the
   cleanest apples-to-apples comparison in this project — DeepSeek V4.1
   Flash remains significantly better than all 3 others (p≤0.023), but
   **Solar Pro 4 is no longer significantly different from Qwen3.8 Flash
   (p=0.070) or GPT-5.6 Luna (p=0.109)**, only from DeepSeek. Qwen3.8
   Flash and GPT-5.6 Luna are statistically tied (p=1.000).

## Status

- ✅ **Baseline (reasoning off, GLM mandatory-on)** — complete, 2026-09-17.
- ✅ **Reasoning-on (all 5 models)** — complete, 2026-09-18.
- ✅ **Token-budget calibration** — complete, 2026-09-18, see
  [Token budget calibration](#token-budget-calibration).
- ✅ **Phase 2 (CTF-solving agent eval)** — full 200-challenge run (1000
  jobs, $8.27) and a clean re-run of the original n=10 sample (60 jobs,
  $0.45) both complete, 2026-09-19. Full CCI/CTFJudge scoring not yet run.
- ✅ **Statistical audit (both benchmarks)** — complete, 2026-09-20. Found
  and fixed a broken significance-threshold derivation in this README (see
  [Statistical notes](#statistical-notes)) and an undisclosed reasoning
  confound in phase 2 (models were never given an explicit reasoning
  on/off setting, so each ran at whatever its provider defaults to —
  0% to 100% depending on model).
- ✅ **Reasoning-controlled re-run (phase 2)** — complete, 2026-09-20, 800
  jobs, $6.13. See [Reasoning-controlled re-run](#reasoning-controlled-re-run-2026-09-20)
  above and `ctftiny/README.md`. **$14.85 total for phase 2** ($8.27 +
  $0.45 + $6.13).

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

All 5 models answer the *same* 2000 questions per run, which makes this
**matched/paired data**. The statistically correct comparison is
**McNemar's exact test** on a per-question basis (used throughout the
results above), not a threshold on the raw accuracy gap between two models.

An earlier version of this section claimed a gap needed "~2.2 percentage
points" to be meaningful, derived by "combining both models' ~±1.6pp margins
of error." That derivation doesn't actually reproduce and was corrected
2026-09-20:

- 2.19pp is the **single-model** 95%-CI margin at conservative p=0.5
  (`1.96 * sqrt(0.5×0.5/2000) × 100`) — not a combined two-model threshold.
- Properly combining two independent models' margins in quadrature (an
  unpaired two-proportion z-test) gives **~3.10pp** at conservative p=0.5,
  or **~1.47pp** using the models' actual observed accuracy (~94%) instead
  of the conservative p=0.5 assumption.
- Neither of those matches the original "~2.2pp" cleanly, and neither is
  actually the right test for this data: the two-proportion z-test assumes
  independent samples, but these are the same 2000 questions answered by
  every model. **McNemar's paired test is the correct comparison** and is
  more statistically powerful than any threshold-on-the-gap approach here —
  it's what recovers the 3 significant reasoning-off pairs that a naive
  "gap < 2.2pp → tied" reading would have missed entirely.
- Multiple-comparisons caveat: with 10 pairwise tests per condition, ~0.5
  false positives are expected by chance at uncorrected α=0.05. None of
  this run's 3 nominally-significant pairs survive Bonferroni correction
  (α=0.05/10=0.005) — see the reasoning-off results above.

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
