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
  n=196, all-4-models-attempted, reasoning uniformly off**: DeepSeek V4.1
  Flash solves significantly more challenges than the other 3 models
  (p ≤ 0.0005 against each); Solar Pro 4 is significantly worse than
  DeepSeek and, at a suggestive level, worse than Qwen3.8 Flash (p=0.013)
  — but not significantly different from GPT-5.6 Luna (p=0.180); Qwen3.8
  Flash and GPT-5.6 Luna are not significantly different (p=0.455). See
  [Results](#results-reasoning-controlled-comparison-n196).
- **Reasoning significantly improves CTF-solving for 3 of 4 testable
  models** (Qwen3.8 Flash, DeepSeek V4.1 Flash, GPT-5.6 Luna: all
  p<0.0001) but has no measurable effect on Solar Pro 4 (p=0.146), even
  though its forced-on reasoning was verified to actually engage.
- **An earlier, uncontrolled full-200 run found Solar Pro 4 significantly
  worse than all 4 other models.** That finding only partially replicates
  once reasoning is held constant: the deficit against DeepSeek replicates
  strongly, the deficit against Qwen3.8 Flash re-emerges but only at a
  suggestive level (p=0.013, down from p<0.0001 uncontrolled) once the
  common sample more than doubles (n=80→196), and the deficit against GPT-5.6
  Luna still does not replicate at all (p=0.180).
- **The uncontrolled full-run comparison also sharpened among the other 4
  models as the sample grew (n=61→169)**: DeepSeek V4.1 Flash is now
  significantly ahead of GPT-5.6 Luna and Qwen3.8 Flash, and GLM 5.3 Flash
  is significantly ahead of GPT-5.6 Luna and (suggestively) Qwen3.8 Flash —
  at n=61 these 4 models looked statistically tied once Solar Pro 4 was
  excluded. See [Results](#results-uncontrolled-full-200-run-2026-09-19).
- **4 of 5 models exceed 2024's tool-enhanced SOTA (EnIGMA, 13.5%) on the
  full-200 run; Solar Pro 4 does not (6.6%).** Rates range 6.6%–35.5% of
  attempted, with the top end near a CTF-specialized fine-tune (CTF-Dojo,
  31.9%), despite a weaker harness and a harsher
  1-attempt/12-round protocol. Read the high end as a likely
  training-data-contamination signal (these are public 2017–2023
  challenges with public writeups) — but Solar Pro 4 scoring *below* 2024
  SOTA is evidence that effect isn't uniform across models, not proof it's
  absent — see [Comparison to published literature](#comparison-to-published-literature).
- **Two repair passes brought "attempted" coverage from 83–175 of 200 up
  to 179–199 of 200** by fixing root causes rather than writing the gaps
  off: an automatic port-conflict resolver, three separate deadlock or
  lock-bookkeeping bugs, a disk-cleanup loop that was deleting the very
  images the next job needed, and a challenge image whose build had rotted
  (Debian archive move + a pinned wheel missing for arm64) — see
  [Appendix B](#appendix-b-operational-incident-log). The
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

## Results: reasoning-controlled comparison (n=196)

This is the **primary, citable comparison** in this project — the only one
where reasoning is held constant across models. It restricts to the **196
challenges all 4 non-GLM models attempted with reasoning uniformly off**
(Solar Pro 4's provider default is a verified 0% reasoning rate — confirmed
by an exhaustive scan of every trajectory in its full-200 run, see
[below](#results-does-reasoning-help-per-model); Qwen3.8 Flash, DeepSeek
V4.1 Flash, and GPT-5.6 Luna were re-run with reasoning explicitly forced
off — GLM 5.3 Flash is excluded, its reasoning cannot be disabled). This
sample grew from 80 to 196 across two repair passes (2026-09-20/21 and
2026-09-22) that fixed the infrastructure causing the gaps rather than
writing them off — see [Appendix B](#appendix-b-operational-incident-log).

| Model | Solved (of 196) | Solve rate |
|---|---|---|
| DeepSeek V4.1 Flash | 41 | 20.9% |
| Qwen3.8 Flash | 23 | 11.7% |
| GPT-5.6 Luna | 19 | 9.7% |
| Solar Pro 4 | 13 | 6.6% |

Pairwise McNemar exact test within this fixed n=196:

| Pair | b, c | p |
|---|---|---|
| DeepSeek V4.1 Flash vs Solar Pro 4 | 28, 0 | **<0.0001** |
| DeepSeek V4.1 Flash vs GPT-5.6 Luna | 26, 4 | **<0.0001** |
| DeepSeek V4.1 Flash vs Qwen3.8 Flash | 22, 4 | **0.0005** |
| Qwen3.8 Flash vs Solar Pro 4 | 12, 2 | **0.013** |
| GPT-5.6 Luna vs Solar Pro 4 | 10, 4 | 0.180 |
| Qwen3.8 Flash vs GPT-5.6 Luna | 10, 6 | 0.455 |

**Interpretation**: DeepSeek V4.1 Flash has a significant, reasoning-
independent CTF-solving advantage over all 3 other testable models, and
that advantage held as the sample grew from n=80 to n=196 (every one of
the six p-values below is identical at n=190 and n=196). Solar Pro 4 is no
longer indistinguishable from every other model at this larger sample size: it remains significantly worse
than DeepSeek, and is now also worse than Qwen3.8 Flash at a **suggestive**
level (p=0.013 — within this project's own 0.01–0.05 "suggestive, not
conclusive" band, see [Limitations](#limitations)) that did not reach
significance at n=80 (p=0.070). It remains statistically indistinguishable
from GPT-5.6 Luna (p=0.180, consistent with n=80's p=0.109).

Since the [Limitations](#limitations) section notes the retry-added rows
are systematically harder, the Qwen3.8-vs-Solar reversal specifically is
worth checking for composition bias rather than genuine added power: the
original n=80 is a strict subset of n=196 (retries only append rows), so
splitting the discordant pairs confirms which explanation holds. Original
80: b=7, c=1 (p=0.070, matches the original finding). The 116 added rows
alone: b=5, c=1 (p=0.219, not significant alone). **Same direction in both
halves**, neither significant alone, pooled significant (p=0.013) — this
is added statistical power on a consistent effect, not a new effect
introduced by biased composition.

This partially revises the uncontrolled full-run finding below, where Solar Pro 4 appeared
significantly worse than all 4 other models: the difference vs. GPT-5.6
Luna still does not survive reasoning control; the difference vs. Qwen3.8
Flash now partially survives (suggestive, weaker than the uncontrolled
p<0.0001); the difference vs. DeepSeek survives fully. GLM 5.3 Flash cannot
be placed in this comparison at all, since its reasoning cannot be disabled
to match the other 4.

**Why n=196 rather than 200**: a paired test requires both models in a pair
to have attempted the same challenge, so this restricts to the challenges
all 4 attempted. The 4 that drop out are infrastructure, not model
behavior: `2023q-web-rainbow_notes` fails for every model (its admin-bot
container hits a Docker/runc bug under Apple Silicon emulation — see
[Appendix B](#appendix-b-operational-incident-log)); `2021f-cry-interoperable`
times out at the 900s ceiling for two models on two separate runs; and
`2019f-web-biometric` plus `2021q-cry-ecc_pop_quiz` each lose one model to
a provider-side rate limit on Qwen3.8 Flash that four attempts over 45
minutes could not clear. Per-model attempted counts in this condition are
197–199 of 200.

**Sensitivity check**: the six p-values above are identical at n=190
(before the 2026-09-22 repair pass) and at n=196 (after), and identical
again if the remaining timeouts are counted as non-solves rather than as
missing data. Challenges no model solves add no discordant pairs, which is
all McNemar uses — so none of the conclusions here turn on how the
unfinished cells are treated.

This comparison still inherits the attempted-count caveat from the
uncontrolled run below — it uses each model's *attempted* subset — though
at n=196 of a possible 200 it now covers 98% of the challenge pool; see
[Limitations](#limitations).

## Results: does reasoning help, per model

Paired McNemar's test, same challenges, reasoning on vs. off:

| Model | n (common attempted) | b, c | p | Verdict |
|---|---|---|---|---|
| Solar Pro 4 (off→on) | 196 | 3, 9 | 0.146 | not significant |
| Qwen3.8 Flash (on→off) | 188 | 28, 3 | **<0.0001** | reasoning helps |
| DeepSeek V4.1 Flash (on→off) | 197 | 34, 5 | **<0.0001** | reasoning helps |
| GPT-5.6 Luna (on→off) | 199 | 26, 2 | **<0.0001** | reasoning helps |

Full per-condition solve rates:

| Model | Condition | Attempted | Solved | Solve rate | Cost |
|---|---|---|---|---|---|
| Solar Pro 4 | default (0% reasoning) | 198 | 13 | 6.6% | $1.80 |
| Solar Pro 4 | reasoning forced **on** | 197 | 19 | 9.6% | $2.52 |
| Qwen3.8 Flash | default (~100% reasoning) | 189 | 48 | 25.4% | $2.18 |
| Qwen3.8 Flash | reasoning forced **off** | 198 | 23 | 11.6% | $1.50 |
| DeepSeek V4.1 Flash | default (~97% reasoning) | 197 | 70 | 35.5% | $1.83 |
| DeepSeek V4.1 Flash | reasoning forced **off** | 198 | 41 | 20.7% | $1.44 |
| GPT-5.6 Luna | default (~36% reasoning) | 199 | 43 | 21.6% | $3.79 |
| GPT-5.6 Luna | reasoning forced **off** | 199 | 19 | 9.5% | $2.68 |

**Reasoning meaningfully helps CTF-solving for 3 of 4 models; Solar Pro 4
is the outlier.** A manipulation check confirms the forced settings
actually took effect. For Solar Pro 4's default (reasoning-off) condition
— the arm this project's primary comparison relies on most, since it's
*inferred* from provider behavior rather than set via an explicit API
parameter — this check is now **exhaustive, not sampled**: every one of
its 195 full-run trajectories was scanned, and 0 of 2,409 assistant turns
used reasoning, across the entire run including the challenges the later
retry batch recovered. Solar Pro 4's forced-**on** run reasoned on 171/171
(100%) sampled turns, and the three forced-**off** re-runs reasoned on
0/175, 1/184, and 0/186 sampled turns (Qwen/DeepSeek/Luna) — these four
checks (Solar's forced-on plus the three forced-off re-runs) all predate
the retry batch and were not re-run exhaustively, since in every one of
these four cases the setting is enforced via an explicit `extra_body` API
parameter rather than inferred from default behavior the way Solar's
reasoning-off arm is. So Solar Pro 4's null result
is a genuine finding, not a broken flag. This contrasts with [Part 1's
CyberMetric result](../README.md#does-reasoning-help-accuracy), where
reasoning has no measurable effect for *any* model — reasoning helps on
this agentic, multi-step task in a way it doesn't on closed-book MCQ.

Total cost of the reasoning-controlled re-runs: $2.52 + $1.50 + $1.44 +
$2.68 = **$8.14**, on top of the $12.00 full-run cost.

## Results: uncontrolled full-200 run (2026-09-19)

The original run, before reasoning was controlled. A 2026-09-20/21 retry
batch closed most of the "attempted" gaps (see [Appendix
B](#appendix-b-operational-incident-log)); the numbers below are the final,
post-retry counts. Included for its larger per-model sample (up to 200 vs.
the 190 above) and because it's the source of the "attempted" imbalance
discussed in [Limitations](#limitations); the [reasoning-controlled
comparison](#results-reasoning-controlled-comparison-n196) above is still
the one to cite for cross-model claims, since this run never controlled
for reasoning.

| Model | Attempted/200 | Solved | Solve rate (of attempted) | Avg wall time | Total cost |
|---|---|---|---|---|---|
| DeepSeek V4.1 Flash | 197 | 70 | 35.5% | 330s | $1.83 |
| GLM 5.3 Flash | 179 | 62 | 34.6% | 293s | $2.39 |
| Qwen3.8 Flash | 189 | 48 | 25.4% | 258s | $2.18 |
| GPT-5.6 Luna | 199 | 43 | 21.6% | 165s | $3.79 |
| Solar Pro 4 | 198 | 13 | 6.6% | 143s | $1.80 |

Total cost across all 5 models, 1000 jobs: **$12.00**. Full per-run data:
[`eval_results_full.jsonl`](eval_results_full.jsonl) (1000 rows),
aggregated in [`eval_summary_full.json`](eval_summary_full.json).

**Attempted counts are still not a perfectly clean denominator** (179–199
of 200, up from an original 83–175 spread before the repair passes — see
[Limitations](#limitations) for why the remaining gap isn't just noise
either). Restricting to the **169 challenges all 5 models actually
attempted** controls for this directly:

| Model | Solved (of 169) | Solve rate |
|---|---|---|
| DeepSeek V4.1 Flash | 64 | 37.9% |
| GLM 5.3 Flash | 59 | 34.9% |
| Qwen3.8 Flash | 45 | 26.6% |
| GPT-5.6 Luna | 40 | 23.7% |
| Solar Pro 4 | 13 | 7.7% |

Pairwise McNemar within this n=169 set:

| Pair | b, c | p |
|---|---|---|
| DeepSeek V4.1 Flash vs Solar Pro 4 | 51, 0 | **<0.0001** |
| GLM 5.3 Flash vs Solar Pro 4 | 47, 1 | **<0.0001** |
| Qwen3.8 Flash vs Solar Pro 4 | 33, 1 | **<0.0001** |
| GPT-5.6 Luna vs Solar Pro 4 | 28, 1 | **<0.0001** |
| DeepSeek V4.1 Flash vs GPT-5.6 Luna | 31, 7 | **0.0001** |
| DeepSeek V4.1 Flash vs Qwen3.8 Flash | 25, 6 | **0.0009** |
| GLM 5.3 Flash vs GPT-5.6 Luna | 28, 9 | **0.0026** |
| GLM 5.3 Flash vs Qwen3.8 Flash | 24, 10 | **0.0243** |
| DeepSeek V4.1 Flash vs GLM 5.3 Flash | 16, 11 | 0.442 |
| Qwen3.8 Flash vs GPT-5.6 Luna | 16, 11 | 0.442 |

At n=61 (the original common-attempted sample, before the repair passes),
this looked like a single clean story: Solar Pro 4 significantly worse
than every other model, the other 4 statistically indistinguishable from
each other. **At n=169, that second half no longer holds** — DeepSeek V4.1
Flash is now significantly ahead of GPT-5.6 Luna and Qwen3.8 Flash, and
GLM 5.3 Flash is significantly ahead of GPT-5.6 Luna and (suggestively)
Qwen3.8 Flash. DeepSeek V4.1 Flash and GLM 5.3 Flash remain statistically
indistinguishable from each other, as do Qwen3.8 Flash and GPT-5.6 Luna.
**As established in [Results: reasoning-controlled
comparison](#results-reasoning-controlled-comparison-n196), the Solar Pro
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
| This project | 5 budget-tier models | Same baseline harness as the original paper, 1 attempt, 12 rounds | 6.6%–35.5% |

**Read this as a caveat about the numbers in this project, not a
capability claim.** **4 of 5 models** here score at or above the 2024
SOTA-with-better-tooling (EnIGMA, 13.5%), and 2 (DeepSeek V4.1 Flash, GLM
5.3 Flash) exceed CTF-Dojo's number — a model *specifically fine-tuned* on
CTF-solving trajectories — with Qwen3.8 Flash approaching it (25.5% vs.
31.9%), despite using the
*weaker* plain baseline harness (no tool-use enhancements) and a *harsher*
protocol (1 attempt / 12 rounds vs. the original paper's 5 attempts / 48
hours). That combination is hard to explain by "these models got better at
reasoning" alone, for those 4. The more likely explanation is
**training-data contamination**: these are real 2017–2023 CTF competition
challenges with public writeups, and a 2026-era model has had far more
opportunity to see them during training than GPT-4/Claude 3 (2023–2024
training cutoffs). **Solar Pro 4 is the exception**: at 6.6%, it scores
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
  far less than before: 179–199 of 200 in the uncontrolled run, 197–199
  in the reasoning-controlled comparison — up from 83–175 and 83–172
  respectively before the 2026-09-20/21 and 2026-09-22 repair passes (see
  [Appendix B](#appendix-b-operational-incident-log)). Every headline
  comparison still restricts to a fixed common subset (n=169 or n=196) to
  control for whatever imbalance remains, and these subsets now cover
  85%–98% of the full 200. What is left is 1 challenge that cannot start
  on this machine at all, a handful of per-model 900s timeouts that
  reproduced on a second idle-machine run, and 3 cells lost to a provider
  rate limit — not a fixable-by-retrying residue.
- **The recovered ("gap-fill") rows solve at a lower rate than the
  originally-attempted rows, in 4 of 5 full-run conditions** — Solar Pro 4
  3.5% (4/115) vs. 10.8% originally, Qwen3.8 Flash 14.5% (8/55) vs. 29.9%,
  GLM 5.3 Flash 26.2% (16/61) vs. 39.0%, GPT-5.6 Luna 12.5% (3/24) vs.
  22.9% (DeepSeek V4.1 Flash is the exception: 39.3%, 11/28, vs. 34.9%). The challenges that previously failed on
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
- **Multiple comparisons.** The n=169 table runs 10 pairwise tests and the
  n=196 table runs 6; treat p-values in the 0.01–0.05 range as suggestive,
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
- [`strip_docker_sock.py`](strip_docker_sock.py) — **63 of the 200 test-split
  challenges bind-mount the host's `/var/run/docker.sock` into the challenge
  container as shipped** (2 more run `privileged: true`), a leftover from the
  original CSAW challenges using docker-in-docker to spawn per-player
  instances. A container holding the host Docker socket can create further
  containers with arbitrary mounts, i.e. it is equivalent to root on the
  host — and this benchmark exists to have an LLM agent find and exploit
  bugs in exactly those services, so a successful exploit lands code
  execution inside a container that can reach the host. Auditing all 1,732
  trajectories from the runs above found no agent ever went near it (every
  solve just read the flag, and the agent's own container has no socket:
  it runs as `docker run -d --rm --network ctfnet --platform linux/amd64
  ctfenv`, with no mounts at all), but the path shouldn't be open. This
  module removes those mounts, and the three drivers call it at startup
  since re-downloading the dataset restores them.
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
parsing code), and two repair passes (2026-09-20/21 and 2026-09-22) that
closed the original "attempted" gap (83–175→179–199 of 200) by fixing the
underlying infrastructure rather than accepting it — see [Appendix
B](#appendix-b-operational-incident-log). **Total cost across all phase 2
runs: $20.60** ($12.00 full-200 + $0.45 n=10 pilot + $8.14
reasoning-controlled).

Not yet done:

- **A fully uniform re-run of every job under identical conditions** —
  would close the residual 1–21-per-model "attempted" gap rather than
  controlling for it on a fixed common subset. Not attempted: the two
  repair passes already cut the gap by roughly 5x, and what remains is
  dominated by causes a uniform re-run would hit again (a challenge whose
  container cannot start on Apple Silicon, timeouts that reproduced on an
  idle machine, and a provider-side rate limit) — see
  [Appendix B](#appendix-b-operational-incident-log).
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

5. **2026-09-22 repair pass.** The first retry batch left 10 challenges
   that still would not run. Investigating each one individually (rather
   than recording them as model failures) found three more root causes, all
   of them producing results that look exactly like "the model didn't solve
   it":
   - **A self-deadlock on multi-port challenges.** `challenge_ports.json`
     records `2019f-web-biometric` as publishing 15000 and 5001, but the
     compose file publishes 5001 and 49186. The stale-port recovery added
     in the previous pass therefore resolved 15000 → 5001, handing
     `run_one` the list `['5001', '5001']` — and acquiring the same
     non-reentrant `threading.Lock` twice deadlocks that worker forever,
     which then strands every later job needing that port. The whole pool
     went idle with 8 jobs queued. Fixed in two places: the recovery now
     excludes ports already covered by the challenge's own list, and the
     drivers de-duplicate before locking.
   - **The disk-cleanup loop was deleting images mid-run.**
     `docker_cleanup_loop.sh` removed every `llmctf/*` image not currently
     running, every 180s, regardless of free space. A challenge image
     pulled for the next job was often gone before the job started, which
     surfaces as a 2–4 second `docker compose` failure. Worse, the
     locally-built `biometric_client` image is not in the registry, so
     deleting it broke that challenge permanently until rebuilt by hand.
     Now it only prunes when disk is actually tight and never touches
     images it cannot re-pull.
   - **A rotted challenge image build.** `2019f-web-biometric` builds from
     `python:3.6` (Debian 11), whose apt repositories moved to
     `archive.debian.org`; its security suite is not archived at all; and
     its pinned `cmake==3.15.3` has no arm64 wheel. Patched the challenge's
     Dockerfile to use the archive, drop the security line, pin
     `cmake==3.15.3.post1`, and build with `platform: linux/amd64`. The
     challenge went from failing for all 5 models to running for all of
     them.

   After the fixes, 7 of the 10 challenges produced real data. The
   remaining 3 are genuine: `2023q-web-rainbow_notes` (runc bug, above),
   a few 900s timeouts that reproduced on a second run with an idle
   machine — so they are the model's limit, not load — and 3 Qwen3.8 Flash
   cells lost to a provider-side rate limit that four attempts across 45
   minutes could not clear. Rate-limited runs are recorded as *not
   attempted* rather than as failures, since a throttled run is not a fair
   attempt.

Rows corrupted by incidents 1 and 2 (8 + 71 rows) were identified by error
signature and given a real retry, since those failures were transient
infrastructure issues unrelated to model behavior. Rows corrupted by
incident 3 (5 rows, all Solar Pro 4) were reclassified but not retried, per
the reasoning above. Full detection logic is in the commit history
(`8820d01`, `a8b2c41`); incident 4's fixes are in `dynamic_ports.py` and
the three driver scripts, this session's commits.

[nyuctf-agents]: https://github.com/NYU-LLM-CTF/nyuctf_agents
