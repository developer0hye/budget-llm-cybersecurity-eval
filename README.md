# Budget-Tier Model Comparison: Cybersecurity Knowledge and Agentic CTF-Solving (KR / US / CN)

Two linked evaluations of 5 similarly-priced OpenRouter models spanning Korea,
the US, and China: **Part 1** measures cybersecurity *knowledge* via
multiple-choice QA ([CyberMetric][cybermetric]); **Part 2** measures
practical CTF-*solving* skill via an autonomous tool-using agent
([`ctftiny/`](ctftiny/), full report in
[`ctftiny/README.md`](ctftiny/README.md)). All comparisons use paired
significance testing (McNemar's exact test) on matched data rather than raw
score gaps — see [Statistical methodology](#statistical-methodology) and
[Limitations](#limitations) before citing any single number from this repo.

[cybermetric]: https://github.com/cybermetric/CyberMetric

## Key findings

- **On knowledge (CyberMetric-2000), the 5 models are statistically
  indistinguishable when reasoning is enabled for all of them** (10/10
  pairwise McNemar tests, p ≥ 0.15). With reasoning left at each model's
  own default (effectively off, except GLM 5.3 Flash which cannot disable
  it), 3 of 10 pairs are nominally significant — but none survive a
  Bonferroni correction for multiple comparisons, and GLM's forced-on
  reasoning drives 2 of the 3.
- **Reasoning does not measurably change MCQ accuracy for any model**
  (paired McNemar, off vs. on, p ≥ 0.21 across all 5) — extra inference-time
  "thinking" doesn't move outcomes on closed-book knowledge recall.
- **On agentic CTF-solving, reasoning matters — and unevenly across
  models.** Disabling reasoning significantly *reduces* solve rate for 3 of
  4 testable models (Qwen3.8 Flash, DeepSeek V4.1 Flash, GPT-5.6 Luna;
  p ≤ 0.0003) but has no measurable effect on Solar Pro 4 (p = 0.125),
  despite verifying the forced-on condition actually engaged reasoning.
- **The uncontrolled full-run CTF comparison was confounded by reasoning
  settings the harness never set explicitly** — each model's provider
  default ranged from 0% to 100% reasoning usage across the 5 models
  (measured empirically from trajectory logs). Once reasoning is held
  constant across models, DeepSeek V4.1 Flash is the only model with a
  significant, reasoning-independent solve-rate edge; Solar Pro 4 is no
  longer distinguishable from 2 of the other 3 models it was originally
  reported as significantly behind. Full analysis:
  [`ctftiny/README.md`](ctftiny/README.md#results-reasoning-controlled-comparison-n80).
- **Absolute CTF solve rates (10–39%) exceed 2024's tool-enhanced SOTA and
  approach a CTF-specialized fine-tuned model**, despite a weaker harness
  and a harsher single-attempt protocol — read as a likely training-data
  contamination signal (2017–2023 challenges with public writeups), not a
  capability claim. Full discussion:
  [`ctftiny/README.md`](ctftiny/README.md#comparison-to-published-literature).

## Models under test

| Country | Model | OpenRouter ID | Released (per OpenRouter) |
|---|---|---|---|
| KR | Solar Pro 4 | `upstage/solar-pro4` | 2026-08-10 |
| US | GPT-5.6 Luna | `openai/gpt-5.6-luna` | 2026-07 |
| CN | DeepSeek V4.1 Flash | `deepseek/deepseek-v4.1-flash` | 2026-09 |
| CN | GLM 5.3 Flash | `z-ai/glm-5.3-flash` | 2026-08-28 |
| CN | Qwen3.8 Flash | `qwen/qwen3.8-flash` | 2026-08-26 |

Selection criterion: all 5 sit in roughly the same OpenRouter weighted-average
price band as Solar Pro 4 (~$0.03–0.10 input / ~$0.4–1.3 output per 1M
tokens at the time of the run — see git history for the exact figures
checked on 2026-09-17). Model pricing and "current budget-tier model per
provider" drift on the order of days to weeks; re-verify before trusting an
older run's model selection.

## Part 1 — CyberMetric: cybersecurity knowledge (MCQ)

[CyberMetric](https://github.com/cybermetric/CyberMetric) (Tihanyi et al.,
arXiv:2402.07688, 2024) is a multiple-choice QA benchmark generated via RAG
from NIST standards, RFCs, and cybersecurity textbooks, covering 9 domains
(pentest, cryptography, network/IoT security, governance, compliance, cloud
security, etc.), human-validated. We use the **2000-question tier**:
narrower margin of error than the 80/500-question tiers (±1.6pp vs. ±3.1pp
at 500) while finishing in ~10–15 minutes, and unlike the 10000-question
tier it isn't flagged by the authors as having an estimated 2–3%
label-error rate. The dataset is not vendored (upstream has no LICENSE
file); `download_data.sh` fetches it fresh at setup time.

Each model answered the **same 2000 questions**, once with reasoning left
at its provider default (effectively off; GLM 5.3 Flash cannot disable
reasoning) and once with reasoning explicitly forced on for all 5.

### Results — reasoning off (2026-09-17)

| Rank | Country | Model | Accuracy | Correct/Total |
|---|---|---|---|---|
| 1 | 🇨🇳 CN | GLM 5.3 Flash\* | 95.10% | 1902/2000 |
| 2 | 🇰🇷 KR | Solar Pro 4 | 94.75% | 1895/2000 |
| 3 | 🇨🇳 CN | Qwen3.8 Flash | 94.05% | 1881/2000 |
| 4 | 🇺🇸 US | GPT-5.6 Luna | 93.85% | 1877/2000 |
| 5 | 🇨🇳 CN | DeepSeek V4.1 Flash | 93.55% | 1871/2000 |

\* GLM 5.3 Flash's reasoning is mandatory and cannot be disabled — its "off"
row is not a true off-condition; see [Cross-model significance](#cross-model-significance) below.

### Results — reasoning explicitly on for all 5 (2026-09-18)

| Rank | Country | Model | Accuracy | Correct/Total |
|---|---|---|---|---|
| 1 | 🇰🇷 KR | Solar Pro 4 | 94.85% | 1897/2000 |
| 1 | 🇨🇳 CN | GLM 5.3 Flash | 94.85% | 1897/2000 |
| 3 | 🇨🇳 CN | Qwen3.8 Flash | 94.35% | 1887/2000 |
| 4 | 🇨🇳 CN | DeepSeek V4.1 Flash | 94.25% | 1885/2000 |
| 5 | 🇺🇸 US | GPT-5.6 Luna | 94.10% | 1882/2000 |

### Statistical methodology

All 5 models answer the identical 2000 questions in each run, which makes
this **matched/paired data**. The correct pairwise comparison is
**McNemar's exact test** on a per-question basis, not a threshold on the
raw accuracy gap (a gap-threshold heuristic implicitly assumes independent
samples, which understates power on matched data and can miss real
effects). All significance claims below use McNemar's test; a
multiple-comparisons caveat (10 pairwise tests per condition) applies
throughout — see [Limitations](#limitations).

### Cross-model significance

**Reasoning off** (n=2000 per pair):

| Pair | b, c | p |
|---|---|---|
| DeepSeek V4.1 Flash vs GLM 5.3 Flash | 49, 80 | **0.0080** |
| GPT-5.6 Luna vs GLM 5.3 Flash | 47, 72 | **0.0274** |
| Solar Pro 4 vs DeepSeek V4.1 Flash | 72, 48 | **0.0353** |
| GLM 5.3 Flash vs Qwen3.8 Flash | 65, 44 | 0.0549 |
| Solar Pro 4 vs Qwen3.8 Flash | 63, 49 | 0.2191 |
| Solar Pro 4 vs GPT-5.6 Luna | 73, 55 | 0.1326 |
| DeepSeek V4.1 Flash vs Qwen3.8 Flash | 55, 65 | 0.4114 |
| GPT-5.6 Luna vs DeepSeek V4.1 Flash | 70, 64 | 0.6660 |
| Solar Pro 4 vs GLM 5.3 Flash | 53, 60 | 0.5727 |
| GPT-5.6 Luna vs Qwen3.8 Flash | 50, 54 | 0.7688 |

3 of 10 pairs are nominally significant (p<0.05); **none survive Bonferroni
correction** (α = 0.05/10 = 0.005). GLM 5.3 Flash's mandatory reasoning
plausibly explains 2 of the 3 — its "off" condition isn't a true off
condition for GLM specifically.

**Reasoning on** (n=2000 per pair): all 10 pairs are not significant
(p ≥ 0.13) — the 5 models are statistically indistinguishable under this
condition.

**Reading the two tables together**: "these 5 similarly-priced models
perform indistinguishably on cybersecurity knowledge MCQs" holds cleanly
for the reasoning-on condition; the reasoning-off condition has real, if
multiple-comparisons-fragile, daylight between a few pairs. Don't cite
either table as "model X beats model Y" without naming the condition and
the correction status.

### Does reasoning help accuracy?

| Model | Reasoning off | Reasoning on | Delta | McNemar p (paired) |
|---|---|---|---|---|
| Solar Pro 4 | 94.75% | 94.85% | +0.10pp | 0.912 |
| GPT-5.6 Luna | 93.85% | 94.10% | +0.25pp | 0.645 |
| DeepSeek V4.1 Flash | 93.55% | 94.25% | +0.70pp | 0.211 |
| GLM 5.3 Flash\* | 95.10% | 94.85% | −0.25pp | 0.568 |
| Qwen3.8 Flash | 94.05% | 94.35% | +0.30pp | 0.617 |

\* GLM's "off" run still had reasoning on (mandatory); its delta reflects
test-retest noise (~0.25pp run-to-run variance at this sample size), not a
real on/off effect.

**No model shows a statistically meaningful effect from reasoning on this
benchmark** — paired McNemar gives p ≥ 0.21 for every model, a proper
non-significant result on matched data, not just "the deltas look small."
Contrast this with [Part 2](#part-2--ctf-solving-agent-evaluation-phase-2),
where reasoning has a large, significant effect for most of the same
models — the type of task matters more than the model for whether
reasoning helps.

## Part 2 — CTF-solving agent evaluation (phase 2)

CyberMetric measures cybersecurity *knowledge*; a companion evaluation in
[`ctftiny/`](ctftiny/) measures practical CTF-*solving* skill for the same
5 models, using NYU's [nyuctf_agents][nyuctf-agents] baseline tool-using
agent against real CTF challenges in a Docker sandbox, plus
[CTFJudge][ctfjudge] for trajectory-quality grading (not yet run
end-to-end). Full methodology, architecture, data, and results:
[`ctftiny/README.md`](ctftiny/README.md).

[nyuctf-agents]: https://github.com/NYU-LLM-CTF/nyuctf_agents
[ctfjudge]: https://github.com/NYU-LLM-CTF/CTFJudge

**Headline result** (see `ctftiny/README.md` for the full statistical
workup): a full 200-challenge run per model (1000 jobs, $8.27) initially
found Solar Pro 4 solving significantly fewer challenges than every other
model. That comparison never controlled for reasoning — a follow-up
audit found the harness had never set an explicit reasoning parameter, so
each model defaulted to its provider's own behavior (0% to 100% reasoning
usage, measured). A reasoning-controlled re-run (800 more jobs, $6.13)
found the effect is partly a confound: with reasoning held uniformly off
across the 4 testable models, DeepSeek V4.1 Flash remains significantly
better than all 3 others, but **Solar Pro 4 is no longer significantly
different from Qwen3.8 Flash or GPT-5.6 Luna** — only from DeepSeek.

## Limitations

- **Matched-data comparisons require paired tests.** Every result in this
  repo compares models on the identical question/challenge set; a raw gap
  between two accuracy or solve-rate numbers is not itself evidence of a
  difference — use the McNemar results, not the ranking tables, to decide
  whether two models actually differ.
- **Multiple comparisons.** Each 5-model condition runs 10 pairwise tests;
  at uncorrected α=0.05 roughly 0.5 false positives are expected by chance.
  Results are reported with raw p-values throughout; treat any p in the
  0.01–0.05 range as suggestive rather than conclusive unless it also
  survives Bonferroni correction (noted explicitly where relevant).
  Cross-model CTF-solving p-values may also be inflated toward significance
  by the attempted-count imbalance discussed in `ctftiny/README.md`.
- **GLM 5.3 Flash's mandatory reasoning breaks the reasoning-off condition
  for that model specifically**, in both Part 1 and Part 2 — its "off" row
  is not a true off-condition and its inclusion in off-condition rankings
  should be discounted accordingly.
- **CTF-solving absolute rates likely overstate genuine problem-solving
  capability** due to training-data contamination risk (public,
  multi-year-old challenges with public writeups) — see
  [`ctftiny/README.md`](ctftiny/README.md#comparison-to-published-literature).
- **Model pricing and routing drift.** OpenRouter model IDs can silently
  route to updated weights, and "budget tier" pricing shifts over weeks —
  results are timestamped and should not be assumed to hold for a re-run
  months later.

## Reproducing this work

```bash
git clone <this-repo>
cd cybersecurity_eval
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
./download_data.sh
cp .env.example .env   # then fill in your own OPENROUTER_API_KEY
```

The script runs all questions for all models on a single asyncio event
loop, bounded by `--concurrency` in-flight requests at a time (default 30).
Results are written incrementally as each call completes — `tail -f
results/<model>.jsonl` or `watch -n2 cat results/summary.json` to watch a
run live.

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

**Reproducing the documented runs exactly**: `python3 run_eval.py --dataset
data/CyberMetric-2000-v1.json` with the `MODELS` dict as it stands in this
commit, no `--reasoning` flag for the off run (2026-09-17), `--reasoning on`
for the on run (2026-09-18), `--concurrency 30`. Re-running later will hit
whatever weights OpenRouter currently routes those model IDs to.

### Token budget calibration

`calibrate_tokens.py` finds the smallest `max_tokens` that avoids truncated
answers (reasoning eating the whole budget, leaving `content: null`) for
each model with reasoning on, by testing a random probe sample at
increasing budgets (250 → 500 → 1000 → 2000 → 4000 → 8000):

```bash
python3 calibrate_tokens.py --probe-size 30 --budgets 250 500 1000 2000 4000 8000
```

Writes `calibration/report.md` / `calibration/report.json` plus an
append-only `calibration/calibration.log`. Low concurrency by default
(5) so it doesn't compete for rate limit with a concurrent `run_eval.py`.

**Results (probe_size=30, seed=42, run 2026-09-18)**:

| Model | Recommended `max_tokens` | Max reasoning tokens seen | p50 tokens used |
|---|---|---|---|
| Solar Pro 4 | **8000** | 4816 | 683 |
| GPT-5.6 Luna | **500** | 221 | 5 |
| DeepSeek V4.1 Flash | **2000** | 1921 | 54 |
| GLM 5.3 Flash (mandatory reasoning) | **1000** | 250 | 111 |
| Qwen3.8 Flash | **8000** | 706 | 108 |

Two clusters: GPT-5.6 Luna barely reasons at all on these questions (p50 of
5 tokens); Solar Pro 4 and Qwen3.8 Flash have a long tail (median well
under 1000 tokens, but occasional spikes past 4800/4000) — this is why the
reasoning-on run above logged 4 truncation errors at `max_tokens=4000`. If
re-running with reasoning on, use `max_tokens=8000` for Solar Pro 4 and
Qwen3.8 Flash specifically rather than one shared budget for all 5.

### Output files

- `results/<model>.jsonl` — per-question log (question, correct answer,
  model's answer, raw response, correctness, error, token usage)
- `results/summary.json` — per-model accuracy + token usage + `cost_usd`,
  plus `_total_cost_usd`; updated every 50 completions during a run
- `results_reasoning_on/summary.json` — same, for the `--reasoning on` run
- `calibration/report.md` / `report.json` — token-budget calibration

### Cost

`run_eval.py` records real per-call cost from OpenRouter's `usage.cost`
field into each `results*/summary.json`. **Total spend on this project's
API key as of 2026-09-18: $2.62** (lifetime key usage, not just the two
documented full runs — includes every smoke test and calibration probe
during development). Rough scale: a full run is 2000 questions × 5 models =
10,000 calls, ~200 input tokens/question, output capped at 16 tokens for
reasoning-off (1000–8000 for reasoning-on) — well under $1 at reasoning
off, a few dollars at reasoning on.

### Known failure modes

Two distinct causes produce the same symptom (`429 Too Many Requests`) and
need different fixes — check the response body, not just the status code.

**1. Own concurrency overwhelming a provider's per-key rate limit.**
Symptom: consistent 429s for one model when run alongside others at high
shared `--concurrency`. Fix: `MODEL_CONCURRENCY_CAP` in `run_eval.py` caps
specific models below the global `--concurrency` regardless of the CLI
value (currently `qwen/qwen3.8-flash: 6`, found by comparing a mixed
5-model run at concurrency=30, which errored on 18/20 Qwen calls, against a
solo Qwen run at concurrency=6, which had 0/2000 errors).

**2. OpenRouter's upstream shared pool for a model being saturated —
external, transient, outside this script's control.** Symptom: 429s on
*every* call to one model, even fully sequential with no concurrency. The
error body's `error.metadata.limit_source` reads
`"upstream_provider_shared_pool"`. No retry/backoff tuning fixes this — it
means OpenRouter's shared routing capacity for that model is exhausted
account-wide. Wait and retry later, or add your own upstream provider key
under [openrouter.ai/settings/integrations](https://openrouter.ai/settings/integrations)
for a dedicated quota. Check `error.metadata.limit_source` in the failing
response before assuming the script regressed.

## Changelog

- **2026-09-17** — Baseline CyberMetric run (reasoning off, GLM
  mandatory-on).
- **2026-09-18** — Reasoning-on run (all 5 models); token-budget
  calibration; real per-call cost tracking added.
- **2026-09-19** — Phase 2 (CTF-solving): full 200-challenge run (1000
  jobs, $8.27) and a clean re-run of a 10-challenge pilot sample (60 jobs,
  $0.45).
- **2026-09-20** — Statistical audit of both benchmarks: replaced an
  unsound significance-threshold heuristic with McNemar's paired test
  throughout; discovered and corrected an uncontrolled-reasoning confound
  in phase 2; ran a reasoning-controlled re-run of phase 2 (800 jobs,
  $6.13). **Phase 2 total: $14.85** ($8.27 + $0.45 + $6.13).
