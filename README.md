# Budget-Tier LLMs on Cybersecurity: Knowledge and Agentic Task-Solving (KR / US / CN)

**Goal.** Measure two separate capabilities of the same 4 similarly-priced
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
| Agentic | Cybench via `inspect_evals`, CTFTiny as anchor | planned |

## Models under test

| Country | Model | OpenRouter ID | Pinned provider | Reasoning off possible? |
|---|---|---|---|---|
| KR | Solar Pro 4 | `upstage/solar-pro4` | Upstage (first-party) | yes |
| US | GPT-5.6 Luna | `openai/gpt-5.6-luna` | OpenAI (first-party) | yes |
| CN | DeepSeek V4.1 Flash | `deepseek/deepseek-v4.1-flash` | **StreamLake, fp8** (third-party, see below) | yes |
| CN | GLM 5.3 Flash | `z-ai/glm-5.3-flash` | Z.AI, fp8 (first-party) | **no**, reasoning is mandatory |

**Selection criterion.** All 4 are in the same OpenRouter price band as
Solar Pro 4: $0.09–0.20 in and $0.36–1.20 out per 1M tokens, checked on
2026-09-24. IDs, providers and quirks live in
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

- **Between models.** 6 pairs per task and condition, Bonferroni
  α = 0.05/6 = 0.0083 per task family.
  - Primary: all items, with no-answer counted as not correct.
  - Sensitivity check: only items both models answered.
- **Reasoning off vs on, within a model.** 3 toggleable models × 3 tasks =
  9 tests, Bonferroni α = 0.05/9 = 0.0056. GLM is excluded because it has
  no off condition.
- **Baselines.** The majority-label baseline is reported per task. The
  CTI-MCQ key is skewed (C 37%, B 32%), so "always C" scores ~37%.

### Results

Full runs, 2026-09-24/25: 4 models × 4,496 items × 2 conditions = 35,968
scored rows, $18.44 total (off $4.36, on $14.08). Every number below is
recomputed by [`knowledge/analyze.py`](knowledge/analyze.py) from the
per-item logs in `knowledge/results_reasoning_{off,on}/`. The analysis
dumps are in `knowledge/analysis_reasoning_{off,on}.json`.

```bash
python3 knowledge/analyze.py knowledge/results_reasoning_on
python3 knowledge/analyze.py knowledge/results_reasoning_off --compare-on knowledge/results_reasoning_on
```

#### Headline findings

1. **Solar Pro 4 is significantly behind the other three on WMDP-cyber and
   CTI-MCQ.** This holds under reasoning on, the only condition where all 4
   models run the same protocol: all 6 of those tests give p ≤ 0.0011.
   DeepSeek V4.1 Flash, GPT-5.6 Luna and GLM 5.3 Flash are **not
   distinguishable** from each other on either task: WMDP p ≥ 0.19,
   CTI-MCQ p ≥ 0.059.
2. **On CTI-RCM (CVE → CWE) the spread is narrow.**
   - DeepSeek beats GLM (p = 0.0063) and Solar (p = 0.0001).
   - DeepSeek vs Luna is nominal only: p = 0.013, which does not survive
     α = 0.0083.
   - All other RCM pairs are non-significant (p ≥ 0.059).
3. **Reasoning helps closed-book recall where there is headroom.** On
   WMDP-cyber, all 3 toggleable models gain, each p ≤ 0.0002:
   - Luna +9.9 pp
   - DeepSeek +4.8 pp
   - Solar +4.5 pp

   On CTI-MCQ, Luna (+4.7 pp) and Solar (+3.1 pp) gain, each p ≤ 0.0001.
   DeepSeek does not (p = 0.74, see below). On CTI-RCM no model gains (all
   p ≥ 0.033, none significant after correction).

   This is **not consistent with the legacy null** on CyberMetric, where
   reasoning moved no model (p ≥ 0.21). The likely explanation is
   CyberMetric's 94–95% ceiling: there was no headroom for reasoning to
   show up. This run does not test that directly, because the item sets
   differ.
4. **The reasoning condition changes the ranking.** With reasoning off,
   Luna is indistinguishable from Solar on WMDP (p = 0.34). With reasoning
   on, it is 6.7 pp ahead (p < 0.0001). A single-condition leaderboard for
   these models would depend on a setting the provider picks by default.
   GLM's "off" row has reasoning on (mandatory), so off-condition
   comparisons against GLM are not like-for-like.
5. **Run-to-run noise is about 1 pp.** GLM's two runs are both
   reasoning-on on the same pinned provider, which makes them a
   test-retest pair:
   - Accuracy moved by 0.8–1.0 pp (p ≥ 0.16 on all 3 tasks).
   - The same answer was extracted on 83.7–90.1% of items.

   Differences of about 1 pp between any two cells here are within noise.

#### Accuracy, reasoning on (primary between-model comparison)

Denominator: all items. Truncation and unparsed rows count as not correct.

| Model | WMDP-cyber (n=996) | CTI-MCQ (n=2,500) | CTI-RCM (n=1,000) |
|---|---|---|---|
| DeepSeek V4.1 Flash (StreamLake fp8) | **84.8%** | 79.6% | **76.3%** |
| GPT-5.6 Luna | 83.8% | **80.2%** | 74.0% |
| GLM 5.3 Flash | 83.3% | 78.7% | 73.9% |
| Solar Pro 4 | 77.1% | 76.0% | 72.1% |
| majority-label baseline | 26.8% (A) | 37.1% (C) | 22.9% (CWE-79) |

#### Accuracy, reasoning off

| Model | WMDP-cyber | CTI-MCQ | CTI-RCM |
|---|---|---|---|
| GLM 5.3 Flash\* | **82.5%** | 77.7% | 74.8% |
| DeepSeek V4.1 Flash | 80.0% | **79.3%** | **76.5%** |
| GPT-5.6 Luna | 73.9% | 75.5% | 74.1% |
| Solar Pro 4 | 72.6% | 72.9% | 70.1% |

\* Reasoning is mandatory for GLM, so this row is a second reasoning-on
run.

#### Pairwise McNemar, reasoning on

`**` means the test survives Bonferroni α = 0.0083 (6 pairs per task);
`*` means p < 0.05 without surviving it. b is the number of items only
the first model got right, and c the number only the second model got
right.

| Pair | WMDP-cyber b/c, p | CTI-MCQ b/c, p | CTI-RCM b/c, p |
|---|---|---|---|
| DeepSeek vs GLM | 64/49, 0.19 | 178/157, 0.27 | 48/24, **0.0063\*\*** |
| DeepSeek vs Luna | 57/47, 0.38 | 157/173, 0.41 | 51/28, 0.013\* |
| DeepSeek vs Solar | 112/35, **<0.0001\*\*** | 250/160, **<0.0001\*\*** | 77/35, **0.0001\*\*** |
| GLM vs Luna | 49/54, 0.69 | 163/200, 0.059 | 21/22, 1.00 |
| GLM vs Solar | 102/40, **<0.0001\*\*** | 253/184, **0.0011\*\*** | 54/36, 0.073 |
| Luna vs Solar | 99/32, **<0.0001\*\*** | 243/137, **<0.0001\*\*** | 55/36, 0.059 |

**Sensitivity check** (only items both models answered): one Bonferroni
call flips. DeepSeek vs Luna on CTI-RCM goes from p = 0.013 to
**p = 0.0038** (n = 991), because DeepSeek's 9 RCM truncations stop
counting against it. All other calls are unchanged.

The off-condition pairwise tables and their sensitivity checks are in the
`analyze.py` output. One call flips there too: GLM vs Luna on CTI-MCQ is
p = 0.0091 in the primary analysis and p < 0.0001 on both-answered items.
The difference is GLM's 116 truncations.

In both flips the truncated side loses significance in the primary
analysis. That is the pre-registered reading: a model that does not answer
within the budget does not get credit.

#### Reasoning off vs on, within model

Bonferroni α = 0.0056 (3 models × 3 tasks). b is the number of items
right only with reasoning off, and c the number right only with it on.

| Model | WMDP-cyber | CTI-MCQ | CTI-RCM |
|---|---|---|---|
| Solar Pro 4 | 72.6 → 77.1%, 48/93, **p = 0.0002** | 72.9 → 76.0%, 152/229, **p = 0.0001** | 70.1 → 72.1%, 30/50, p = 0.033 |
| GPT-5.6 Luna | 73.9 → 83.8%, 33/132, **p < 0.0001** | 75.5 → 80.2%, 92/210, **p < 0.0001** | 74.1 → 74.0%, 24/23, p = 1.00 |
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

Each cell is WMDP-cyber / CTI-MCQ / CTI-RCM.

- **CTI-MCQ provokes the most non-termination.** Its questions are about
  ATT&CK ID-level detail. The pilot trace of a model enumerating
  non-existent IDs came from this task.
- **Unparsed rows are mostly refusals.** They are almost all on WMDP-cyber,
  whose items are about offensive techniques. Examples: DeepSeek's "I'm
  sorry, but I can't help with that request."; GLM's "I will not provide
  a letter answer for this question."; Luna answering with a safer
  alternative instead of a letter. A few are invalid letters, such as
  Luna answering `F`.

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

## Axis 2 — Agentic task-solving (planned)

Not run yet under this design. Plan:

- **[Cybench](https://github.com/andyzorigin/cybench)** via
  `inspect_evals/cybench`: 39 tasks, Apache-2.0, OpenRouter-native. The
  tasks come from 2022–2024 professional CTFs, so this does not fix
  contamination either. It is chosen because published numbers exist for
  this model tier under a documented protocol. For example,
  [arXiv:2607.15263](https://arxiv.org/abs/2607.15263) reports GPT-5.6 Luna
  at 79.5% and DeepSeek v4 Flash at 86.4%, on 39 tasks × 3 epochs. This
  project's numbers can be anchored to theirs.
- **CTFTiny** (50 challenges from NYU CTF Bench) as a continuity anchor
  with the legacy run.

The legacy CTF results (NYU CTF Bench 200 + CTFTiny, 3,000+ agent jobs,
round-budget and reasoning-confound analyses) remain in
[`legacy/ctftiny/README.md`](legacy/ctftiny/README.md). They are not part
of this design.

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
| `legacy/` | the previous CyberMetric + NYU CTF Bench / CTFTiny study, archived as-is ([README](legacy/README.md)) |

## License

Apache-2.0 for this project's code, logs and write-ups (see
[`LICENSE`](LICENSE)). Third-party terms are in [`NOTICE`](NOTICE).
WMDP-cyber (MIT) and CTIBench (CC BY-NC-SA 4.0) are fetched at run time,
not redistributed. The per-item logs store model responses, answer keys
and prompt hashes, but not question text.
