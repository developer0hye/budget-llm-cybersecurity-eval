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
  `chat_template_kwargs.enable_thinking=false/true`. For Qwen the request
  also carries `reasoning_effort: "medium"` when on, matching OpenRouter's
  definition of `enabled: true`; the Qwen3.8 template only reads that field
  at the top level of the request. Gemma 4 has no effort control.
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
  prompts (`SEQS` in `queue.sh`). The first 1,944 `gemma-4-12b` reasoning-off
  rows ran at 8 server sequences and the rest at 32; at temperature 0 this
  can change outputs only through batch-dependent floating-point order.

## Results

**In progress.** Runs finish one at a time (fastest first: every model with
reasoning off, then reasoning on). Only complete runs (4,496 scored rows, no
transport errors) are committed. Every number below is printed by
[`tables.py`](tables.py) from `analysis_reasoning_{off,on}.json`, which
[`analyze_spark.py`](analyze_spark.py) recomputes from the per-item logs in
`results_reasoning_{off,on}/`; the full test output is in
`analysis_reasoning_{off,on}.txt`.

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

n = 996 / 2,500 / 1,000 per model; accuracy = correct / all items. GLM 5.3
Flash cannot turn reasoning off, so its row has reasoning on (as in the main
README). Every model present is one Bonferroni family: with 7 models that is
21 pairs per task, α = 0.0024. α shrinks as local models are added, so a
verdict near α can change until the last run is in.

McNemar, local model vs each other model (primary analysis, all items):

| Local model | Task | deepseek-v4.1-flash | glm-5.3-flash | gpt-5.6-luna | gpt-6-luna | solar-pro4 | gemma-4-26b-a4b | qwen3.8-27b |
|---|---|---|---|---|---|---|---|---|
| gemma-4-26b-a4b | WMDP-cyber | − 0.002 | − <0.001** | + 0.117 | + 0.106 | + 0.010 | — | + 0.760 |
| gemma-4-26b-a4b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − 0.005 | − 0.616 | — | + 0.457 |
| gemma-4-26b-a4b | CTI-RCM | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.009 | — | − 0.001** |
| qwen3.8-27b | WMDP-cyber | − <0.001** | − <0.001** | + 0.239 | + 0.227 | + 0.017 | − 0.760 | — |
| qwen3.8-27b | CTI-MCQ | − <0.001** | − <0.001** | − <0.001** | − <0.001** | − 0.198 | − 0.457 | — |
| qwen3.8-27b | CTI-RCM | − <0.001** | − <0.001** | − 0.003 | − 0.003 | + 0.516 | + 0.001** | — |

`+` / `−` = the local model got more / fewer of the discordant items right;
`**` = below α. Both-answered sensitivity results are in
`analysis_reasoning_off.txt`. Two verdicts change there:
DeepSeek V4.1 Flash vs Gemma 4 26B-A4B on WMDP-cyber goes from p = 0.0025 to
0.0010 (significant), and Qwen3.8-27B vs GPT-6 Luna on CTI-MCQ from 0.0004
to 0.0035 (not significant), so that gap partly comes from non-answers.

- **Gemma 4 26B-A4B and Qwen3.8-27B are not separable on WMDP-cyber or
  CTI-MCQ** (p = 0.76, 0.46). On CTI-RCM (CVE description → CWE ID)
  Qwen3.8-27B is ahead, 70.9% vs 67.3% (p = 0.0011).
- **WMDP-cyber**: both local models sit with the two GPT Luna models and
  Solar Pro 4 (all p ≥ 0.010 > α) and behind GLM 5.3 Flash. DeepSeek V4.1
  Flash is ahead of Qwen3.8-27B (p = 0.0007); against Gemma 4 26B-A4B it is
  just above α (p = 0.0025).
- **CTI-MCQ**: both local models are level with Solar Pro 4 and behind
  DeepSeek, GLM and GPT-5.6 Luna. Against GPT-6 Luna, Qwen3.8-27B is behind
  (p = 0.0004) and Gemma 4 26B-A4B is not separable (p = 0.005).
- **CTI-RCM**: Gemma 4 26B-A4B has the lowest score of the seven and is
  behind every model except Solar Pro 4 (p = 0.009). Qwen3.8-27B is behind
  DeepSeek and GLM; its gaps to the GPT Luna models (p = 0.003) no longer
  clear α with 7 models.

### Reasoning on

Not run yet.

### Wall-clock per run

| Model | Reasoning | Wall-clock | Server sequences | Client concurrency |
|---|---|---|---|---|
| qwen3.8-27b | off | 2.02 h | 32 | 64 |
| gemma-4-26b-a4b | off | 0.54 h | 32 | 64 |

Source: the `wall-clock` line `run_local.py` prints, collected in
[`runs.json`](runs.json).

## Reproducing

On a DGX Spark with Docker and the NVIDIA container toolkit, from the repo
root:

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
./knowledge/download_data.sh
# download the checkpoints listed in llm-serve (hf download <repo> --revision <hash>)
local-spark/llm-serve qwen27          # start one model on :8000
.venv/bin/python local-spark/run_local.py --models qwen3.8-27b --reasoning off \
    --concurrency 64 --out local-spark/results_reasoning_off
# or everything, one server at a time:
setsid nohup local-spark/queue.sh > queue.log 2>&1 < /dev/null &
python3 local-spark/analyze_spark.py on --json local-spark/analysis_reasoning_on.json --compare-off
```

The logged runs wrote to `knowledge/spark_reasoning_{off,on}/` on the
device and were copied here unchanged.
