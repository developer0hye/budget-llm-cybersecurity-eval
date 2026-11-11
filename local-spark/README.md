# Knowledge axis on five open-weight models served from one DGX Spark

The main study measures five budget models through OpenRouter. This adds the
case where prompts may not leave the building: open-weight models served by
vLLM on a single NVIDIA DGX Spark (GB10, 121 GiB unified memory, 273 GB/s,
aarch64), the class of box sold as an on-premises AI appliance. Same 4,496
items, same prompts, same extraction and scoring, both reasoning conditions.
Tracking issue: #5.

Only the knowledge axis is run. Cybench needs the k8s + gVisor + Cilium
sandbox from the main study, which runs on x86; the Spark is aarch64.

## Models and serving

| Short name | Model | Checkpoint | Image | Speculative decoding |
|---|---|---|---|---|
| `gemma-4-12b` | Gemma 4 12B (dense) | `RedHatAI/gemma-4-12B-it-NVFP4@8965ad1` (llm-compressor W4A4; card says preliminary) | `vllm/vllm-openai:v0.29.0` | none (the 12B assistant drafter's architecture is not registered in either image) |
| `gemma-4-26b-a4b` | Gemma 4 26B-A4B (MoE, 4B active) | `nvidia/Gemma-4-26B-A4B-NVFP4@a19cfe0` | `eugr/spark-vllm:nightly-20260704` | MTP drafter `google/gemma-4-26B-A4B-it-assistant`, 4 tokens |
| `gemma-4-31b` | Gemma 4 31B (dense) | `nvidia/Gemma-4-31B-IT-NVFP4@4135a98` | `vllm/vllm-openai:v0.29.0` | draft model `google/gemma-4-31B-it-assistant`, 4 tokens |
| `qwen3.8-27b` | Qwen3.8-27B (dense, 48 of 64 layers Gated DeltaNet) | `nvidia/Qwen3.8-27B-NVFP4@482ca0f` (NVFP4 MLP + FP8 attention) | `vllm/vllm-openai:v0.29.0` | built-in MTP head, 3 tokens |
| `qwen3.8-flash-next` | Qwen3.8-Flash-Next (MoE, 125B total, 6B active) | `nvidia/Qwen3.8-Flash-Next-FP4-Local@b9ce18a` | `eugr/spark-vllm-b12x` | MTP, 3 tokens |

Image digests, every vLLM flag and the snapshot hashes are in
[`llm-serve`](llm-serve). One model is served at a time. Speculative
decoding does not change greedy outputs in principle; it is on because it is
how these models would be deployed on this box.

## What is the same as the main study, and what is not

Same, by construction: [`run_local.py`](run_local.py) imports
`knowledge/run_knowledge.py` and replaces only the `models` module and
`call_model`. Templates, system prompts, the 996-item WMDP-cyber subset, MCQ
extraction v2, the RCM rule, outcome classes, the resume guard and
`summary.json` are upstream code. Temperature 0, `max_tokens=16000`, one
sample per item.

Different:

- **Reasoning toggle.** vLLM has no `reasoning: {enabled}` field. Off/on is
  `chat_template_kwargs.enable_thinking=false/true`; every reasoning-on row
  is checked for a non-empty trace.
- **Reasoning effort: Qwen at its maximum, not medium.** The OpenRouter runs
  used medium effort (OpenRouter's definition of `enabled: true`). The local
  Qwen3.8 runs use `reasoning_effort: "xhigh"`, the model's highest setting
  and its chat template's default, by the owner's choice: the question here
  is what each local model does at its best setting. The template reads the
  field only at the top level of the request; with `xhigh` it prepends
  "think carefully through the task, validate key assumptions, consider
  plausible alternatives, …" to the system prompt (verified: +42 prompt
  tokens vs `medium` on the same request). Each row logs the effort it ran
  with (`reasoning_effort`). Gemma 4 has no effort control.
- **Extra condition: model-card sampling** (`results_reasoning_on_card/`).
  Greedy decoding is the protocol, and both model cards recommend sampling
  for thinking (Qwen3.8: temperature 1.0, top_p 0.95, top_k 20, min_p 0,
  presence_penalty 0; Gemma 4: 1.0, 0.95, 64 — the values in each
  checkpoint's `generation_config.json`), warning that greedy thinking can
  loop. So every reasoning-on run is repeated with those values and
  `seed: 0` (logged per row as `sampling`). The OpenRouter models could not
  be re-run, so in that table they keep their greedy, medium-effort rows:
  read those cross comparisons as mixed-setting. The within-model
  greedy-vs-card test is like-for-like.
- **Local vs OpenRouter is not best setting vs best setting.** The local
  Qwen runs use the maximum effort and are also run with the card's
  sampling; the OpenRouter rows are medium effort with temperature 0 as
  requested (whether each provider applied temperature 0 to its reasoning
  model is not checked here). Higher effort or recommended sampling could
  move the OpenRouter scores either way: a longer trace can help, and it
  also hits the 16,000-token cap more often, as xhigh does for the local
  Qwen models. A re-run of the OpenRouter models at their own best settings
  (for example a fixed 300-item subset per task) would settle the ranking;
  it is not done here because OpenRouter is not available for this run.
- **Reasoning tokens.** vLLM does not report
  `completion_tokens_details.reasoning_tokens`. The wrapper sets it to
  `completion_tokens` minus the tokenized final answer (off by a few
  template tokens), and stores the trace length in characters as
  `reasoning_chars`. Engagement checks use this field.
- **Per-call timeout** 3600 s instead of 600 s. A 16k-token trace at
  ~20 tok/s per stream takes ~800 s on this box; a 600 s timeout would
  discard and retry it.
- **Weights.** All five are 4-bit (NVFP4) quantizations, four from
  NVIDIA's ModelOpt releases and one from Red Hat. No BF16 reference was
  run, so quantization error and model capability are not separable here.
- **Cost.** No per-call price. `usage.cost` is 0 in every row; wall-clock
  per run is reported instead, and the box cost is stated with the results.
- **Server concurrency.** `--max-num-seqs` was raised for these short
  prompts (`SEQS` in `queue1.sh` / `queue2.sh`). The first 1,944 `gemma-4-12b` reasoning-off
  rows ran at 8 server sequences and the rest at 32; at temperature 0 this
  can change outputs only through batch-dependent floating-point order.
- **Two boxes.** Runs are split across two identical DGX Sparks to finish
  sooner; `runs.json` records which box ran which run.

## Results

**In progress** (reasoning-on runs for Gemma 4 12B and Gemma 4 31B are still running, card sampling first, then greedy). Runs finish one at a time (fastest first: every model with
reasoning off, then reasoning on, greedy then card sampling). Only complete
runs (4,496 scored rows, no transport errors) are committed. Every number
below is printed by [`tables.py`](tables.py) from
`analysis_reasoning_{off,on,on_card}.json`, which
[`analyze_spark.py`](analyze_spark.py) recomputes from the per-item logs in
`results_reasoning_{off,on,on_card}/`; the full test output is in
`analysis_reasoning_*.txt`.

Hardware: one MSI EdgeXpert MS-C931 (DGX Spark class), bought 2026-11-09 for
KRW 11,000,000 (about $8,200). Calls cost nothing at the margin, so cost is
reported as wall-clock below.

### Headline so far

1. **With reasoning off, the best local models reach the OpenRouter field on
   two of three tasks.** Qwen3.8-Flash-Next and Gemma 4 31B both score 78.4%
   on WMDP-cyber, not separable from DeepSeek V4.1 Flash (p = 0.20, 0.22) and
   ahead of both GPT Luna models. On CTI-RCM, Qwen3.8-Flash-Next (75.0%) is
   level with DeepSeek, GLM and both GPT Luna models (p ≥ 0.17). On CTI-MCQ
   every local model is behind DeepSeek and GLM.
2. **Gemma 4 with greedy thinking loses points to loops, not to wrong
   answers.** Gemma 4 26B-A4B with reasoning on at temperature 0 hits the
   16,000-token cap on 659 of 4,496 items (24% of WMDP-cyber), and its
   WMDP-cyber score falls from 76.1% (off) to 63.0%. Of the items it does
   answer, 83.0% are right. With the model card's sampling the cap is hit 16
   times and the score is 78.8%, so the "reasoning hurts" result is an
   artifact of greedy decoding for this model. The OpenRouter models all
   gained from reasoning on WMDP-cyber (+4.5 to +9.9 pp).
3. **Neither Qwen3.8 model gains from greedy reasoning at xhigh, but card
   sampling does — most for Flash-Next.** Against reasoning off,
   Qwen3.8-Flash-Next moves −1.0 / −2.4 / +1.0 pp
   (WMDP-cyber / CTI-MCQ / CTI-RCM) and Qwen3.8-27B −1.4 / −1.5 / +1.0 pp;
   none of the six differences is significant, and 340 / 293 items hit the
   16,000-token cap. Neither greedy run collapses the way Gemma 4 26B-A4B's
   did. Model-card sampling lifts both over greedy: Flash-Next
   +3.1 / +5.5 / +0.2 pp (significant on the first two, p ≤ 0.0006) and the
   27B +3.6 / +1.8 / +1.2 pp (significant only on WMDP-cyber). With card
   sampling Qwen3.8-Flash-Next is the strongest local model: on CTI-RCM
   (76.2%) it is statistically level with the entire OpenRouter field and
   ahead of Solar Pro 4, on WMDP-cyber (80.5%) level with GPT-6 Luna, and on
   CTI-MCQ (77.6%) level with GLM and Solar Pro 4.

### Reasoning off

<!-- tables:off -->
| Model (reasoning off) | Where | WMDP-cyber | CTI-MCQ | CTI-RCM | Non-answers (trunc / unparsed) |
|---|---|---|---|---|---|
| deepseek-v4.1-flash | OpenRouter | 80.0% | 79.3% | 76.5% | 7 / 3 |
| glm-5.3-flash | OpenRouter | 82.8% | 78.0% | 74.8% | 144 / 3 |
| **qwen3.8-flash-next** | **Spark** | 78.4% | 74.5% | 75.0% | 5 / 2 |
| gpt-5.6-luna | OpenRouter | 73.9% | 75.5% | 74.1% | 0 / 7 |
| **gemma-4-31b** | **Spark** | 78.4% | 74.8% | 70.1% | 5 / 1 |
| gpt-6-luna | OpenRouter | 73.8% | 74.8% | 73.8% | 0 / 24 |
| **qwen3.8-27b** | **Spark** | 75.6% | 71.7% | 70.9% | 2 / 15 |
| **gemma-4-26b-a4b** | **Spark** | 76.1% | 72.4% | 67.3% | 10 / 0 |
| solar-pro4 | OpenRouter | 72.6% | 72.9% | 70.1% | 0 / 4 |
| **gemma-4-12b** | **Spark** | 71.8% | 69.3% | 55.9% | 15 / 9 |

n = 996 / 2,500 / 1,000 per model. Accuracy = correct / all items. 10 models, Bonferroni alpha = 0.05/45 = 0.0011 per task.

Local model vs each OpenRouter model, reasoning off: p (primary) and who is ahead; ** = below the Bonferroni alpha.

| Local model | Task | deepseek-v4.1-flash | glm-5.3-flash | gpt-5.6-luna | gpt-6-luna | solar-pro4 | gemma-4-12b | gemma-4-26b-a4b | gemma-4-31b | qwen3.8-27b | qwen3.8-flash-next |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-12b | WMDP-cyber | − <0.001** | − <0.001** | − 0.152 | − 0.179 | − 0.619 | — | − 0.001 | − <0.001** | − 0.007 | − <0.001** |
| gemma-4-12b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − <0.001** | — | − <0.001** | − <0.001** | − 0.008 | − <0.001** |
| gemma-4-12b | CTI-RCM | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − <0.001** | — | − <0.001** | − <0.001** | − <0.001** | − <0.001** |
| gemma-4-26b-a4b | WMDP-cyber | − 0.002 | − <0.001** | + 0.117 | + 0.106 | + 0.010 | + 0.001 | — | − 0.058 | + 0.760 | − 0.067 |
| gemma-4-26b-a4b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − 0.005 | − 0.616 | + <0.001** | — | − 0.003 | + 0.457 | − 0.014 |
| gemma-4-26b-a4b | CTI-RCM | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.009 | + <0.001** | — | − 0.001** | − 0.001** | − <0.001** |
| gemma-4-31b | WMDP-cyber | − 0.217 | − <0.001** | + <0.001** | + <0.001** | + <0.001** | + <0.001** | + 0.058 | — | + 0.028 | − 1.000 |
| gemma-4-31b | CTI-MCQ | − <0.001** | − <0.001** | − 0.415 | − 0.961 | + 0.023 | + <0.001** | + 0.003 | — | + <0.001** | + 0.805 |
| gemma-4-31b | CTI-RCM | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 1.000 | + <0.001** | + 0.001** | — | − 0.509 | − <0.001** |
| qwen3.8-27b | WMDP-cyber | − <0.001** | − <0.001** | + 0.239 | + 0.227 | + 0.017 | + 0.007 | − 0.760 | − 0.028 | — | − 0.023 |
| qwen3.8-27b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.198 | + 0.008 | − 0.457 | − <0.001** | — | − 0.001** |
| qwen3.8-27b | CTI-RCM | − <0.001** | − <0.001** | − 0.003 | − 0.003 | + 0.516 | + <0.001** | + 0.001** | + 0.509 | — | − <0.001** |
| qwen3.8-flash-next | WMDP-cyber | − 0.201 | − <0.001** | + 0.001** | + <0.001** | + <0.001** | + <0.001** | + 0.067 | + 1.000 | + 0.023 | — |
| qwen3.8-flash-next | CTI-MCQ | − <0.001** | − <0.001** | − 0.266 | − 0.739 | + 0.060 | + <0.001** | + 0.014 | − 0.805 | + 0.001** | — |
| qwen3.8-flash-next | CTI-RCM | − 0.167 | + 0.923 | + 0.444 | + 0.290 | + <0.001** | + <0.001** | + <0.001** | + <0.001** | + <0.001** | — |

`+` = the local model got more of the discordant items right, `−` = fewer.

Verdicts that change on both-answered items (reasoning off, alpha = 0.0011):
- WMDP-cyber, deepseek-v4.1-flash vs gemma-4-26b-a4b: all items p = 0.0025, both answered p = 0.0010 (n = 987)
- WMDP-cyber, gemma-4-31b vs gpt-5.6-luna: all items p = 0.0010, both answered p = 0.0023 (n = 987)
- WMDP-cyber, gemma-4-31b vs gpt-6-luna: all items p = 0.0008, both answered p = 0.0165 (n = 972)
- WMDP-cyber, gpt-5.6-luna vs qwen3.8-flash-next: all items p = 0.0011, both answered p = 0.0033 (n = 989)
- WMDP-cyber, gpt-6-luna vs qwen3.8-flash-next: all items p = 0.0006, both answered p = 0.0251 (n = 972)
- CTI-MCQ, gemma-4-12b vs gemma-4-26b-a4b: all items p = 0.0007, both answered p = 0.0012 (n = 2,482)
- CTI-MCQ, gemma-4-31b vs qwen3.8-27b: all items p = 0.0003, both answered p = 0.0019 (n = 2,482)
- CTI-MCQ, gpt-6-luna vs qwen3.8-27b: all items p = 0.0004, both answered p = 0.0035 (n = 2,483)
- CTI-MCQ, qwen3.8-27b vs qwen3.8-flash-next: all items p = 0.0010, both answered p = 0.0048 (n = 2,476)
- CTI-RCM, gemma-4-26b-a4b vs qwen3.8-27b: all items p = 0.0011, both answered p = 0.0019 (n = 998)
<!-- /tables:off -->

GLM 5.3 Flash cannot turn reasoning off, so its row has reasoning on (as in
the main README). Every model present is one Bonferroni family; with all ten
models that is 45 pairs per task, α = 0.0011.

- **Qwen3.8-Flash-Next and Gemma 4 31B are the strongest local models and
  are not separable from each other** on WMDP-cyber or CTI-MCQ (p = 1.00,
  0.81). Both are level with DeepSeek V4.1 Flash on WMDP-cyber
  (p = 0.20, 0.22), behind GLM 5.3 Flash (which runs with reasoning on), and
  ahead of both GPT Luna models on all items (p ≤ 0.0011; on both-answered
  items these gaps are not significant, so they rest partly on the GPT Luna
  models' non-answers). On CTI-RCM they split: Qwen3.8-Flash-Next 75.0% is
  level with DeepSeek, GLM and the GPT Luna models (p ≥ 0.17), Gemma 4 31B
  70.1% is behind all four and level with Solar Pro 4 (p = 1.00).
- **Gemma 4 26B-A4B and Qwen3.8-27B are not separable on WMDP-cyber or
  CTI-MCQ** (p = 0.76, 0.46) and sit with Solar Pro 4 and the GPT Luna models
  on WMDP-cyber. On CTI-RCM Qwen3.8-27B is ahead, 70.9% vs 67.3%
  (p = 0.0011, just under α; on both-answered items p = 0.0019).
- **Gemma 4 12B is the lowest of the ten on CTI-MCQ and CTI-RCM.** On
  CTI-RCM (55.9%) it is behind every other model (all p < 0.001); it
  answers 99.7% of RCM items and gets 56.1% of those right, so the gap is
  wrong CWE IDs, not non-answers.

### Reasoning on

Two conditions for the local models: greedy decoding as in the protocol
(`results_reasoning_on/`), and the model card's sampling
(`results_reasoning_on_card/`). The OpenRouter rows are the same greedy,
medium-effort runs in both tables, because they could not be re-run; in the
card-sampling table, local-vs-OpenRouter tests compare different settings.

<!-- tables:on -->
| Model (reasoning on) | Where | WMDP-cyber | CTI-MCQ | CTI-RCM | Non-answers (trunc / unparsed) |
|---|---|---|---|---|---|
| deepseek-v4.1-flash | OpenRouter | 84.9% | 79.6% | 76.3% | 102 / 0 |
| gpt-5.6-luna | OpenRouter | 83.8% | 80.2% | 74.0% | 0 / 4 |
| gpt-6-luna | OpenRouter | 81.6% | 81.0% | 75.1% | 0 / 38 |
| glm-5.3-flash | OpenRouter | 83.3% | 78.9% | 73.9% | 128 / 5 |
| **qwen3.8-flash-next** | **Spark** | 77.4% | 72.1% | 76.0% | 340 / 0 |
| solar-pro4 | OpenRouter | 77.1% | 76.0% | 72.1% | 47 / 2 |
| **qwen3.8-27b** | **Spark** | 74.2% | 70.2% | 71.9% | 293 / 1 |
| **gemma-4-26b-a4b** | **Spark** | 63.0% | 63.8% | 70.0% | 659 / 0 |

n = 996 / 2,500 / 1,000 per model. Accuracy = correct / all items. 8 models, Bonferroni alpha = 0.05/28 = 0.0018 per task.

Local model vs each OpenRouter model, reasoning on: p (primary) and who is ahead; ** = below the Bonferroni alpha.

| Local model | Task | deepseek-v4.1-flash | glm-5.3-flash | gpt-5.6-luna | gpt-6-luna | solar-pro4 | gemma-4-26b-a4b | qwen3.8-27b | qwen3.8-flash-next |
|---|---|---|---|---|---|---|---|---|---|
| gemma-4-26b-a4b | WMDP-cyber | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − <0.001** | — | − <0.001** | − <0.001** |
| gemma-4-26b-a4b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − <0.001** | — | − <0.001** | − <0.001** |
| gemma-4-26b-a4b | CTI-RCM | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.033 | — | − 0.064 | − <0.001** |
| qwen3.8-27b | WMDP-cyber | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.018 | + <0.001** | — | − 0.007 |
| qwen3.8-27b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − <0.001** | + <0.001** | — | − 0.029 |
| qwen3.8-27b | CTI-RCM | − <0.001** | − 0.024 | − 0.014 | − <0.001** | − 0.916 | + 0.064 | — | − <0.001** |
| qwen3.8-flash-next | WMDP-cyber | − <0.001** | − <0.001** | − <0.001** | − 0.001** | + 0.865 | + <0.001** | + 0.007 | — |
| qwen3.8-flash-next | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − <0.001** | + <0.001** | + 0.029 | — |
| qwen3.8-flash-next | CTI-RCM | − 0.815 | + 0.006 | + 0.009 | + 0.281 | + <0.001** | + <0.001** | + <0.001** | — |

`+` = the local model got more of the discordant items right, `−` = fewer.

Verdicts that change on both-answered items (reasoning on, alpha = 0.0018):
- WMDP-cyber, gemma-4-26b-a4b vs gpt-5.6-luna: all items p = 0.0000, both answered p = 0.0141 (n = 754)
- WMDP-cyber, gemma-4-26b-a4b vs qwen3.8-27b: all items p = 0.0000, both answered p = 0.0535 (n = 729)
- WMDP-cyber, gemma-4-26b-a4b vs qwen3.8-flash-next: all items p = 0.0000, both answered p = 1.0000 (n = 735)
- WMDP-cyber, gemma-4-26b-a4b vs solar-pro4: all items p = 0.0000, both answered p = 0.6445 (n = 757)
- WMDP-cyber, gpt-5.6-luna vs qwen3.8-flash-next: all items p = 0.0000, both answered p = 0.0067 (n = 938)
- WMDP-cyber, gpt-6-luna vs qwen3.8-flash-next: all items p = 0.0013, both answered p = 0.0023 (n = 905)
- CTI-MCQ, gemma-4-26b-a4b vs qwen3.8-27b: all items p = 0.0000, both answered p = 0.3346 (n = 1,923)
- CTI-MCQ, gemma-4-26b-a4b vs qwen3.8-flash-next: all items p = 0.0000, both answered p = 0.0106 (n = 1,885)
- CTI-MCQ, gemma-4-26b-a4b vs solar-pro4: all items p = 0.0000, both answered p = 0.0206 (n = 2,076)
- CTI-MCQ, gpt-5.6-luna vs qwen3.8-flash-next: all items p = 0.0000, both answered p = 0.1194 (n = 2,219)
- CTI-MCQ, gpt-6-luna vs qwen3.8-flash-next: all items p = 0.0000, both answered p = 0.0029 (n = 2,219)
- CTI-MCQ, qwen3.8-27b vs qwen3.8-flash-next: all items p = 0.0292, both answered p = 0.0004 (n = 2,059)
- CTI-MCQ, qwen3.8-27b vs solar-pro4: all items p = 0.0000, both answered p = 0.0167 (n = 2,237)
- CTI-MCQ, qwen3.8-flash-next vs solar-pro4: all items p = 0.0000, both answered p = 0.1115 (n = 2,196)
<!-- /tables:on -->

<!-- tables:on_card -->
| Model (reasoning on_card) | Where | WMDP-cyber | CTI-MCQ | CTI-RCM | Non-answers (trunc / unparsed) |
|---|---|---|---|---|---|
| deepseek-v4.1-flash | OpenRouter | 84.9% | 79.6% | 76.3% | 102 / 0 |
| gpt-5.6-luna | OpenRouter | 83.8% | 80.2% | 74.0% | 0 / 4 |
| gpt-6-luna | OpenRouter | 81.6% | 81.0% | 75.1% | 0 / 38 |
| glm-5.3-flash | OpenRouter | 83.3% | 78.9% | 73.9% | 128 / 5 |
| **qwen3.8-flash-next** | **Spark** | 80.5% | 77.6% | 76.2% | 54 / 0 |
| solar-pro4 | OpenRouter | 77.1% | 76.0% | 72.1% | 47 / 2 |
| **qwen3.8-27b** | **Spark** | 77.8% | 72.0% | 73.1% | 56 / 2 |
| **gemma-4-26b-a4b** | **Spark** | 78.8% | 73.9% | 69.9% | 16 / 0 |

n = 996 / 2,500 / 1,000 per model. Accuracy = correct / all items. 8 models, Bonferroni alpha = 0.05/28 = 0.0018 per task.

Local model vs each OpenRouter model, reasoning on_card: p (primary) and who is ahead; ** = below the Bonferroni alpha.

| Local model | Task | deepseek-v4.1-flash | glm-5.3-flash | gpt-5.6-luna | gpt-6-luna | solar-pro4 | gemma-4-26b-a4b | qwen3.8-27b | qwen3.8-flash-next |
|---|---|---|---|---|---|---|---|---|---|
| gemma-4-26b-a4b | WMDP-cyber | − <0.001** | − <0.001** | − <0.001** | − 0.035 | + 0.178 | — | + 0.447 | − 0.159 |
| gemma-4-26b-a4b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.013 | — | + 0.033 | − <0.001** |
| gemma-4-26b-a4b | CTI-RCM | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.033 | — | − 0.001** | − <0.001** |
| qwen3.8-27b | WMDP-cyber | − <0.001** | − <0.001** | − <0.001** | − 0.004 | + 0.621 | − 0.447 | — | − 0.014 |
| qwen3.8-27b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.033 | — | − <0.001** |
| qwen3.8-27b | CTI-RCM | − 0.001** | − 0.416 | − 0.321 | − 0.021 | + 0.326 | + 0.001** | — | − <0.001** |
| qwen3.8-flash-next | WMDP-cyber | − <0.001** | − 0.009 | − 0.002 | − 0.396 | + 0.004 | + 0.159 | + 0.014 | — |
| qwen3.8-flash-next | CTI-MCQ | − 0.014 | − 0.095 | − <0.001** | − <0.001** | + 0.051 | + <0.001** | + <0.001** | — |
| qwen3.8-flash-next | CTI-RCM | − 1.000 | + 0.004 | + 0.004 | + 0.161 | + <0.001** | + <0.001** | + <0.001** | — |

`+` = the local model got more of the discordant items right, `−` = fewer.

Verdicts that change on both-answered items (reasoning on_card, alpha = 0.0018):
- WMDP-cyber, gemma-4-26b-a4b vs gpt-6-luna: all items p = 0.0347, both answered p = 0.0000 (n = 948)
- WMDP-cyber, gpt-6-luna vs qwen3.8-27b: all items p = 0.0039, both answered p = 0.0000 (n = 941)
- WMDP-cyber, qwen3.8-27b vs qwen3.8-flash-next: all items p = 0.0141, both answered p = 0.0016 (n = 965)
- WMDP-cyber, qwen3.8-flash-next vs solar-pro4: all items p = 0.0039, both answered p = 0.0003 (n = 969)
- CTI-MCQ, deepseek-v4.1-flash vs qwen3.8-flash-next: all items p = 0.0136, both answered p = 0.0001 (n = 2,396)
- CTI-MCQ, gemma-4-26b-a4b vs solar-pro4: all items p = 0.0134, both answered p = 0.0004 (n = 2,465)
- CTI-MCQ, glm-5.3-flash vs qwen3.8-flash-next: all items p = 0.0947, both answered p = 0.0001 (n = 2,371)
- CTI-MCQ, gpt-5.6-luna vs qwen3.8-flash-next: all items p = 0.0008, both answered p = 0.0066 (n = 2,470)
- CTI-RCM, gemma-4-26b-a4b vs qwen3.8-27b: all items p = 0.0013, both answered p = 0.0023 (n = 996)
<!-- /tables:on_card -->

<!-- tables:within -->
Reasoning off vs on (greedy), local models

| Model | Task | off | on (greedy) | b / c | p | Truncated (on (greedy)) |
|---|---|---|---|---|---|---|
| gemma-4-26b-a4b | WMDP-cyber | 76.1% | 63.0% | 169 / 39 | <0.001 | 239 |
| gemma-4-26b-a4b | CTI-MCQ | 72.4% | 63.8% | 329 / 114 | <0.001 | 403 |
| gemma-4-26b-a4b | CTI-RCM | 67.3% | 70.0% | 24 / 51 | 0.002 | 17 |
| qwen3.8-27b | WMDP-cyber | 75.6% | 74.2% | 85 / 71 | 0.298 | 51 |
| qwen3.8-27b | CTI-MCQ | 71.7% | 70.2% | 238 / 199 | 0.069 | 232 |
| qwen3.8-27b | CTI-RCM | 70.9% | 71.9% | 28 / 38 | 0.268 | 10 |
| qwen3.8-flash-next | WMDP-cyber | 78.4% | 77.4% | 86 / 76 | 0.480 | 54 |
| qwen3.8-flash-next | CTI-MCQ | 74.5% | 72.1% | 240 / 180 | 0.004 | 281 |
| qwen3.8-flash-next | CTI-RCM | 75.0% | 76.0% | 38 / 48 | 0.332 | 5 |

b = right only under off, c = right only under on (greedy); n = all items of the task.

Greedy vs model-card sampling, reasoning on

| Model | Task | greedy | card sampling | b / c | p | Truncated (card sampling) |
|---|---|---|---|---|---|---|
| gemma-4-26b-a4b | WMDP-cyber | 63.0% | 78.8% | 21 / 178 | <0.001 | 11 |
| gemma-4-26b-a4b | CTI-MCQ | 63.8% | 73.9% | 78 / 330 | <0.001 | 2 |
| gemma-4-26b-a4b | CTI-RCM | 70.0% | 69.9% | 26 / 25 | 1.000 | 3 |
| qwen3.8-27b | WMDP-cyber | 74.2% | 77.8% | 30 / 66 | <0.001 | 16 |
| qwen3.8-27b | CTI-MCQ | 70.2% | 72.0% | 179 / 224 | 0.028 | 39 |
| qwen3.8-27b | CTI-RCM | 71.9% | 73.1% | 20 / 32 | 0.126 | 1 |
| qwen3.8-flash-next | WMDP-cyber | 77.4% | 80.5% | 24 / 55 | <0.001 | 24 |
| qwen3.8-flash-next | CTI-MCQ | 72.1% | 77.6% | 107 / 244 | <0.001 | 30 |
| qwen3.8-flash-next | CTI-RCM | 76.0% | 76.2% | 15 / 17 | 0.860 | 0 |

b = right only under greedy, c = right only under card sampling; n = all items of the task.

Reasoning off vs on (card sampling), local models

| Model | Task | off | on (card) | b / c | p | Truncated (on (card)) |
|---|---|---|---|---|---|---|
| gemma-4-26b-a4b | WMDP-cyber | 76.1% | 78.8% | 41 / 68 | 0.012 | 11 |
| gemma-4-26b-a4b | CTI-MCQ | 72.4% | 73.9% | 121 / 158 | 0.031 | 2 |
| gemma-4-26b-a4b | CTI-RCM | 67.3% | 69.9% | 27 / 53 | 0.005 | 3 |
| qwen3.8-27b | WMDP-cyber | 75.6% | 77.8% | 73 / 95 | 0.105 | 16 |
| qwen3.8-27b | CTI-MCQ | 71.7% | 72.0% | 220 / 226 | 0.813 | 39 |
| qwen3.8-27b | CTI-RCM | 70.9% | 73.1% | 31 / 53 | 0.021 | 1 |
| qwen3.8-flash-next | WMDP-cyber | 78.4% | 80.5% | 63 / 84 | 0.099 | 24 |
| qwen3.8-flash-next | CTI-MCQ | 74.5% | 77.6% | 152 / 229 | <0.001 | 30 |
| qwen3.8-flash-next | CTI-RCM | 75.0% | 76.2% | 38 / 50 | 0.241 | 0 |

b = right only under off, c = right only under on (card); n = all items of the task.
<!-- /tables:within -->

The within-model tests are paired on all items of a task (n = 996 / 2,500 /
1,000). The off-vs-on family follows the main README (every toggleable
model present × 3 tasks, Bonferroni); the greedy-vs-card family is the
local models present × 3 tasks.

- **Gemma 4 26B-A4B, greedy**: 239 WMDP-cyber, 403 CTI-MCQ and 17 CTI-RCM
  items end at the 16,000-token cap. The traces repeat; truncated items are
  non-answers by the protocol. Accuracy over answered items is 83.0% /
  76.1% (WMDP-cyber / CTI-MCQ), so the drop from reasoning off
  (76.1% → 63.0%, 72.4% → 63.8%) is the cap, not worse answers.
- **Gemma 4 26B-A4B, card sampling**: 16 truncations in total. Against
  greedy: WMDP-cyber +15.8 pp (b/c = 21/178) and CTI-MCQ +10.1 pp (78/330),
  both p < 0.001; CTI-RCM unchanged (p = 1.00). Against reasoning off it is
  higher on all three tasks (+2.7, +1.5, +2.6 pp), but none of the three
  differences clears α.
- Against the OpenRouter models' reasoning-on rows (a mixed-setting
  comparison), Gemma 4 26B-A4B with card sampling is level with Solar Pro 4
  on all three tasks and with GPT-6 Luna on WMDP-cyber (p = 0.035), and
  behind the others.
- **Qwen3.8-Flash-Next, greedy, `reasoning_effort` xhigh**: no task changes
  significantly against reasoning off. WMDP-cyber −1.0 pp (p = 0.48),
  CTI-MCQ −2.4 pp (p = 0.0039, above α = 0.0024), CTI-RCM +1.0 pp
  (p = 0.33). 340 items end at the 16,000-token cap (54 WMDP-cyber, 281
  CTI-MCQ, 5 CTI-RCM). The median completion is about 390 tokens on
  WMDP-cyber and CTI-MCQ, so the cap is hit by a tail of items, not by
  typical ones. Accuracy over answered items is 81.8% / 81.3% / 76.4%;
  169 of the 340 truncated items were right with reasoning off. The
  reasoning text is not stored, so whether these traces repeat (as Gemma
  4 26B-A4B's do) is not checked.
- Against the OpenRouter models' reasoning-on rows, Qwen3.8-Flash-Next is
  level with DeepSeek, GLM and both GPT Luna models on CTI-RCM
  (p ≥ 0.006) and ahead of Solar Pro 4 (p < 0.001). On WMDP-cyber it is
  level with Solar Pro 4 (p = 0.87) and behind the other four; on CTI-MCQ
  it is behind all five. Several of those WMDP-cyber and CTI-MCQ gaps are
  not significant on both-answered items (list above), so they rest partly
  on the truncations.
- **Qwen3.8-Flash-Next, card sampling**: 54 items end at the 16,000-token cap
  (24 WMDP-cyber, 30 CTI-MCQ, 0 CTI-RCM). Against greedy it is
  +3.1 / +5.5 / +0.2 pp (WMDP-cyber / CTI-MCQ / CTI-RCM): WMDP-cyber
  (77.4% → 80.5%, b/c = 24/55, p = 0.0006) and CTI-MCQ (72.1% → 77.6%,
  107/244, p < 0.001) clear α, CTI-RCM is unchanged (p = 0.86). This is the
  largest card-vs-greedy gain of the three local models run so far and makes
  Flash-Next the strongest local model on all three tasks.
- Against the OpenRouter models' on_card rows (a mixed-setting comparison,
  see Deviations): on CTI-RCM it is level with the whole field
  (p ≥ 0.0038, none below α = 0.0018) and ahead of Solar Pro 4 (p < 0.001);
  on WMDP-cyber level with GPT-6 Luna (p = 0.40) and not separable from GLM
  or GPT-5.6 Luna after correction (p = 0.009, 0.003), behind DeepSeek
  (p = 0.0001); on CTI-MCQ level with DeepSeek, GLM and Solar Pro 4, behind
  GPT-5.6 and GPT-6 Luna (p < 0.001).
- **Qwen3.8-27B, greedy, `reasoning_effort` xhigh**: no task changes
  significantly against reasoning off. WMDP-cyber −1.4 pp (p = 0.30),
  CTI-MCQ −1.5 pp (p = 0.069), CTI-RCM +1.0 pp (p = 0.27). 293 items end at
  the 16,000-token cap (51 WMDP-cyber, 232 CTI-MCQ, 10 CTI-RCM); median
  completions are 555 / 672 / 259 tokens. Accuracy over answered items is
  78.3% / 77.3% / 72.6%; 135 of the 293 truncated items were right with
  reasoning off.
- **Two Qwen3.8-27B items needed a third pass.** CTI-MCQ items 1330 and
  2174 failed on every attempt of the first two passes (6 retries each;
  the error text is not kept). Re-sent by hand, item 1330 returned empty
  content with finish_reason "stop" twice: the reasoning counts
  "T2083? T2084? …" until the model stops without writing an answer.
  Item 2174 returned an answer. A third pass of `run_local.py` then scored
  both (1330 right, 2174 wrong), so no row was written by hand.
- **Greedy decoding is not reproducible on this server.** The two re-sends
  of item 1330 used 12,790 and 7,834 completion tokens, and item 2174
  answered A by hand and C in the third pass, all at temperature 0. Batch
  composition and MTP speculative decoding change the arithmetic between
  calls, so a re-run can move single items; the run-level accuracies are
  what the tests above compare.
- Qwen3.8-27B against Qwen3.8-Flash-Next (both greedy, xhigh): behind on
  CTI-RCM (p < 0.001), not separable on WMDP-cyber or CTI-MCQ (p = 0.0067,
  0.029). Against the OpenRouter models' reasoning-on rows it is behind
  DeepSeek, GLM and both GPT Luna models on WMDP-cyber and CTI-MCQ
  (p < 0.001), level with Solar Pro 4 on WMDP-cyber and CTI-RCM
  (p = 0.018, 0.92) and behind it on CTI-MCQ (p < 0.001). On CTI-RCM it is
  level with GLM and GPT-5.6 Luna (p = 0.025, 0.014) and behind DeepSeek
  and GPT-6 Luna.
- **Qwen3.8-27B, card sampling**: 56 items end at the 16,000-token cap
  (16 WMDP-cyber, 39 CTI-MCQ, 1 CTI-RCM), down from greedy's 293. Against
  greedy it is +3.6 / +1.8 / +1.2 pp (WMDP-cyber / CTI-MCQ / CTI-RCM),
  significant only on WMDP-cyber (74.2% → 77.8%, b/c = 30/66, p < 0.001);
  the greedy run did not collapse the way Gemma 4 26B-A4B's did, so the gain
  is smaller. Against reasoning off (card) no task clears α: WMDP-cyber
  +2.2 pp (p = 0.105), CTI-MCQ +0.3 pp (p = 0.81), CTI-RCM +2.2 pp
  (p = 0.021).
- Qwen3.8-27B against Gemma 4 26B-A4B (both card sampling): not separable on
  WMDP-cyber (p = 0.45), behind on CTI-MCQ (p = 0.033) and ahead on CTI-RCM
  (p = 0.0013). Against the OpenRouter models' on_card rows it is level with
  Solar Pro 4 on WMDP-cyber (p = 0.62) and CTI-RCM (p = 0.33) and behind the
  four stronger models; this is a mixed-setting comparison (see Deviations).

### Wall-clock per run

<!-- tables:runs -->
| Model | Reasoning | Box | Wall-clock | Server sequences | Client concurrency |
|---|---|---|---|---|---|
| qwen3.8-27b | off | spark-1 | 2.02 h | 32 | 64 |
| gemma-4-26b-a4b | off | spark-1 | 0.54 h | 32 | 64 |
| gemma-4-12b | off | spark-1 then spark-2 | 1.32 h | 8 (first 1,944 rows) / 32 | 16 / 64 |
| qwen3.8-flash-next | off | spark-1 | 3.27 h | 16 | 64 |
| gemma-4-31b | off | spark-2 | 0.55 h | 128 | 192 |
| gemma-4-26b-a4b | on (greedy) | spark-2 | 4.00 h | 32 / 64 / 128 / 256 / 128 | 64-384 |
| gemma-4-26b-a4b | on (card sampling) | spark-2 | 1.85 h | 128 | 192 |
| qwen3.8-flash-next | on (greedy) | spark-1 | 12.43 h | 32 | 192 |
| qwen3.8-27b | on (greedy) | spark-2 | 11.66 h | 128 | 192 |
| qwen3.8-27b | on (card sampling) | spark-2 | 13.79 h | 128 | 192 |
| qwen3.8-flash-next | on (card sampling) | spark-1 | 23.06 h | 32 | 192 |
<!-- /tables:runs -->

From 2026-11-09 21:45 the runs are split across two identical boxes
(spark-1, spark-2: same MSI EdgeXpert model, OTA 7.6.0, driver 580.178.04,
image digests, checkpoint revisions and `llm-serve` flags). The
`gemma-4-12b` reasoning-off run was stopped by hand on spark-1 after 1,944
rows (to free the server) and resumed on spark-2; the 1,944 rows are
byte-identical in both copies. The `gemma-4-26b-a4b` greedy reasoning-on run
was restarted four times while server concurrency was being tuned (32 → 64
→ 128 → 256 → 128; generation throughput 908, 1,267, 1,657 and 1,425 tok/s
over 8-minute windows), so its wall-clock overstates the steady-state time.
Sources: the `wall-clock` line `run_local.py` prints, collected in
[`runs.json`](runs.json).

## Reproducing

On a DGX Spark with Docker and the NVIDIA container toolkit, from the repo
root:

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
./knowledge/download_data.sh
# download the checkpoints listed in llm-serve (hf download <repo> --revision <hash>)
local-spark/llm-serve qwen27          # start one model on :8000 (SEQS=32 for these short prompts)
.venv/bin/python local-spark/run_local.py --models qwen3.8-27b --reasoning on \
    --concurrency 64 --out local-spark/work_reasoning_on              # greedy, Qwen effort xhigh
BCSE_SAMPLING=card .venv/bin/python local-spark/run_local.py --models qwen3.8-27b --reasoning on \
    --concurrency 64 --out local-spark/work_reasoning_on_card         # model-card sampling
# the two-box split as run (queue2.sh on the second box):
setsid nohup local-spark/queue1.sh > queue1.log 2>&1 < /dev/null &
local-spark/publish.sh                # copy complete runs to results_reasoning_*/ and re-analyse
python3 local-spark/tables.py         # every table in this README
```

`BCSE_QWEN_EFFORT` overrides the Qwen effort (default `xhigh`). The logged
runs wrote to `knowledge/spark_reasoning_{off,on,on_card}/` on the devices
and were copied here unchanged; the queue scripts here are the ones that ran,
with paths pointed at `local-spark/`.
