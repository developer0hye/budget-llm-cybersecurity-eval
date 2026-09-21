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
  4 testable models (Qwen3.8 Flash, DeepSeek V4.1 Flash, GPT-5.6 Luna; all
  p<0.0001) but has no measurable effect on Solar Pro 4 (p = 0.146),
  despite verifying — via an exhaustive scan of every trajectory, not a
  sample — that the forced-on condition actually engaged reasoning.
- **The uncontrolled full-run CTF comparison was confounded by reasoning
  settings the harness never set explicitly** — each model's provider
  default ranged from 0% to 100% reasoning usage across the 5 models
  (measured empirically from trajectory logs). Once reasoning is held
  constant across models, DeepSeek V4.1 Flash remains the model with the
  strongest, reasoning-independent solve-rate edge; Solar Pro 4 is no
  longer significantly distinguishable from GPT-5.6 Luna (one of the 3
  models it was originally reported as significantly behind), though a
  significant-at-a-suggestive-level gap against Qwen3.8 Flash re-emerges
  once the common sample nearly triples (n=80→190). Full analysis:
  [`ctftiny/README.md`](ctftiny/README.md#results-reasoning-controlled-comparison-n190).
- **4 of 5 models exceed 2024's tool-enhanced CTF-solving SOTA; Solar Pro
  4 does not.** Absolute solve rates otherwise range 6.7%–36.1%, with the
  top end approaching a CTF-specialized fine-tuned model, despite a weaker
  harness and a harsher single-attempt protocol — read the high end as a
  likely training-data contamination signal (2017–2023 challenges with
  public writeups), not a capability claim; Solar Pro 4 falling below SOTA
  suggests that signal isn't uniform across models. Full discussion:
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

### Results

Accuracy on the same 2000 questions, in both reasoning conditions. Ranked
by the reasoning-on column — the apples-to-apples one, since GLM 5.3 Flash
cannot disable reasoning and its "off" row is therefore not a true
off-condition.

| Rank | Country | Model | Reasoning off | Reasoning on |
|---|---|---|---|---|
| 1 | 🇰🇷 KR | Solar Pro 4 | 94.75% | **94.85%** |
| 1 | 🇨🇳 CN | GLM 5.3 Flash\* | 95.10% | **94.85%** |
| 3 | 🇨🇳 CN | Qwen3.8 Flash | 94.05% | **94.35%** |
| 4 | 🇨🇳 CN | DeepSeek V4.1 Flash | 93.55% | **94.25%** |
| 5 | 🇺🇸 US | GPT-5.6 Luna | 93.85% | **94.10%** |

\* GLM's "off" run still had reasoning on (mandatory).

**Verdict: the 5 models are statistically indistinguishable.** With
reasoning on for all of them, all 10 pairwise McNemar tests are
non-significant (p ≥ 0.13). With reasoning at each model's default, 3 of 10
pairs are nominally significant but **none survive Bonferroni correction**,
and GLM's mandatory reasoning plausibly explains 2 of those 3. A 1.3pp
spread across 2000 questions is not a ranking — don't cite one of these
models as beating another on this benchmark.

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

<details>
<summary>Full pairwise McNemar tests, reasoning off (n=2000 per pair)</summary>

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

3 of 10 pairs are nominally significant (p<0.05); none survive Bonferroni
correction (α = 0.05/10 = 0.005). Under reasoning-on, all 10 pairs are
non-significant (p ≥ 0.13).

</details>

### Does reasoning help accuracy?

**No — not for any of the 5 models.** Paired McNemar on the same 2000
questions, off vs. on: Solar Pro 4 p=0.912, GPT-5.6 Luna p=0.645, DeepSeek
V4.1 Flash p=0.211, GLM 5.3 Flash p=0.568, Qwen3.8 Flash p=0.617. Deltas
run −0.25pp to +0.70pp, within the ~0.25pp test-retest noise at this sample
size. This is a proper non-significant result on matched data, not just
"the deltas look small."

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
workup): a full 200-challenge run per model (1000 jobs, $11.84 after a
later retry batch closed most infra-caused gaps) initially found Solar Pro
4 solving significantly fewer challenges than every other model. That
comparison never controlled for reasoning — a follow-up audit found the
harness had never set an explicit reasoning parameter, so each model
defaulted to its provider's own behavior (0% to 100% reasoning usage,
measured). A reasoning-controlled re-run (800 more jobs, $8.09) found the
effect is partly a confound: with reasoning held uniformly off across the
4 testable models on a fixed common sample of 190, DeepSeek V4.1 Flash
remains significantly better than all 3 others, and **Solar Pro 4 is no
longer significantly different from GPT-5.6 Luna** — it is still
significantly worse than DeepSeek, and (at a suggestive, not fully
conclusive level) worse than Qwen3.8 Flash again once the sample grew.

### Results — reasoning-controlled comparison (n=190, the one to cite)

The 190 challenges all 4 testable models attempted with reasoning uniformly
off. GLM 5.3 Flash is excluded — its reasoning cannot be disabled.

| Rank | Country | Model | Solved (of 190) | Solve rate |
|---|---|---|---|---|
| 1 | 🇨🇳 CN | DeepSeek V4.1 Flash | 41 | 21.6% |
| 2 | 🇨🇳 CN | Qwen3.8 Flash | 23 | 12.1% |
| 3 | 🇺🇸 US | GPT-5.6 Luna | 19 | 10.0% |
| 4 | 🇰🇷 KR | Solar Pro 4 | 13 | 6.8% |

Pairwise McNemar: DeepSeek beats all 3 others (p ≤ 0.0005); Solar Pro 4 vs
Qwen3.8 Flash p=0.013 (suggestive); Solar Pro 4 vs GPT-5.6 Luna p=0.180 and
Qwen3.8 Flash vs GPT-5.6 Luna p=0.455 (both not significant). Full table:
[`ctftiny/README.md`](ctftiny/README.md#results-reasoning-controlled-comparison-n190).

**Why 190 and not 200**: a paired test needs both models to have actually
attempted the same challenge, so the comparison uses the challenges all 4
attempted. 10 drop out, none for model-quality reasons — 2 fail to start
for every model (`2019f-web-biometric`, a Debian package 404 at image build;
`2023q-web-rainbow_notes`, a Docker/runc bug on Apple Silicon), and 8 lose a
single model each to a 900s timeout (6) or a one-off compose failure (2).
Treating timeouts as non-solves instead — which raises the sample to n=196 —
leaves **all 6 pairwise p-values identical**, since those challenges went
unsolved by every model and contribute no discordant pairs.

### Does reasoning help? (paired, same challenges, on vs. off)

**Yes — for 3 of the 4 testable models, strongly.** Qwen3.8 Flash (n=187),
DeepSeek V4.1 Flash (n=191) and GPT-5.6 Luna (n=196) all lose solve rate
when reasoning is disabled, p<0.0001 each. Solar Pro 4 is the exception
(n=192, p=0.146) — no measurable effect, and the forced-on condition was
verified to actually engage reasoning. This is the opposite of [Part 1's
CyberMetric result](#does-reasoning-help-accuracy), where reasoning moves
nothing for any model: the type of task decides whether reasoning pays off,
more than the model does.

GLM 5.3 Flash cannot be tested here at all (mandatory reasoning). The
earlier **uncontrolled** full-200 run — every model at its own provider
default, so not apples-to-apples — plus per-model cost, attempted counts,
and the n=166 all-5-attempted subset are in
[`ctftiny/README.md`](ctftiny/README.md#results-uncontrolled-full-200-run-2026-09-19).

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

<details>
<summary><b>Calibrated budgets (probe_size=30, seed=42, run 2026-09-18)</b></summary>

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

</details>

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
  originally $6.13, revised to $8.09 after the 2026-09-21 retry batch
  below added more rows).
- **2026-09-20/21** — Retry batch closing phase 2's "attempted" gap
  (83–175→174–196 of 200): replaced a one-off, hand-edited host-port fix
  for 24 challenges with a general automatic port-conflict resolver
  (`ctftiny/dynamic_ports.py`); fixed two deadlock bugs found by a Codex
  review of the retry pipeline and one more severe concurrency-collapse
  bug (stale port-lock metadata) found live; confirmed one previously-seen
  challenge failure is non-transient (Docker/runc bug on Apple Silicon)
  rather than retrying indefinitely. Full incident log:
  [`ctftiny/README.md`](ctftiny/README.md#appendix-b-operational-incident-log).
  With this batch's added rows, the reasoning-controlled comparison's
  common sample grew from n=80 to n=190, which surfaced a previously
  undetected (suggestive) gap between Solar Pro 4 and Qwen3.8 Flash that
  didn't reach significance at the smaller sample size. **Phase 2 total:
  $20.38** ($11.84 full-200 + $0.45 n=10 pilot + $8.09
  reasoning-controlled).
