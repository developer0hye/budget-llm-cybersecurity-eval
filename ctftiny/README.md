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

- **The reasoning-controlled comparison (the correct one to cite) is
  n=190, all-4-models-attempted, reasoning uniformly off**: DeepSeek V4.1
  Flash solves significantly more challenges than the other 3 models
  (p ≤ 0.0005 against each); Solar Pro 4 is significantly worse than
  DeepSeek and, at a suggestive level, worse than Qwen3.8 Flash (p=0.013)
  — but not significantly different from GPT-5.6 Luna (p=0.180); Qwen3.8
  Flash and GPT-5.6 Luna are not significantly different (p=0.455). See
  [Results](#results-reasoning-controlled-comparison-n190).
- **Reasoning significantly improves CTF-solving for 3 of 4 testable
  models** (Qwen3.8 Flash, DeepSeek V4.1 Flash, GPT-5.6 Luna: all
  p<0.0001) but has no measurable effect on Solar Pro 4 (p=0.146), even
  though its forced-on reasoning was verified to actually engage.
- **An earlier, uncontrolled full-200 run found Solar Pro 4 significantly
  worse than all 4 other models.** That finding only partially replicates
  once reasoning is held constant: the deficit against DeepSeek replicates
  strongly, the deficit against Qwen3.8 Flash re-emerges but only at a
  suggestive level (p=0.013, down from p<0.0001 uncontrolled) once the
  common sample nearly triples (n=80→190), and the deficit against GPT-5.6
  Luna still does not replicate at all (p=0.180).
- **The uncontrolled full-run comparison also sharpened among the other 4
  models as the sample grew (n=61→166)**: DeepSeek V4.1 Flash is now
  significantly ahead of GPT-5.6 Luna and Qwen3.8 Flash, and GLM 5.3 Flash
  is significantly ahead of GPT-5.6 Luna and (suggestively) Qwen3.8 Flash —
  at n=61 these 4 models looked statistically tied once Solar Pro 4 was
  excluded. See [Results](#results-uncontrolled-full-200-run-2026-09-19).
- **4 of 5 models exceed 2024's tool-enhanced SOTA (EnIGMA, 13.5%) on the
  full-200 run; Solar Pro 4 does not (6.7%).** Rates otherwise range
  6.7%–36.1% of attempted, with the top end near a CTF-specialized
  fine-tune (CTF-Dojo, 31.9%), despite a weaker harness and a harsher
  1-attempt/12-round protocol. Read the high end as a likely
  training-data-contamination signal (these are public 2017–2023
  challenges with public writeups) — but Solar Pro 4 scoring *below* 2024
  SOTA is evidence that effect isn't uniform across models, not proof it's
  absent — see [Comparison to published literature](#comparison-to-published-literature).
- **A dedicated retry effort brought "attempted" coverage from 83–175 of
  200 up to 174–198 of 200** — a general, automatic port-conflict
  resolver replaced the original one-off fix, and two deadlock bugs plus a
  stale-lock-metadata bug (found live, mid-batch) were diagnosed and
  fixed — see [Appendix B](#appendix-b-operational-incident-log). The
  newly-recovered challenges solve at a *lower* rate than the
  originally-attempted ones in 4 of 5 full-run conditions: the challenges
  that previously failed on infrastructure grounds were systematically
  harder, not a random subset — see [Limitations](#limitations).

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

## Results: reasoning-controlled comparison (n=190)

This is the **primary, citable comparison** in this project — the only one
where reasoning is held constant across models. It restricts to the **190
challenges all 4 non-GLM models attempted with reasoning uniformly off**
(Solar Pro 4's provider default is a verified 0% reasoning rate — confirmed
by an exhaustive scan of every trajectory in its full-200 run, see
[below](#results-does-reasoning-help-per-model); Qwen3.8 Flash, DeepSeek
V4.1 Flash, and GPT-5.6 Luna were re-run with reasoning explicitly forced
off — GLM 5.3 Flash is excluded, its reasoning cannot be disabled). This
sample grew from 80 to 190 after a retry batch closed most of the
"attempted" gaps (see [Appendix B](#appendix-b-operational-incident-log)).

| Model | Solved (of 190) | Solve rate |
|---|---|---|
| DeepSeek V4.1 Flash | 41 | 21.6% |
| Qwen3.8 Flash | 23 | 12.1% |
| GPT-5.6 Luna | 19 | 10.0% |
| Solar Pro 4 | 13 | 6.8% |

Pairwise McNemar exact test within this fixed n=190:

| Pair | b, c | p |
|---|---|---|
| DeepSeek V4.1 Flash vs Solar Pro 4 | 28, 0 | **<0.0001** |
| DeepSeek V4.1 Flash vs GPT-5.6 Luna | 26, 4 | **0.0001** |
| DeepSeek V4.1 Flash vs Qwen3.8 Flash | 22, 4 | **0.0005** |
| Qwen3.8 Flash vs Solar Pro 4 | 12, 2 | **0.013** |
| GPT-5.6 Luna vs Solar Pro 4 | 10, 4 | 0.180 |
| Qwen3.8 Flash vs GPT-5.6 Luna | 10, 6 | 0.455 |

**Interpretation**: DeepSeek V4.1 Flash has a significant, reasoning-
independent CTF-solving advantage over all 3 other testable models, and
that advantage held (in fact strengthened) as the sample nearly tripled
from n=80 to n=190. Solar Pro 4 is no longer indistinguishable from every
other model at this larger sample size: it remains significantly worse
than DeepSeek, and is now also worse than Qwen3.8 Flash at a **suggestive**
level (p=0.013 — within this project's own 0.01–0.05 "suggestive, not
conclusive" band, see [Limitations](#limitations)) that did not reach
significance at n=80 (p=0.070). It remains statistically indistinguishable
from GPT-5.6 Luna (p=0.180, consistent with n=80's p=0.109). This partially
revises the uncontrolled full-run finding below, where Solar Pro 4 appeared
significantly worse than all 4 other models: the difference vs. GPT-5.6
Luna still does not survive reasoning control; the difference vs. Qwen3.8
Flash now partially survives (suggestive, weaker than the uncontrolled
p<0.0001); the difference vs. DeepSeek survives fully. GLM 5.3 Flash cannot
be placed in this comparison at all, since its reasoning cannot be disabled
to match the other 4.

This comparison inherits the attempted-count caveat from the uncontrolled
run below — it uses each model's *attempted* subset (not the full 200),
though at n=190 of a possible 200 this now covers 95% of the challenge
pool — see [Limitations](#limitations).

## Results: does reasoning help, per model

Paired McNemar's test, same challenges, reasoning on vs. off:

| Model | n (common attempted) | b, c | p | Verdict |
|---|---|---|---|---|
| Solar Pro 4 (off→on) | 192 | 3, 9 | 0.146 | not significant |
| Qwen3.8 Flash (on→off) | 187 | 28, 3 | **<0.0001** | reasoning helps |
| DeepSeek V4.1 Flash (on→off) | 191 | 34, 5 | **<0.0001** | reasoning helps |
| GPT-5.6 Luna (on→off) | 196 | 26, 2 | **<0.0001** | reasoning helps |

Full per-condition solve rates:

| Model | Condition | Attempted | Solved | Solve rate | Cost |
|---|---|---|---|---|---|
| Solar Pro 4 | default (0% reasoning) | 195 | 13 | 6.7% | $1.79 |
| Solar Pro 4 | reasoning forced **on** | 195 | 19 | 9.7% | $2.52 |
| Qwen3.8 Flash | default (~100% reasoning) | 188 | 48 | 25.5% | $2.18 |
| Qwen3.8 Flash | reasoning forced **off** | 197 | 23 | 11.7% | $1.50 |
| DeepSeek V4.1 Flash | default (~97% reasoning) | 194 | 70 | 36.1% | $1.81 |
| DeepSeek V4.1 Flash | reasoning forced **off** | 194 | 41 | 21.1% | $1.39 |
| GPT-5.6 Luna | default (~36% reasoning) | 196 | 43 | 21.9% | $3.73 |
| GPT-5.6 Luna | reasoning forced **off** | 198 | 19 | 9.6% | $2.68 |

**Reasoning meaningfully helps CTF-solving for 3 of 4 models; Solar Pro 4
is the outlier.** A manipulation check confirms the forced settings
actually took effect. For Solar Pro 4's default (reasoning-off) condition
— the arm this project's primary comparison relies on most, since it's
*inferred* from provider behavior rather than set via an explicit API
parameter — this check is now **exhaustive, not sampled**: every one of
its 195 full-run trajectories was scanned, and 0 of 2,409 assistant turns
used reasoning, across the entire run including the challenges the later
retry batch recovered. Solar Pro 4's forced-on run reasoned on 171/171
(100%) sampled turns; the three forced-off re-runs reasoned on 0/175,
1/184, and 0/186 sampled turns (Qwen/DeepSeek/Luna) — these three checks
predate the retry batch and were not re-run exhaustively, since their
"off" setting is enforced via an explicit `extra_body` API parameter
rather than inferred from default behavior. So Solar Pro 4's null result
is a genuine finding, not a broken flag. This contrasts with [Part 1's
CyberMetric result](../README.md#does-reasoning-help-accuracy), where
reasoning has no measurable effect for *any* model — reasoning helps on
this agentic, multi-step task in a way it doesn't on closed-book MCQ.

Total cost of the reasoning-controlled re-runs: $2.52 + $1.50 + $1.39 +
$2.68 = **$8.09**, on top of the $11.84 full-run cost.

## Results: uncontrolled full-200 run (2026-09-19)

The original run, before reasoning was controlled. A 2026-09-20/21 retry
batch closed most of the "attempted" gaps (see [Appendix
B](#appendix-b-operational-incident-log)); the numbers below are the final,
post-retry counts. Included for its larger per-model sample (up to 200 vs.
the 190 above) and because it's the source of the "attempted" imbalance
discussed in [Limitations](#limitations); the [reasoning-controlled
comparison](#results-reasoning-controlled-comparison-n190) above is still
the one to cite for cross-model claims, since this run never controlled
for reasoning.

| Model | Attempted/200 | Solved | Solve rate (of attempted) | Avg wall time | Total cost |
|---|---|---|---|---|---|
| DeepSeek V4.1 Flash | 194 | 70 | 36.1% | 328s | $1.81 |
| GLM 5.3 Flash | 174 | 62 | 35.6% | 292s | $2.34 |
| Qwen3.8 Flash | 188 | 48 | 25.5% | 258s | $2.18 |
| GPT-5.6 Luna | 196 | 43 | 21.9% | 165s | $3.73 |
| Solar Pro 4 | 195 | 13 | 6.7% | 140s | $1.79 |

Total cost across all 5 models, 1000 jobs: **$11.84**. Full per-run data:
[`eval_results_full.jsonl`](eval_results_full.jsonl) (1000 rows),
aggregated in [`eval_summary_full.json`](eval_summary_full.json).

**Attempted counts are still not a perfectly clean denominator** (174–196
of 200, down from an original 83–175 spread before the retry batch — see
[Limitations](#limitations) for why the remaining gap isn't just noise
either). Restricting to the **166 challenges all 5 models actually
attempted** controls for this directly:

| Model | Solved (of 166) | Solve rate |
|---|---|---|
| DeepSeek V4.1 Flash | 63 | 38.0% |
| GLM 5.3 Flash | 59 | 35.5% |
| Qwen3.8 Flash | 45 | 27.1% |
| GPT-5.6 Luna | 40 | 24.1% |
| Solar Pro 4 | 13 | 7.8% |

Pairwise McNemar within this n=166 set:

| Pair | b, c | p |
|---|---|---|
| DeepSeek V4.1 Flash vs Solar Pro 4 | 50, 0 | **<0.0001** |
| GLM 5.3 Flash vs Solar Pro 4 | 47, 1 | **<0.0001** |
| Qwen3.8 Flash vs Solar Pro 4 | 33, 1 | **<0.0001** |
| GPT-5.6 Luna vs Solar Pro 4 | 28, 1 | **<0.0001** |
| DeepSeek V4.1 Flash vs GPT-5.6 Luna | 30, 7 | **0.0002** |
| DeepSeek V4.1 Flash vs Qwen3.8 Flash | 24, 6 | **0.0014** |
| GLM 5.3 Flash vs GPT-5.6 Luna | 28, 9 | **0.0026** |
| GLM 5.3 Flash vs Qwen3.8 Flash | 24, 10 | **0.0243** |
| DeepSeek V4.1 Flash vs GLM 5.3 Flash | 15, 11 | 0.557 |
| Qwen3.8 Flash vs GPT-5.6 Luna | 16, 11 | 0.442 |

At n=61 (the original common-attempted sample, before the retry batch),
this looked like a single clean story: Solar Pro 4 significantly worse
than every other model, the other 4 statistically indistinguishable from
each other. **At n=166, that second half no longer holds** — DeepSeek V4.1
Flash is now significantly ahead of GPT-5.6 Luna and Qwen3.8 Flash, and
GLM 5.3 Flash is significantly ahead of GPT-5.6 Luna and (suggestively)
Qwen3.8 Flash. DeepSeek V4.1 Flash and GLM 5.3 Flash remain statistically
indistinguishable from each other, as do Qwen3.8 Flash and GPT-5.6 Luna.
**As established in [Results: reasoning-controlled
comparison](#results-reasoning-controlled-comparison-n190), the Solar Pro
4 comparisons here are confounded by uncontrolled reasoning settings** —
the deficit vs. DeepSeek fully replicates under reasoning control, the
deficit vs. Qwen3.8 Flash partially replicates (weakens from p<0.0001 to a
suggestive p=0.013), and the deficit vs. GPT-5.6 Luna does not replicate
at all (p=0.180). GLM 5.3 Flash cannot be re-tested under reasoning
control at all, so its significant pairings here (vs. Luna, vs. Qwen)
neither replicate nor are contradicted — they're simply untested under
control.

## Comparison to published literature

| Source | Model | Method | Solve rate on NYU CTF Bench (200) |
|---|---|---|---|
| [Original paper](https://arxiv.org/html/2406.05590v2) (2024) | GPT-4 | Same baseline harness, 5 attempts/challenge, 48h budget | ~3.7% (best of the paper's models) |
| [EnIGMA](https://arxiv.org/html/2409.16165) (2024) | Claude 3.5 Sonnet | Enhanced tool-use agent, pass@1, $3 budget | 13.5% (SOTA at publication) |
| [CTF-Dojo](https://arxiv.org/pdf/2508.18370) (2025) | 32B, fine-tuned on 486 execution-verified CTF trajectories | pass@1 | 31.9% |
| This project | 5 budget-tier models | Same baseline harness as the original paper, 1 attempt, 12 rounds | 6.7%–36.1% |

**Read this as a caveat about the numbers in this project, not a
capability claim.** **4 of 5 models** here score at or above the 2024
SOTA-with-better-tooling (EnIGMA, 13.5%), and 3 (DeepSeek V4.1 Flash, GLM
5.3 Flash, Qwen3.8 Flash) score near or above CTF-Dojo's number — a model
*specifically fine-tuned* on CTF-solving trajectories — despite using the
*weaker* plain baseline harness (no tool-use enhancements) and a *harsher*
protocol (1 attempt / 12 rounds vs. the original paper's 5 attempts / 48
hours). That combination is hard to explain by "these models got better at
reasoning" alone, for those 4. The more likely explanation is
**training-data contamination**: these are real 2017–2023 CTF competition
challenges with public writeups, and a 2026-era model has had far more
opportunity to see them during training than GPT-4/Claude 3 (2023–2024
training cutoffs). **Solar Pro 4 is the exception**: at 6.7%, it scores
*below* 2024 SOTA despite presumably having the same training-era exposure
to these public writeups as the other 4 — evidence that any contamination
effect here isn't uniform across models, or that Solar Pro 4's baseline
CTF-solving capability is genuinely weaker independent of contamination
(the two aren't mutually exclusive). Treat the absolute solve-rate numbers
for the 4 higher-scoring models as upper bounds on genuine problem-solving
capability, not clean measurements of it; Solar Pro 4's number is more
likely closer to a genuine measurement precisely because it isn't
inflated.

## Limitations

- **The "attempted" denominator is still uneven across models**, though
  far less than before: 174–196 of 200 in the uncontrolled run, 194–198
  in the reasoning-controlled comparison — down from 83–175 and 83–172
  respectively before a 2026-09-20/21 retry batch closed most of the gap
  (see [Appendix B](#appendix-b-operational-incident-log)). Every headline
  comparison in this project still restricts to a fixed common subset
  (n=166 or n=190) to control for whatever imbalance remains, and these
  subsets now cover 83%–95% of the full 200; only a fully uniform re-run
  of all jobs would resolve the residual gap entirely.
- **The retry-recovered ("gap-fill") rows solve at a lower rate than the
  originally-attempted rows, in 4 of 5 full-run conditions** — Solar Pro 4
  3.6% vs. 10.8% originally, Qwen3.8 Flash 14.8% vs. 29.9%, GLM 5.3 Flash
  28.6% vs. 39.0%, GPT-5.6 Luna 14.3% vs. 22.9% (DeepSeek V4.1 Flash is the
  exception: 44.0% vs. 34.9%). The challenges that previously failed on
  infrastructure grounds — mostly the 24 port-5000-conflict challenges and
  a handful of longer-running ones prone to resource contention under
  concurrency — were not a random subset of the 200; they skew toward
  challenges this harness solves less often, plausibly because challenges
  needing more rounds/tool calls before succeeding or timing out are also
  more likely to collide with a shared Docker resource. This means the
  now-much-larger "attempted" denominators are a fairer sample of the full
  200 than the original run's, not a strictly *comparable* one — the
  original per-model solve rates above were probably mildly optimistic for
  this specific reason, not just from random noise.
- **`avg_wall_time_s_attempted` mixes two measurement definitions.** Rows
  collected before the 2026-09-20/21 retry batch measure wall time from
  subprocess launch; rows collected during and after it (once a Codex
  review caught the discrepancy) measure it from lock acquisition instead,
  excluding time spent blocked on a contended Docker host port. The
  reported per-model averages are not a clean apples-to-apples timing
  comparison across runs — treat them as rough indicators only, never for
  a timing-based claim.
- **GLM 5.3 Flash cannot be included in any reasoning-controlled
  comparison** — its reasoning is mandatory and cannot be disabled via the
  API. It remains in the uncontrolled full-run numbers only.
- **Multiple comparisons.** The n=166 table runs 10 pairwise tests and the
  n=190 table runs 6; treat p-values in the 0.01–0.05 range as suggestive,
  not conclusive (this is the threshold cited throughout this README, e.g.
  the Solar Pro 4 vs. Qwen3.8 Flash p=0.013 result). Unlike the CyberMetric
  side of this project, a formal Bonferroni correction is not applied here
  — apply your own correction before citing a specific pair as significant
  in a downstream context.
- **Training-data contamination risk** likely inflates absolute solve
  rates for 4 of 5 models (all trained on similar-vintage web data) — see
  [Comparison to published literature](#comparison-to-published-literature)
  for why Solar Pro 4's below-SOTA result suggests this effect is not
  uniform across all 5 models. This affects the credibility of absolute
  numbers more than relative model-to-model comparisons.
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
- [`dynamic_ports.py`](dynamic_ports.py) — added during the 2026-09-20/21
  retry batch, replacing the original one-off, hand-edited fix for the 24
  challenges that hardcode host port 5000 (which macOS's AirPlay Receiver
  occupies by default) with a general, automatic mechanism. Right before
  each job runs, it bind-probes every host port the challenge's
  `docker-compose.yml` declares and, if one is occupied by anything
  (AirPlay, a leftover container, an unrelated local service), rewrites
  that challenge's compose file to a fresh OS-assigned free port —
  permanently, since the agent only ever reaches challenge containers via
  the internal `ctfnet` Docker network's DNS alias, never the
  host-published port (verified empirically by remapping a challenge and
  confirming a container on `ctfnet` could still resolve and connect to it
  by alias unaffected). Two bugs were found and fixed live while building
  it: a connect-probe gave inconsistent occupancy answers against a small
  `listen()` backlog (fixed by switching to a bind-probe); and a
  stale-metadata fallback path could return a challenge's *previous*
  (already-remapped-away) port unchanged, causing concurrent jobs to lock
  on a port nothing was using while the port genuinely in use had no lock
  protecting it at all — this collapsed worker concurrency from 6 to
  effectively 1 for 15+ minutes during the retry batch before being
  diagnosed and fixed (see [Appendix B](#appendix-b-operational-incident-log)).
- **Two deadlock bugs in the retry-batch drivers, found by a Codex code
  review of the pipeline**: `ensure_port_free()`'s `docker ps`/`docker
  kill` cleanup calls had no `timeout=`, so a single hung Docker call
  could block a worker thread — and the port lock it held — forever; and
  `wall_time_s` was measured from subprocess launch rather than from lock
  acquisition, so time spent blocked on a contended port was miscounted as
  run time. Both fixed in all three driver scripts.

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
docker-compose host port don't race each other; host-port conflicts are
resolved automatically and permanently by
[`dynamic_ports.py`](dynamic_ports.py)). **Reproducing the
reasoning-controlled re-run**: `python3 run_solarpro4_reasoning.py` and
`python3 run_reasoning_off.py`.

## Status & future work

Complete: full-200 run (all 5 models), reasoning-controlled re-run (4 of 5
models), n=10 pilot sample, format adapter (verified against CTFJudge's own
parsing code), and a 2026-09-20/21 retry batch that closed most of the
original "attempted" gap (83–175→174–196 of 200) by fixing the underlying
infrastructure issues rather than accepting the gap — see [Appendix
B](#appendix-b-operational-incident-log). **Total cost across all phase 2
runs: $20.38** ($11.84 full-200 + $0.45 n=10 pilot + $8.09
reasoning-controlled).

Not yet done:

- **A fully uniform re-run of every job under identical conditions** —
  would close the residual ~2–26-per-model "attempted" gap entirely rather
  than controlling for it on a fixed common subset; not attempted because
  the retry batch already reduced the gap by roughly 5x and the remaining
  no-log rows include at least one confirmed non-transient failure (see
  [Appendix B](#appendix-b-operational-incident-log)) that a uniform
  re-run wouldn't fix either.
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
4. **2026-09-20/21 retry batch.** A post-incident spot-check (re-running
   one of Solar Pro 4's failed challenges by hand, cache warm, no
   concurrent load) had succeeded, suggesting much of the remaining
   `no_log` count was recoverable transient failure rather than a
   permanently broken environment — this motivated a dedicated effort to
   close the gap rather than accept it, bringing "attempted" coverage from
   83–175/200 to 174–196/200. It surfaced and fixed several new issues:
   - The 24 challenges hardcoding host port 5000 (occupied by macOS's
     AirPlay Receiver) had been fixed by hand, once; generalized into
     [`dynamic_ports.py`](dynamic_ports.py), an automatic bind-probe-based
     port-conflict resolver (see [Architecture](#architecture--implementation)).
   - Two deadlock bugs found by a Codex review of the retry drivers:
     missing `timeout=` on `docker ps`/`docker kill` cleanup calls (a hung
     call could block a worker thread, and its held port lock, forever),
     and `wall_time_s` measured from subprocess launch instead of lock
     acquisition.
   - A more severe concurrency-collapse bug found live, independent of the
     Codex review: `dynamic_ports.py`'s stale-metadata fallback path could
     return a challenge's *previous* (already-remapped-away) port
     unchanged, so concurrent jobs would lock on a port nothing was using
     while the port genuinely in use had no lock at all — this collapsed
     worker concurrency from 6 to effectively 1 for 15+ minutes, diagnosed
     by ruling out disk space, `CTFDataset` init, and 56 orphaned Docker
     containers (all cleaned up but not the fix) before finding the actual
     lock/reality mismatch.
   - **One confirmed non-transient failure, found during the retry**:
     `2023q-web-rainbow_notes` fails Docker container init with a runc
     error (`check "thread-self" component is not overmounted`) specific
     to this challenge's amd64 image under Apple Silicon emulation —
     reproduced twice by hand (not a flake); the fix (disabling Docker
     Desktop's Rosetta-based x86/amd64 emulation) requires a Docker
     Desktop restart, too disruptive to a live batch for a 3-row (1
     challenge × 3 models in the reasoning-off stage) impact, so this was
     left as a genuine `no_log` gap rather than forced through. Alongside
     the pre-existing `2019f-web-biometric` failure (a Debian package
     404), these are the two challenges most likely to still show a
     `no_log` row in the final data.

Rows corrupted by incidents 1 and 2 (8 + 71 rows) were identified by error
signature and given a real retry, since those failures were transient
infrastructure issues unrelated to model behavior. Rows corrupted by
incident 3 (5 rows, all Solar Pro 4) were reclassified but not retried, per
the reasoning above. Full detection logic is in the commit history
(`8820d01`, `a8b2c41`); incident 4's fixes are in `dynamic_ports.py` and
the three driver scripts, this session's commits.

[nyuctf-agents]: https://github.com/NYU-LLM-CTF/nyuctf_agents
