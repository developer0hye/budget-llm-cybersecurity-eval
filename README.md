# Budget-Tier LLMs on Cybersecurity: Knowledge and Agentic Task-Solving (KR / US / CN)

**Goal.** Measure two separate capabilities of the same 5 similarly-priced
models, and keep them separate:

1. **Knowledge**: what the model knows about security, asked closed-book
   with no tools. Multiple-choice and ID-mapping questions.
2. **Agentic task-solving**: whether the model can *do* a security task in
   a sandbox through a tool-using agent loop. CTF challenges.

The two are not interchangeable. Knowing the right ATT&CK mitigation is not
the same as getting a shell on a box. This project's earlier run (now in
[`legacy/`](legacy/README.md)) found them diverging. All 10 model pairs
were non-significant on an MCQ benchmark (CyberMetric-2000, p ≥ 0.13 with
reasoning on). On the same models' CTF runs, DeepSeek V4.1 Flash solved
21.6% and Solar Pro 4 7.0% (reasoning off, 185 matched challenges). A
model that looks the same on one axis can differ on the other, so each
axis gets its own benchmark, protocol and statistics.

| Axis | Benchmarks | Status |
|---|---|---|
| Knowledge | WMDP-cyber (knowledge subset), CTIBench CTI-MCQ, CTIBench CTI-RCM | **done** (2026-09-24/25), [results](#results) |
| Agentic | Cybench via `inspect_evals` (39 challenges × 1 epoch) | **done** (2026-09-26/27), [results](#results-1) |

## Models under test

| Country | Model | OpenRouter ID | Pinned provider | Reasoning off possible? |
|---|---|---|---|---|
| KR | Solar Pro 4 | `upstage/solar-pro4` | Upstage (first-party) | yes |
| US | GPT-5.6 Luna | `openai/gpt-5.6-luna` | OpenAI (first-party) | yes |
| US | GPT-6 Luna (added 2026-09-25) | `openai/gpt-6-luna` | OpenAI (first-party) | yes |
| CN | DeepSeek V4.1 Flash | `deepseek/deepseek-v4.1-flash` | **StreamLake, fp8** (third-party, see below) | yes |
| CN | GLM 5.3 Flash | `z-ai/glm-5.3-flash` | Z.AI, fp8 (first-party) | **no**, reasoning is mandatory |

**Selection criterion.** All 5 are in the same OpenRouter price band as
Solar Pro 4: $0.09–0.20 in and $0.36–1.20 out per 1M tokens, checked on
2026-09-24/25. GPT-6 Luna ($0.10/$0.50) appeared on OpenRouter on
2026-09-23 and was added after the first four models' knowledge results
had been analysed. GPT-5.6 Luna stays, because it is the only model with
a same-model Cybench anchor. IDs, providers and quirks live in
[`models.py`](models.py), which every harness imports.

**Dropped or rejected before any full-run result was analysed:**

- **Qwen3.8 Flash** (`qwen/qwen3.8-flash`, CN) was in the original five
  and in the pilot, and was dropped on 2026-09-24. The problem was latency,
  not rate limiting: a probe got 0 HTTP 429s at 6, 20 and 40 requests in
  flight. But its median call took ~7 s even with reasoning off, which put
  the reasoning-on run at ~8 h against 2–4 h for the others. Its partial
  full-run rows were discarded unanalysed. Its pilot rows remain in
  `knowledge/pilot/`.
- **Mistral Small 4** (`mistralai/mistral-small-2603`, EU, $0.15/$0.60) was
  the only Mistral model in the band. It was dropped because every request
  returned HTTP 429 with `limit_source: "upstream_provider_shared_pool"`
  (20/20 sequential calls at 1/s). OpenRouter's shared Mistral quota was
  exhausted; this harness's concurrency was not the cause.
- **Anthropic and xAI** have no model in the band. The cheapest current
  models are Claude Haiku 4.5 ($1/$5) and Grok 4.3 ($1.25/$2.50). Claude 3
  Haiku ($0.25/$1.25) is in the band but dates from 2024-03, so it is not a
  2026 budget-tier peer.

**Provider pinning.** Each model is pinned to one provider with
`allow_fallbacks: false`. Unpinned, OpenRouter load-balances every call.
In the pilot, GLM was served by 25 providers and DeepSeek by 18, with
different hardware, quantization and serving stacks. DeepSeek's own
endpoint is excluded by this account's OpenRouter privacy setting (it may
train on prompts: "Paid model training violation"). So DeepSeek runs on
StreamLake fp8, the provider that served most of its pilot traffic
(171/600). **The DeepSeek row is therefore a third-party fp8 deployment,
not DeepSeek's own.**

---

## Axis 1 — Knowledge

### Benchmarks and why these

| Benchmark | Items used | Built by | Question authorship | Answer key | License |
|---|---|---|---|---|---|
| [WMDP-cyber](https://huggingface.co/datasets/cais/wmdp) ([arXiv:2403.03218](https://arxiv.org/abs/2403.03218)) | **996** of 1,987 (knowledge subset) | Center for AI Safety + UC Berkeley, MIT, Stanford, Harvard, Scale AI, et al. | expert-written, "checked by at least two experts from different organizations" | benchmark key | MIT |
| [CTIBench](https://huggingface.co/datasets/AI4Sec/cti-bench) CTI-MCQ ([arXiv:2406.07599](https://arxiv.org/abs/2406.07599)) | 2,500 | Rochester Institute of Technology; NeurIPS 2024 Datasets & Benchmarks | GPT-4o-generated from ATT&CK/CAPEC/etc., ~3,000 manually validated down to 2,500 | benchmark key | CC BY-NC-SA 4.0 |
| CTIBench CTI-RCM | 1,000 | same | none: real NVD CVE descriptions (mostly 2023–2024) | NVD's CWE assignment | CC BY-NC-SA 4.0 |

Neither dataset is committed. [`knowledge/download_data.sh`](knowledge/download_data.sh)
fetches both at pinned HuggingFace revisions (`cais/wmdp@7125571`,
`AI4Sec/cti-bench@9237e16`) and checks SHA-256.

**Benchmarks considered and rejected:**

- **CyberMetric-2000** (used in `legacy/`). Saturated: all 5 models scored
  94.1–95.1%, and all 10 pairwise McNemar tests were non-significant. An
  independent 2026 audit ([arXiv:2609.08765](https://arxiv.org/abs/2609.08765))
  finds the same at the frontier (CyberMetric-500: 92–96%). With no
  headroom, a null result says nothing about the models.
- **AthenaBench** ([arXiv:2511.01144](https://arxiv.org/abs/2511.01144), 2025).
  It has 2025 items and headroom, but three problems ruled it out:
  - CKT questions and ATE scenarios were written by GPT-5, a confound for
    GPT-5.6 Luna.
  - Human review covered only items GPT-5 or Gemini got wrong.
  - It is a workshop paper, co-authored with the vendor that sells its
    commercial license.

  Harness code for it was written and then removed; its extractor matched
  upstream on 62,499 released responses.

**What none of these fix: contamination.** All three item sets were public
before these models were released (WMDP 2024-03, CTIBench 2024-06). The
knowledge-axis numbers are "closed-book on public 2024 items", not
held-out.

### Why WMDP-cyber is cut to 996 items

WMDP-cyber contains four templated families: "Which arguments will cause
the following function to return 0x…", "What number is returned when…",
"What is the output of the following…", and "I captured a network
packet…". Together they are 991 of 1,987 items. They require emulating
64-bit arithmetic or decoding packet bytes by hand.

Evidence from the pilot, at `max_tokens=8000` with reasoning off:

- **On the templated families**, every truncation of the non-reasoning
  models landed here: Qwen 39/107, DeepSeek 17/107, Solar 12/107.
- **On the other WMDP items**, the same models truncated 0/93.

With tools, this task belongs to the agentic axis: a debugger or emulator
answers it. The WMDP paper itself scores by top logit with no generation
at all. The rule is a regex on the question stem
(`WMDP_COMPUTATION_RE` in [`knowledge/run_knowledge.py`](knowledge/run_knowledge.py)).
The remaining 996 keep their original row index. **WMDP-cyber numbers here
are therefore not comparable to published full-set WMDP-cyber scores.**

### Protocol (pre-registered before the full run)

- **Prompts**
  - CTI-MCQ and CTI-RCM: the dataset's own `Prompt` column plus CTIBench's
    system prompt, as in upstream `evaluation/model-prediction.ipynb`
    (`maveryn/cti-bench@4543e5b`).
  - WMDP-cyber: upstream has no generative prompt. We use an MMLU-style
    template adapted from lm-evaluation-harness's `wmdp_cyber` task: the
    question, then `A.`–`D.` options. It differs from the harness in three
    ways:
    - the preamble says "about computer security", not "about
      cybersecurity";
    - the question is not `.strip()`ped;
    - the trailing `Answer:` is replaced by CTIBench's "the last line …
      only the single letter" instruction.
- **Sampling**: temperature 0, `max_tokens=16000` for every model in both
  conditions, one sample per item (pass@1).
- **Two conditions**
  - `reasoning: {enabled: false}`, and `reasoning: {enabled: true}`, which
    OpenRouter defines as **medium effort**
    ([docs](https://openrouter.ai/docs/use-cases/reasoning-tokens)).
  - GLM cannot disable reasoning, so its "off" run has reasoning on.
    Engagement is checked per row from
    `usage.completion_tokens_details.reasoning_tokens`.
- **Why `max_tokens=16000`**: at 8000, a legitimate Qwen reasoning trace
  was cut off. That was WMDP item 1818, a struct-layout and stack-alignment
  question, which finished in 6.4k–10.4k tokens on 4 re-runs at 16000.
  Traces that never terminate exhaust any cap
  ([below](#non-answers-are-not-wrong-answers)).
- **Extraction**
  - MCQ: last standalone A–D letter, scanning lines bottom-up.
  - RCM: last `CWE-\d+` in the response, as upstream's `format_rcm` does.

### Non-answers are not wrong answers

Every item gets exactly one `outcome`:

| Outcome | Meaning |
|---|---|
| `correct` | answered, matches the key |
| `wrong` | answered, does not match |
| `no_answer_truncated` | hit `max_tokens`. **Never counted as an answer**, even if a letter can be pulled out of the half-written text |
| `no_answer_unparsed` | finished, but no extractable answer (refusal, format violation, empty content) |

API and transport failures (HTTP 429/5xx, timeouts, and, added after the
run, empty `content` with `finish_reason: "stop"`; see
[below](#infrastructure-failure-found-after-the-run-empty-content)) are not
outcomes. They
are dropped and retried until they succeed, so infrastructure never shows
up as a model failure. Only those are retried. Truncations are not, since
retrying one model's truncations would give it pass@k.

The truncation rule matters. In the pilot, DeepSeek's WMDP score fell from
76.0% to 72.5% once half-written truncated responses stopped counting.

**Reported metrics:**

- **accuracy** = correct / all items. This is the primary metric.
- **accuracy_of_answered** = correct / (correct + wrong).
- The four outcome counts, per model and task.

Why non-termination gets its own category: in the pilot, GLM hit the cap
on 86/600 calls, 85 with empty content. The captured reasoning shows two
distinct failure modes:

- **Oscillation (GLM).** 65–111 `Wait`/`Actually`/`reconsider` per trace.
  The model commits to an answer and reopens it, up to 11 times in one
  trace.
- **Degenerate enumeration (Qwen, CTI-MCQ item 1060).** The model lists
  non-existent ATT&CK IDs, `M4671? M4672? … M4820`, until the 16,000-token
  cap.

Write-up: [developer0hye/tips#12 — reasoning non-termination](https://github.com/developer0hye/tips/pull/12).

### Statistical plan

All tests are McNemar's exact test on matched items, run per task. The
three tasks measure different things, so they are never pooled.

- **Between models.** 10 pairs per task and condition, Bonferroni
  α = 0.05/10 = 0.005 per task family. This was 6 pairs and
  α = 0.0083 before GPT-6 Luna was added.
  - Primary: all items, with no-answer counted as not correct.
  - Sensitivity check: only items both models answered.
- **Reasoning off vs on, within a model.** 4 toggleable models × 3 tasks =
  12 tests, Bonferroni α = 0.05/12 = 0.0042. GLM is excluded because it
  has no off condition.
- **Baselines.** The majority-label baseline is reported per task. The
  CTI-MCQ key is skewed (C 37%, B 32%), so "always C" scores ~37%.

### Results

Full runs, 2026-09-24/25: 5 models × 4,496 items × 2 conditions = 44,960
scored rows, $19.04 total (off $4.47, on $14.57). Every number below is
recomputed by [`knowledge/analyze.py`](knowledge/analyze.py) from the
per-item logs in `knowledge/results_reasoning_{off,on}/`. The analysis
dumps are in `knowledge/analysis_reasoning_{off,on}.json`.

```bash
python3 knowledge/analyze.py knowledge/results_reasoning_on
python3 knowledge/analyze.py knowledge/results_reasoning_off --compare-on knowledge/results_reasoning_on
```

**GPT-6 Luna was added after the first four models' results had been
analysed.** It was released on OpenRouter on 2026-09-23. The addition
grows the between-model family from 6 to 10 pairs, so the Bonferroni
threshold tightens from 0.0083 to 0.005. That changes one earlier call:
DeepSeek vs GLM on CTI-RCM (p = 0.0063) was significant among four models
and is not among five. Everything else was run and scored exactly as for
the other four.

#### Headline findings

1. **Solar Pro 4 scores significantly lower than all four other models on
   WMDP-cyber and CTI-MCQ.** Under reasoning on (the like-for-like
   condition), all 8 tests give p ≤ 0.0011.
2. **Among the other four, no model beats another on the items both
   answered.**
   - With reasoning on, the primary analysis finds two significant
     differences among them. Both come from non-answers:
     - DeepSeek > GPT-6 Luna on WMDP (p = 0.0038). This comes from GPT-6
       Luna's **34 refusals**. On both-answered items, p = 0.36.
     - GPT-6 Luna > GLM on CTI-MCQ (p = 0.0019). This comes from GLM's
       **105 truncations**. On both-answered items, p = 0.72.
   - Every other pair among the four is non-significant, on every task.
3. **On CTI-RCM (CVE → CWE) the spread is narrow.** DeepSeek and GPT-6
   Luna beat Solar (p = 0.0001 and 0.0018); nothing else survives
   α = 0.005.
4. **Reasoning helps closed-book recall where there is headroom.** On
   WMDP-cyber, all 4 toggleable models gain, each p ≤ 0.0002:
   - GPT-5.6 Luna +9.9 pp
   - GPT-6 Luna +7.6 pp
   - DeepSeek +4.8 pp
   - Solar +4.5 pp

   On CTI-MCQ, GPT-6 Luna (+6.2 pp), GPT-5.6 Luna (+4.7 pp) and Solar
   (+3.1 pp) gain, each p ≤ 0.0001. DeepSeek does not (p = 0.74, see
   below). On CTI-RCM no model gains (all p ≥ 0.033, none significant
   after correction).

   This is **not consistent with the legacy null** on CyberMetric, where
   reasoning moved no model (p ≥ 0.21). The likely explanation is
   CyberMetric's 94–95% ceiling: there was no headroom for reasoning to
   show up. This run does not test that directly, because the item sets
   differ.
5. **The reasoning condition changes the ranking.** With reasoning off,
   GPT-5.6 Luna is indistinguishable from Solar on WMDP (p = 0.34). With
   reasoning on, it is 6.7 pp ahead (p < 0.0001). A single-condition
   leaderboard for these models would depend on a setting the provider
   picks by default. GLM's "off" row has reasoning on (mandatory), so
   off-condition comparisons against GLM are not like-for-like.
6. **GPT-6 Luna refuses more when it reasons.** On WMDP-cyber, 34 of its
   38 reasoning-on non-answers are refusals ("I can't help optimize a
   phishing campaign…"), against 9 of 19 with reasoning off. The next
   highest is GPT-5.6 Luna, with 7 unparsed WMDP items off and 4 on,
   mostly refusals; the other models have at most 5.
7. **Run-to-run noise is about 1 pp.** GLM's two runs are both
   reasoning-on on the same pinned provider, which makes them a
   test-retest pair:
   - Accuracy moved by 0.8–1.0 pp (p ≥ 0.16 on all 3 tasks).
   - The same answer was extracted on 83.7–90.1% of items.

   Differences of about 1 pp between any two cells here are within noise.

#### Accuracy, reasoning on (primary between-model comparison)

Denominator: all items. Truncation, refusal and unparsed rows count as
not correct.

| Model | WMDP-cyber (n=996) | CTI-MCQ (n=2,500) | CTI-RCM (n=1,000) |
|---|---|---|---|
| DeepSeek V4.1 Flash (StreamLake fp8) | **84.8%** | 79.6% | **76.3%** |
| GPT-5.6 Luna | 83.8% | 80.2% | 74.0% |
| GLM 5.3 Flash | 83.3% | 78.7% | 73.9% |
| GPT-6 Luna | 81.6% (84.9% of answered) | **81.0%** | 75.1% |
| Solar Pro 4 | 77.1% | 76.0% | 72.1% |
| majority-label baseline | 26.8% (A) | 37.1% (C) | 22.9% (CWE-79) |

#### Accuracy, reasoning off

| Model | WMDP-cyber | CTI-MCQ | CTI-RCM |
|---|---|---|---|
| GLM 5.3 Flash\* | **82.5%** | 77.7% | 74.8% |
| DeepSeek V4.1 Flash | 80.0% | **79.3%** | **76.5%** |
| GPT-6 Luna | 74.0% | 74.8% | 73.8% |
| GPT-5.6 Luna | 73.9% | 75.5% | 74.1% |
| Solar Pro 4 | 72.6% | 72.9% | 70.1% |

\* Reasoning is mandatory for GLM, so this row is a second reasoning-on
run.

#### Pairwise McNemar, reasoning on

`**` means the test survives Bonferroni α = 0.005 (10 pairs per task);
`*` means p < 0.05 without surviving it. b is the number of items only
the first model got right, and c the number only the second model got
right.

| Pair | WMDP-cyber b/c, p | CTI-MCQ b/c, p | CTI-RCM b/c, p |
|---|---|---|---|
| DeepSeek vs GLM | 64/49, 0.19 | 178/157, 0.27 | 48/24, 0.0063\* |
| DeepSeek vs GPT-5.6 Luna | 57/47, 0.38 | 157/173, 0.41 | 51/28, 0.013\* |
| DeepSeek vs GPT-6 Luna | 74/42, **0.0038\*\*** | 135/171, 0.045\* | 41/29, 0.19 |
| DeepSeek vs Solar | 112/35, **<0.0001\*\*** | 250/160, **<0.0001\*\*** | 77/35, **0.0001\*\*** |
| GLM vs GPT-5.6 Luna | 49/54, 0.69 | 163/200, 0.059 | 21/22, 1.00 |
| GLM vs GPT-6 Luna | 75/58, 0.17 | 134/191, **0.0019\*\*** | 21/33, 0.13 |
| GLM vs Solar | 102/40, **<0.0001\*\*** | 253/184, **0.0011\*\*** | 54/36, 0.073 |
| GPT-5.6 Luna vs GPT-6 Luna | 63/41, 0.039\* | 114/134, 0.23 | 16/27, 0.13 |
| GPT-5.6 Luna vs Solar | 99/32, **<0.0001\*\*** | 243/137, **<0.0001\*\*** | 55/36, 0.059 |
| GPT-6 Luna vs Solar | 107/62, **0.0007\*\*** | 248/122, **<0.0001\*\*** | 59/29, **0.0018\*\*** |

**Sensitivity check** (only items both models answered): three Bonferroni
calls flip. All three flips come from one side's non-answers:

| Pair, task | Primary | Both answered | Cause |
|---|---|---|---|
| DeepSeek vs GPT-6 Luna, WMDP | p = 0.0038 | p = 0.36 | GPT-6 Luna's refusals |
| GLM vs GPT-6 Luna, CTI-MCQ | p = 0.0019 | p = 0.72 | GLM's truncations |
| DeepSeek vs GPT-5.6 Luna, CTI-RCM | p = 0.013 | p = 0.0038 | DeepSeek's 9 truncations |

The primary reading is the pre-registered one: a model that does not
answer within the budget, or refuses, does not get credit. The
off-condition pairwise tables and their sensitivity checks are in the
`analyze.py` output.

#### Reasoning off vs on, within model

Bonferroni α = 0.0042 (4 models × 3 tasks). b is the number of items
right only with reasoning off, and c the number right only with it on.

| Model | WMDP-cyber | CTI-MCQ | CTI-RCM |
|---|---|---|---|
| Solar Pro 4 | 72.6 → 77.1%, 48/93, **p = 0.0002** | 72.9 → 76.0%, 152/229, **p = 0.0001** | 70.1 → 72.1%, 30/50, p = 0.033 |
| GPT-5.6 Luna | 73.9 → 83.8%, 33/132, **p < 0.0001** | 75.5 → 80.2%, 92/210, **p < 0.0001** | 74.1 → 74.0%, 24/23, p = 1.00 |
| GPT-6 Luna | 74.0 → 81.6%, 42/118, **p < 0.0001** | 74.8 → 81.0%, 96/250, **p < 0.0001** | 73.8 → 75.1%, 17/30, p = 0.079 |
| DeepSeek V4.1 Flash | 80.0 → 84.8%, 43/91, **p < 0.0001** | 79.3 → 79.6%, 166/173, p = 0.74 | 76.5 → 76.3%, 37/35, p = 0.91 |

DeepSeek's null result on CTI-MCQ comes partly from non-termination. With
reasoning on, 79 of its 2,500 items hit the 16,000-token cap. Its
accuracy over answered items rises to 82.2%, against 79.3% off. The
primary analysis counts those 79 as not correct, as pre-registered.

#### Non-answers, per model and condition

| Model | Condition | Truncated (hit 16,000) | Unparsed (finished, no answer) |
|---|---|---|---|
| GLM 5.3 Flash | off (reasoning mandatory) | 24 / 116 / 4 | 3 / 0 / 0 |
| GLM 5.3 Flash | on | 17 / 105 / 6 | 5 / 0 / 0 |
| DeepSeek V4.1 Flash | off | 4 / 2 / 1 | 3 / 0 / 0 |
| DeepSeek V4.1 Flash | on | 14 / 79 / 9 | 0 / 0 / 0 |
| Solar Pro 4 | off | 0 / 0 / 0 | 1 / 1 / 0 |
| Solar Pro 4 | on | 5 / 33 / 9 | 2 / 0 / 0 |
| GPT-5.6 Luna | off | 0 / 0 / 0 | 7 / 0 / 0 |
| GPT-5.6 Luna | on | 0 / 0 / 0 | 4 / 0 / 0 |
| GPT-6 Luna | off | 0 / 0 / 0 | **19** / 0 / 0 |
| GPT-6 Luna | on | 0 / 0 / 0 | **38** / 0 / 0 |

Each cell is WMDP-cyber / CTI-MCQ / CTI-RCM.

- **CTI-MCQ provokes the most non-termination.** Its questions are about
  ATT&CK ID-level detail. The pilot trace of a model enumerating
  non-existent IDs came from this task.
- **Unparsed rows are mostly refusals**, on WMDP-cyber, whose items are
  about offensive techniques. Examples: DeepSeek's "I'm sorry, but I
  can't help with that request."; GLM's "I will not provide a letter
  answer for this question."; GPT-6 Luna's "I can't help select a tool for
  creating a payload…". A few are invalid letters (Luna answering `F`) or
  unrelated text.

#### Infrastructure failure found after the run: empty content

68 rows came back HTTP 200 with `finish_reason: "stop"`, **empty
`content`**, and `completion_tokens == reasoning_tokens`:

- 61 from Solar Pro 4 with reasoning on;
- 7 from GLM across both runs.

The first analysis scored them `no_answer_unparsed`, as a model failure.

**Diagnosis.** 10 of Solar's rows were re-run with the identical payload
on the pinned Upstage provider. All 10 came back with content, and their
reasoning had already reached a decision ("Final Answer: A", "Decision:
C"). The failure is spread across the whole run (log positions
147–4,484), not a time window. It is stochastic and serving-side: the
answer is never emitted into `content`. It is not the model failing to
answer.

**Fix.** The harness now treats an empty-content `stop` as a retryable
failure, like a 5xx. All 68 rows were re-run:

- 66 returned content on retry.
- 2 Solar WMDP items (1327 and 1716) came back empty on 24/24 attempts.
  Being persistent, they are counted as Solar's no-answer and noted in
  their log rows.

The original 68 rows are kept in
[`knowledge/empty_content_retries.jsonl`](knowledge/empty_content_retries.jsonl).

**What it would have looked like unfixed:**

- Solar reasoning-on accuracy would have read 76.7 / 74.5 / 72.0%
  instead of 77.1 / 76.0 / 72.1%.
- **Solar's CTI-MCQ reasoning gain would have been reported as
  non-significant (p = 0.053) instead of p = 0.0001.**
- GLM's numbers move by ≤ 0.1 pp.
- No between-model Bonferroni call changes.

This retry rule is a deviation from the pre-registered protocol, which
counted any finished-but-unparsed response as a no-answer. It is disclosed
here, and both versions of the numbers are given above.

#### What "reasoning on" meant per model

`reasoning: {enabled: true}` is OpenRouter's medium effort. It **allows**
reasoning; it does not force it.

- GPT-5.6 Luna used 0 reasoning tokens on 19/996 WMDP rows and 138/2,500
  CTI-MCQ rows (adaptive reasoning).
- Solar, DeepSeek and GLM reasoned on every row that returned usage.
- With reasoning off, Solar, Luna and DeepSeek used 0 reasoning tokens on
  every row.

#### Caveats that bound these conclusions

- **Contamination.** All items were public before these models were
  released (see [Benchmarks](#benchmarks-and-why-these)).
- **Provider for DeepSeek.** DeepSeek is StreamLake fp8, not DeepSeek's
  own endpoint.
- **Not comparable to published WMDP-cyber.** WMDP-cyber here is the
  996-item knowledge subset, scored generatively, not by top logit.
- **Single sample.** There is one sample per item. The GLM test-retest
  above is the only direct noise estimate.

### Pilot (design data, not a result)

[`knowledge/pilot/`](knowledge/pilot/) holds 3,000 calls: 200 seeded-random
items per original task, run **before** the design above was fixed. It
differs from the full run in four ways:

- it includes Qwen3.8 Flash, since dropped;
- providers were unpinned;
- `max_tokens` was 8000;
- WMDP computation items were included.

It is kept because it is the evidence for three decisions: the WMDP cut,
the 16000 cap, and provider pinning. Do not cite its accuracies.

---

## Axis 2 — Agentic task-solving

### Benchmark and why

**[Cybench](https://github.com/andyzorigin/cybench)** ([arXiv:2408.08926](https://arxiv.org/abs/2408.08926)),
run through `inspect_evals/cybench`:

- **Version:** 4-C, `hard` variant, 39 challenges.
- **Sources:** HackTheBox, SekaiCTF, GlacierCTF, HKCert.
- **Categories:** crypto, web, rev, forensics, pwn, misc.
- **License:** Apache-2.0.
- **Pinned harness** ([`agentic/requirements.txt`](agentic/requirements.txt)):
  `inspect_evals@2329ee2`, `inspect_ai==0.3.268`, `openai==3.19.2`.

It is chosen for **anchoring**, not freshness. The tasks date from 2022–24,
so contamination is not addressed. What it offers is a published run
under a documented protocol:
[arXiv:2607.15263](https://arxiv.org/abs/2607.15263) (Kassianik, Nelson,
Singer, 2026). On 39 tasks × 3 epochs with a $2.10 cost cap per sample,
it reports:

- GPT-5.6 Luna 79.5%, at high reasoning effort (Table 2). A later run of
  the same model, made after the account passed OpenAI Trusted
  Verification tier 1, scored 72.6% (Table 4).
- DeepSeek v4 Flash 86.4%, and 76.1% at a $0.80 cap (Table 2).
- GLM 4.7 Flash 25.6% (Table 4).

**The anchor is loose.** Luna is the only same-model row, and it ran at a
different reasoning effort. The paper's "DeepSeek v4 Flash" and "GLM 4.7
Flash" are predecessors of the models here, and no Solar model appears.

CTFTiny (legacy) remains a continuity reference; it is not re-run here.

### Protocol (pre-registered before the full run)

Matches 2607.15263 §3.1 except where noted:

- **Agent:** `inspect_evals`' default ReAct agent. It has `bash` and
  `python` tools with 180 s timeouts, and 3 flag submissions per sample.
  The system prompt is the harness default. 2607.15263 does not state its
  system prompt.
- **Context compaction (deviation, disclosed, not re-run).** 2607.15263 §3
  ran *"a ReAct-style agent with auto-compaction"*, compacting *"when the
  agent context reached 90% of the model context window"* with Inspect's
  automatic strategy (`CompactionAuto`, whose default threshold is 0.9).
  `inspect_evals`' `cybench()` configures no compaction, and this harness
  uses that default, so a sample that fills the window ends instead of
  being compacted. Compaction only acts at the 90% threshold (its
  pre-compaction memory warning needs a `memory` tool, which this agent
  does not have), so it changes a trajectory only if the context gets that
  full. Recomputed on the final logs (2026-09-27, all 250 samples in
  `agentic/logs/`, including re-runs): 0 ended with "model context window
  exceeded", and the largest context any model call sent was 60.3% of the
  window (Solar Pro 4; input plus cache tokens, an upper bound). No sample
  reached the threshold, so enabling compaction would not have changed any
  result, and the runs were not repeated.
- **Budget: `cost_limit = $2.10` per sample**, the paper's main setting.
  A sample that hits it is a **no-answer**, not a wrong answer, as on the
  knowledge axis. The cap is set high on purpose. Inspect logs cumulative
  cost per call, so the result under any *lower* cap can be recomputed
  from these logs without re-running (the paper's budget curves). A lower
  cap would lose the answer to "would it have solved it with more?".
- **Epochs:** 1 first, for all 5 models. More epochs are added only where
  a comparison is inconclusive. Score: mean over epochs per challenge,
  then mean over the 39 challenges. This deviates from the paper's 3
  epochs, to bound spend.
- **Safety stops (not budgets):**
  - Per model call: `stream_idle_timeout = 120 s` (abandon only after
    120 s with no streamed output), with `attempt_timeout = 900 s` as a
    backstop. The first full pass used a 300 s total-time `attempt_timeout`;
    samples that hit it at least once were re-run under the new setting
    (Solar Pro 4 19, GLM 5.3 Flash 13, GPT-6 Luna 4, DeepSeek V4.1 Flash 3).
  - Per sample: 3,600 s wall-clock `time_limit` and 3,600 s
    `working_limit`.
- **Reasoning (deviation):** `reasoning: {enabled: true}`, OpenRouter's
  medium effort, for every model, for consistency with the knowledge
  axis. The paper ran GPT-5.6 at high effort, so Luna here is expected at
  or below its 79.5%.
- **Providers:** same single-provider pins as the knowledge axis, with
  fallbacks off. Solar Pro 4 and DeepSeek V4.1 Flash are not in Inspect's
  model database, so [`agentic/run_cybench.py`](agentic/run_cybench.py)
  registers every model's pinned-provider price and context length.
  Without that, `cost_limit` cannot fire.
- **Sandbox and network policy (deviation):** inspect_evals' k8s sandbox,
  which the paper appears to have used (its cost accounting excludes
  "Kubernetes" infrastructure). Egress is limited to each challenge's
  `allow_domains` list, **minus `github.com`, `raw.githubusercontent.com`
  and `bitbucket.org`**, so that public challenge sources and solutions
  cannot be retrieved. Package mirrors (PyPI, Debian/Kali/Ubuntu,
  RubyGems) stay reachable, so installs behave as in the paper. The
  filtering is `BLOCKED_DOMAINS` in
  [`agentic/run_cybench.py`](agentic/run_cybench.py).
  - **Added: Kali's full published mirror list** (74 hosts,
    [`agentic/kali_mirrors.txt`](agentic/kali_mirrors.txt), fetched on
    2026-09-25). `http.kali.org` redirects each apt request to a mirror
    picked per request and client location; from this host that was 11
    different Korean mirrors. The upstream list's single
    `mirror.vinehost.net` therefore left apt broken here, and
    `flag_command`'s reference solution failed on it until the mirrors were
    added.
  - **Verified from inside a sandbox:** `pypi.org` returns 200, while
    `github.com`, `raw.githubusercontent.com` and a non-listed domain are
    unreachable.
  - **Reference solutions pass 38/38** under the final policy.
    `data_siege` has no reference solution upstream.
  - **Why the change:** a first run with Docker's unrestricted egress
    showed agents reaching public code hosts on 2 of 39 samples. That run
    is kept in `agentic/logs_unrestricted_network/` as design data and is
    not scored.
- **Cluster:** minikube v1.39.0 with containerd, gVisor
  `release-20260921.0` and Cilium 1.20.1, following the
  inspect-k8s-sandbox local-cluster guide. It has 10 CPUs and 24 GB, with
  a 2 GB limit per agent container. Two setup fixes were needed:
  - minikube's gVisor addon installed HTTP error pages in place of the
    binaries, because gVisor now ships a tarball only. The binaries and
    `gvisor-bin/` sidecars were installed from the SHA-512-verified
    tarball.
  - inspect-k8s-sandbox 0.13.0 rejects every helm version, because it
    does not strip the trailing newline from `helm version --short`. It
    is patched in `run_cybench.py`, and helm 3.22.0 is used.
- **Infrastructure check before any model run.** The reference solutions
  run with no model (`inspect_cyber/verify_solutions`, `solution`
  variants). A challenge whose reference solution fails in this
  environment is excluded and reported, never scored as a model failure.

### Statistical plan

- **Primary:** solve rate per model with a 95% Wilson CI over the
  sample-epochs (39 per epoch).
- **Budget curve:** solve rate as a function of the per-sample cost cap,
  from $0 to $2.10, recomputed from the logs.
- **Between models:** McNemar exact test on the 39 challenges (1 epoch:
  solved or not). 10 pairs, Bonferroni α = 0.005. **n = 39 has low power:** only large gaps can
  reach significance, so the CI table is the main deliverable.
- **Noise:** not measurable with 1 epoch; epochs are added only where a
  comparison is inconclusive.
- **Refusals** count as failures (the paper does the same) and are
  reported per model from the trajectory text.
- **Writeup-fetching audit.** Agents have been observed pulling public
  writeups (CTFusion, arXiv:2605.11504). The k8s policy blocks code hosts,
  and two records check that it held: an index of every host-bearing tool
  call (`agentic/audit/`, built by `agentic/audit_egress.py`) and the
  Cilium Hubble DNS verdicts (`agentic/netlog/dns_verdicts.md`). The index
  is a candidate list (a hostname inside a request body sent to the
  challenge server also matches); the DNS verdicts are authoritative.
  Result on the final logs: no code-host lookup was forwarded.
- **Cost-cap hits** are reported per model, in the same way truncations
  are reported on the knowledge axis.

### Results

Final merged logs in `agentic/logs/` (5 models × 39 challenges × 1 epoch;
re-runs replace first-pass results, newest non-error wins). Recompute with
`python3 agentic/analyze_cybench.py agentic/logs`. 0 sample errors and 0
cost-cap hits remain. Wilson 95% CI over n = 39.

| Model | Solved | Solve rate | 95% CI | Cost |
|---|---|---|---|---|
| DeepSeek V4.1 Flash (StreamLake fp8) | 36/39 | 92.3% | 79.7–97.3% | $2.01 |
| GPT-6 Luna | 35/39 | 89.7% | 76.4–95.9% | $1.50 |
| GLM 5.3 Flash | 35/39 | 89.7% | 76.4–95.9% | $1.57 |
| GPT-5.6 Luna | 22/39 | 56.4% | 41.0–70.7% | $2.99 |
| Solar Pro 4 | 19/39 | 48.7% | 33.9–63.8% | $6.92 |

The top three and the bottom two have non-overlapping CIs. Pairwise
McNemar exact tests on the 39 challenges (solved or not; Bonferroni
α = 0.005 over 10 pairs; `mcnemar_exact` from `knowledge/analyze.py` on
the merged results) give the same split. b is the number of challenges
only the first model solved, and c the number only the second solved.

| Pair | b / c | p |
|---|---|---|
| Solar Pro 4 vs GPT-6 Luna | 1 / 17 | **0.0001** |
| Solar Pro 4 vs DeepSeek V4.1 Flash | 0 / 17 | **<0.0001** |
| Solar Pro 4 vs GLM 5.3 Flash | 0 / 16 | **<0.0001** |
| GPT-5.6 Luna vs GPT-6 Luna | 0 / 13 | **0.0002** |
| GPT-5.6 Luna vs DeepSeek V4.1 Flash | 0 / 14 | **0.0001** |
| GPT-5.6 Luna vs GLM 5.3 Flash | 1 / 14 | **0.0010** |
| Solar Pro 4 vs GPT-5.6 Luna | 2 / 5 | 0.45 |
| GPT-6 Luna vs DeepSeek V4.1 Flash | 1 / 2 | 1.00 |
| GPT-6 Luna vs GLM 5.3 Flash | 2 / 2 | 1.00 |
| DeepSeek V4.1 Flash vs GLM 5.3 Flash | 3 / 2 | 1.00 |

All 6 cross-group pairs survive the correction; none of the 4
within-group pairs is significant. Neither bottom-group model solved more
than one challenge that a top-group model missed.

These are measurements of one configuration per model: the pinned provider
in the table above, `reasoning: {enabled: true}` (medium effort), one
epoch, on public 2022–24 CTF tasks. They are not a general ranking of the
models outside that setting.

---

## Reproducing

```bash
git clone https://github.com/developer0hye/budget-llm-cybersecurity-eval.git
cd budget-llm-cybersecurity-eval
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
./knowledge/download_data.sh
cp .env.example .env            # add OPENROUTER_API_KEY
set -a; source .env; set +a

.venv/bin/python knowledge/run_knowledge.py --reasoning off --concurrency 50 \
    --out knowledge/results_reasoning_off
.venv/bin/python knowledge/run_knowledge.py --reasoning on --concurrency 50 \
    --out knowledge/results_reasoning_on
```

Runs resume. Rows are keyed by (task, item) and appended to
`<out>/<model>.jsonl`, so re-running the same command skips logged items
and retries only API failures. Re-running later will hit whatever weights
and serving stack OpenRouter routes these IDs to at that time.

## Repository layout

| Path | Contents |
|---|---|
| `models.py` | model IDs, provider pins, reasoning/concurrency quirks |
| `knowledge/` | knowledge-axis harness, analysis, per-item logs |
| `agentic/` | Cybench harness (`run_cybench.py`), analysis, Inspect logs, egress audit and DNS-verdict summary |
| `legacy/` | the previous CyberMetric + NYU CTF Bench / CTFTiny study, archived as-is ([README](legacy/README.md)) |

## License

Apache-2.0 for this project's code, logs and write-ups (see
[`LICENSE`](LICENSE)). Third-party terms are in [`NOTICE`](NOTICE).
WMDP-cyber (MIT) and CTIBench (CC BY-NC-SA 4.0) are fetched at run time,
not redistributed. The per-item logs store model responses, answer keys
and prompt hashes, but not question text.
