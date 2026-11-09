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

**In progress.** Runs finish one at a time (fastest first: every model with
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

### Reasoning off

| Model (reasoning off) | Where | WMDP-cyber | CTI-MCQ | CTI-RCM | Non-answers (trunc / unparsed) |
|---|---|---|---|---|---|
| deepseek-v4.1-flash | OpenRouter | 80.0% | 79.3% | 76.5% | 7 / 3 |
| glm-5.3-flash | OpenRouter | 82.8% | 78.0% | 74.8% | 144 / 3 |
| gpt-5.6-luna | OpenRouter | 73.9% | 75.5% | 74.1% | 0 / 7 |
| gpt-6-luna | OpenRouter | 73.8% | 74.8% | 73.8% | 0 / 24 |
| **qwen3.8-27b** | **Spark** | 75.6% | 71.7% | 70.9% | 2 / 15 |
| **gemma-4-26b-a4b** | **Spark** | 76.1% | 72.4% | 67.3% | 10 / 0 |
| solar-pro4 | OpenRouter | 72.6% | 72.9% | 70.1% | 0 / 4 |
| **gemma-4-12b** | **Spark** | 71.8% | 69.3% | 55.9% | 15 / 9 |

n = 996 / 2,500 / 1,000 per model; accuracy = correct / all items. GLM 5.3
Flash cannot turn reasoning off, so its row has reasoning on (as in the main
README). Every model present is one Bonferroni family: with 8 models that is
28 pairs per task, α = 0.0018. α shrinks as local models are added, so a
verdict near α can change until the last run is in.

McNemar, local model vs each other model (primary analysis, all items):

| Local model | Task | deepseek-v4.1-flash | glm-5.3-flash | gpt-5.6-luna | gpt-6-luna | solar-pro4 | gemma-4-12b | gemma-4-26b-a4b | qwen3.8-27b |
|---|---|---|---|---|---|---|---|---|---|
| gemma-4-12b | WMDP-cyber | − <0.001** | − <0.001** | − 0.152 | − 0.179 | − 0.619 | — | − 0.001** | − 0.007 |
| gemma-4-12b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − <0.001** | — | − <0.001** | − 0.008 |
| gemma-4-12b | CTI-RCM | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − <0.001** | — | − <0.001** | − <0.001** |
| gemma-4-26b-a4b | WMDP-cyber | − 0.002 | − <0.001** | + 0.117 | + 0.106 | + 0.010 | + 0.001** | — | + 0.760 |
| gemma-4-26b-a4b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − 0.005 | − 0.616 | + <0.001** | — | + 0.457 |
| gemma-4-26b-a4b | CTI-RCM | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.009 | + <0.001** | — | − 0.001** |
| qwen3.8-27b | WMDP-cyber | − <0.001** | − <0.001** | + 0.239 | + 0.227 | + 0.017 | + 0.007 | − 0.760 | — |
| qwen3.8-27b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.198 | + 0.008 | − 0.457 | — |
| qwen3.8-27b | CTI-RCM | − <0.001** | − <0.001** | − 0.003 | − 0.003 | + 0.516 | + <0.001** | + 0.001** | — |

`+` / `−` = the row model got more / fewer of the discordant items right;
`**` = below α. Verdicts that change when only items both models answered
are tested (full output in `analysis_reasoning_off.txt`):

- WMDP-cyber, DeepSeek V4.1 Flash vs Gemma 4 26B-A4B: p = 0.0025 → 0.0010 (becomes significant)
- WMDP-cyber, Gemma 4 12B vs Gemma 4 26B-A4B: p = 0.0013 → 0.0039 (no longer significant)
- CTI-MCQ, GPT-6 Luna vs Qwen3.8-27B: p = 0.0004 → 0.0035 (no longer significant)
- CTI-RCM, Gemma 4 26B-A4B vs Qwen3.8-27B: p = 0.0011 → 0.0019 (no longer significant, just above α)

What the off condition shows so far:

- **WMDP-cyber**: all three local models sit with the two GPT Luna models
  and Solar Pro 4 (every p ≥ 0.010 > α) and behind GLM 5.3 Flash and
  DeepSeek V4.1 Flash (DeepSeek vs Gemma 4 26B-A4B: p = 0.0025, significant
  only on both-answered items). Gemma 4 26B-A4B is ahead of Gemma 4 12B
  (p = 0.0013).
- **CTI-MCQ**: Gemma 4 26B-A4B and Qwen3.8-27B are level with each other and
  with Solar Pro 4, and behind DeepSeek, GLM and GPT-5.6 Luna. Gemma 4 12B
  is the lowest of the eight (69.3%) and behind every model except
  Qwen3.8-27B (p = 0.008).
- **CTI-RCM** (CVE description → CWE ID) separates the local models most:
  Qwen3.8-27B 70.9% (level with Solar Pro 4, p = 0.52) > Gemma 4 26B-A4B
  67.3% > Gemma 4 12B 55.9%, which is behind every other model (all
  p < 0.001). Gemma 4 12B answers 99.7% of RCM items and gets 56.1% of
  those right, so the gap is wrong CWE IDs, not non-answers.

### Reasoning on

Not run yet.

### Wall-clock per run

| Model | Reasoning | Box | Wall-clock | Server sequences | Client concurrency |
|---|---|---|---|---|---|
| qwen3.8-27b | off | spark-1 | 2.02 h | 32 | 64 |
| gemma-4-26b-a4b | off | spark-1 | 0.54 h | 32 | 64 |
| gemma-4-12b | off | spark-1 then spark-2 | 1.32 h | 8 (first 1,944 rows) / 32 | 16 / 64 |

From 2026-11-09 21:45 the runs are split across two identical boxes
(spark-1, spark-2: same MSI EdgeXpert model, OTA 7.6.0, driver 580.178.04,
image digests, checkpoint revisions and `llm-serve` flags). The
`gemma-4-12b` reasoning-off run was stopped by hand on spark-1 after 1,944
rows (to free the server) and resumed on spark-2; the 1,944 rows are
byte-identical in both copies. Sources: the `wall-clock` line
`run_local.py` prints, collected in [`runs.json`](runs.json); the
spark-1 segment of that run is approximate (about 2,940 s, from its last
progress line).

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
