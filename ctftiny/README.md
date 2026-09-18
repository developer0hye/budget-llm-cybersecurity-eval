# CTF-solving agent evaluation (phase 2)

Companion project to the [CyberMetric budget-model comparison](../README.md) in
this repo. CyberMetric measures pure cybersecurity *knowledge* (multiple-choice
questions); this directory sets up a pipeline to measure practical CTF-*solving*
skill for the same budget-tier models, using two existing open-source projects
from NYU's LLM-CTF group rather than building an agent harness from scratch.

**Status: all 5 models run on a 12-challenge sample.** See
[Results](#results-baseline-agent-run-2026-09-18) below — and read the
statistical-power caveat before drawing any conclusion from the ranking.

## What's here

- [`nyuctf_agents/`](nyuctf_agents/) — vendored, modified copy of
  [NYU-LLM-CTF/nyuctf_agents](https://github.com/NYU-LLM-CTF/nyuctf_agents)
  (MIT license). Runs an LLM agent against real CTF challenges inside a Docker
  container (radare2, sqlmap, nikto, apktool, jadx, Ghidra, etc.) and logs the
  full tool-call trajectory.
- [`CTFJudge/`](CTFJudge/) — vendored, modified copy of
  [NYU-LLM-CTF/CTFJudge](https://github.com/NYU-LLM-CTF/CTFJudge), the
  official trajectory grader from the CTFTiny / D-CIPHER line of work
  (AAAI'26). Upstream has no `LICENSE` file as of this fork (commit
  `1eef031`); treated here as source-available for evaluation purposes only,
  not redistributed under a stated license.
- [`adapt_baseline_trajectory.py`](adapt_baseline_trajectory.py) — converts
  nyuctf_agents' baseline trajectory format into the shape CTFJudge expects
  (see [Format adapter](#format-adapter) below).
- [`run_all_models.py`](run_all_models.py) — driver that runs all 5 models
  against the fixed challenge sample and writes
  [`eval_results.jsonl`](eval_results.jsonl) / [`eval_summary.json`](eval_summary.json)
  (see [Results](#results-baseline-agent-run-2026-09-18) below).

Both vendored projects had their own `.git` history; it was dropped when
copying them in (no local commits existed in either — verified before
deleting) so this repo tracks the modifications as plain diffs against the
commits noted below, rather than as submodules.

- `nyuctf_agents` vendored at upstream commit `612190f` ("update dependencies")
- `CTFJudge` vendored at upstream commit `1eef031` ("Fix citation format in README.md")

## Why these two projects

- **nyuctf_agents**: the official baseline/D-CIPHER agent harness for
  [NYU CTF Bench](https://arxiv.org/abs/2406.05590) (NeurIPS'24 D&B) — real
  CSAW/pwn/rev/web/crypto/misc challenges, a working Docker sandbox, and a
  baseline single-agent harness alongside the more complex D-CIPHER
  planner/executor multi-agent one. Actively maintained, 163★, MIT.
- **CTFJudge**: an LLM-as-judge scorer built specifically for grading CTF
  *trajectories* (not just final-flag correctness) against a reference
  writeup, producing a CCI (something like "competency/completeness index")
  score — exactly the kind of process-quality metric a pure solve-rate number
  misses. Companion tool to the CTFTiny paper.

## What was modified and why

### 1. OpenRouter routing (both projects)

Both projects hard-code the Anthropic/OpenAI SDKs against their default
endpoints. All calls in this fork go through OpenRouter instead, so the same
code can run any of the five budget-tier models from the CyberMetric
comparison (including non-OpenAI/non-Anthropic ones like Qwen) without a
separate backend per provider.

- `nyuctf_agents/nyuctf_baseline/backends/openai_backend.py`: when
  `OPENROUTER_API_KEY` is set, the OpenAI SDK client points its `base_url` at
  `https://openrouter.ai/api/v1` instead of api.openai.com. Falls back to a
  real OpenAI key if only `OPENAI_API_KEY` is set (upstream behavior
  unchanged). Also added a `tiktoken` fallback to `cl100k_base` for model IDs
  tiktoken doesn't recognize (e.g. `qwen/qwen3.8-flash` — only used for a
  local cost estimate, doesn't need to be the real tokenizer).
- `CTFJudge/writeup_summary_agent.py`, `trajectory_summary_agent.py`,
  `qualitative_evaluation_agent.py`, `run_evaluation.py`: swapped the
  Anthropic SDK for the OpenAI SDK pointed at OpenRouter
  (`client.messages.create` → `client.chat.completions.create`,
  `response.content[0].text` → `response.choices[0].message.content`, env var
  `ANTHROPIC_API_KEY` → `OPENROUTER_API_KEY`). `CTFJudge/config.json`'s
  `model` is set to `anthropic/claude-sonnet-5` (OpenRouter's model ID) as the
  judge model, per the original CTFJudge paper's choice of a Claude Sonnet
  model as judge.
- `nyuctf_agents/nyuctf_baseline/backends/model_info.json`: added a
  `qwen/qwen3.8-flash` pricing entry so cost estimates resolve for that model.

### 2. Real cost tracking (`openai_backend.py`)

Upstream's local cost estimate only counted tokens in the *current turn's*
new user message, silently ignoring that every round resends the full
conversation history — undercounting real spend by roughly two orders of
magnitude once a conversation has a few rounds in it. `_call_model()` now
returns the full API response object, and `send()` reads OpenRouter's
authoritative `response.usage.cost` (computed server-side from real
request/response token counts) as the primary source, falling back to the old
local-estimate formula only when `.cost` isn't present (e.g. plain OpenAI
API, which doesn't return it).

### 3. Upstream bug fixes

- **`keys.cfg` crash**: `parse_keys()` in
  `nyuctf_baseline/backends/utils.py` catches `FileExistsError` instead of
  `FileNotFoundError` around `open(key_path)`, so a *missing* file crashes
  instead of falling back to `{}`. Not patched in the vendored code (works
  around it instead) — `nyuctf_agents/keys.cfg` (empty) needs to exist; it's
  gitignored (upstream's own `.gitignore` already excludes it), recreate with
  `touch nyuctf_agents/keys.cfg` before running. Not needed for OpenRouter
  runs either way since the OpenRouter key comes from the environment, not
  this file.
- **Missing dependencies**: `requirements.txt` has `ToolDefGenerator`,
  `jinja2`, `bs4`, `lxml`, `ruamel.yaml` commented out even though the active
  code imports them uncommented. Install them manually (see
  [Setup](#setup)).
- **Docker build fails on Apple Silicon**: `setup_baseline.sh`'s
  `docker build` doesn't pass `--platform`, so on arm64 Docker resolves i386
  packages against `ports.ubuntu.com` (no i386 packages there) instead of
  `archive.ubuntu.com`/`security.ubuntu.com`, and the build 404s partway
  through `apt-get install` (`libc6-dev:i386`, `gcc-multilib`, ...). Build
  with `--platform linux/amd64` explicitly (see [Setup](#setup)).

### Format adapter

nyuctf_agents (baseline) and CTFJudge (built for D-CIPHER) use incompatible
trajectory shapes:

| | baseline output | CTFJudge/D-CIPHER expects |
|---|---|---|
| top-level fields | `solved`, `cost`, `runtime.total`, `finish_reason` | `success`, `total_cost`, `time_taken`, `exit_reason` |
| conversation | flat `messages: [[timestamp, {role, content, tool_calls: [...]}], ...]`, OpenAI chat format | `planner`/`executors` lists of `{role: "MessageRole.X", index, content, tool_call: {...} | tool_result: {...}}` |
| tool calls per turn | plural `tool_calls` (OpenAI parallel tool calling) | singular `tool_call` — one per entry |
| tool results | `role: "tool"` messages, JSON-stringified `content` | separate `MessageRole.OBSERVATION` entries with a nested `tool_result.result` dict |

`adapt_baseline_trajectory.py` converts one into the other. Baseline has no
planner/executor split, so the whole conversation goes into CTFJudge's
`"planner"` list and `"executors"` is left `[]` (confirmed safe: CTFJudge's
`config.json` marks `executor_conversation` as `"required": false` with
`"default": []`, and no code indexes into it). A single baseline turn with
multiple tool calls is split into multiple synthetic `MessageRole.ASSISTANT`
entries, since CTFJudge's formatter only renders one `tool_call` per entry;
only the first split entry keeps the turn's reasoning text, so the same
reasoning doesn't get printed once per tool call. Tool output is also
stripped of ANSI color codes (radare2 etc. emit them; left in, they'd read as
~2-3x their real content in escape sequences to the judge LLM).

This required **zero changes to CTFJudge's own code or config** — it works
entirely by producing data in the exact shape CTFJudge's existing
`role_mappings`/`trajectory_fields` config already expects.

Usage:

```bash
python3 adapt_baseline_trajectory.py \
  nyuctf_agents/logs_baseline/<user>/<experiment>/<challenge>.json \
  CTFJudge/trajs/<challenge>.json
```

Verified by loading the adapted output through CTFJudge's own
`TrajectoryDecomposer.restructure_trajectory()` +
`_format_trajectory_for_analysis()` (not just checking it parses as JSON) —
correct metadata and a correctly rendered planner conversation log, no
duplicated reasoning text on multi-tool-call turns, no stray "EXECUTOR AGENT"
section.

## Setup

```bash
cd nyuctf_agents
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install "ToolDefGenerator @ git+https://github.com/moyix/ToolDefGenerator@main" \
  jinja2 bs4 lxml ruamel.yaml   # missing from requirements.txt upstream
touch keys.cfg                  # works around the FileExistsError/FileNotFoundError bug above

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

## Results (baseline agent, run 2026-09-18)

### Methodology

- **Challenge sample**: 12 challenges from NYU CTF Bench's test split (200
  total), 2 per category (crypto/forensics/misc/pwn/rev/web), selected with
  `random.seed(42)` — fixed and reproducible, not cherry-picked. See
  `run_all_models.py` for the exact list and selection code.
- **Budget**: `max_rounds: 12`, `max_cost: 1.5` per (model, challenge) run.
  The upstream repo's own default baseline config uses `max_rounds: 3`
  (looks like a placeholder) while its `launch_baseline.sh` driver script
  defaults to 30; 12 is a middle ground chosen to bound wall-clock time for
  this run. Every one of the 60 runs terminated at `max_rounds` or `solved`
  — `max_cost` never bound, so it had no effect at these prices.
- **Infra exclusion, symmetric across all 5 models**: 2 of the 12 challenges
  (`2021q-cry-ecc_pop_quiz`, `2021f-for-no_time_to_register`) hardcode their
  challenge server to host port 5000 via `docker-compose`. On macOS, port
  5000 is already bound by the OS's own AirPlay Receiver (ControlCenter), so
  `docker compose up` fails before the agent ever runs — for every model,
  identically and immediately (~10-85s). This is an environment conflict,
  not a model outcome; it's excluded from solve-rate denominators below.
  Because the exclusion is identical across all 5 models, comparing them on
  the remaining **10** challenges is still apples-to-apples.
- Full per-run data: [`eval_results.jsonl`](eval_results.jsonl) (60 rows, one
  per model×challenge, includes cost/time/finish_reason/error for every run
  including the 2 excluded ones). Aggregated: [`eval_summary.json`](eval_summary.json).
  Raw trajectory logs: `nyuctf_agents/logs_baseline/eval/NYU_Baseline_<model>/`.

### Solve rate (n=10 attempted challenges per model)

| Model | Solved | Solve rate | Avg wall time/run | Total cost (10 runs) | Cost/solve |
|---|---|---|---|---|---|
| DeepSeek V4.1 Flash | 5/10 | 50% | 222s | $0.1041 | $0.0208 |
| Qwen3.8 Flash | 3/10 | 30% | 186s | $0.0992 | $0.0331 |
| GLM 5.3 Flash | 3/10 | 30% | 284s | $0.0775 | $0.0258 |
| GPT-5.6 Luna | 2/10 | 20% | 115s | $0.1076 | $0.0538 |
| Solar Pro4 | 1/10 | 10% | 98s | $0.0902 | $0.0902 |

### This ranking is not statistically significant — do not cite it as one

n=10 paired challenges gives very little power. Since every model ran the
*same* 10 challenges, the correct test is a paired one (McNemar's exact
test on the win/loss pairs), not a two-proportion test. Running it on every
model pair:

| Pair | Discordant (b, c) | Exact p |
|---|---|---|
| DeepSeek vs Solar Pro4 (largest gap: 50% vs 10%) | 4, 0 | 0.125 |
| DeepSeek vs GPT-5.6 Luna | 3, 0 | 0.25 |
| DeepSeek vs Qwen3.8 / DeepSeek vs GLM 5.3 | 2, 0 | 0.50 |
| every other pair | ≤2, ≤2 | ≥0.50 |

**No pair reaches even p<0.10.** The largest observed gap in the table
(DeepSeek 50% vs Solar Pro4 10%) has a 12.5% chance of arising from a coin
flip. Two more facts sharpen why: 5 of the 10 challenges
(`2022q-msc-cattheflag`, `2022f-pwn-salt_server`, `2017q-for-missed_registration`,
`2018f-rev-1nsayne`, `2021q-web-securinotes`) were solved by **zero** of the
5 models and carry no discriminating information at all — the entire
comparison rests on the other 5. Reproduce the p-values from
`eval_results.jsonl` before trusting this table further; don't repeat the
ranking as a finding. (This also means the two Chinese-lab models in this
set, GLM 5.3 Flash and DeepSeek V4.1 Flash, landing 1st/tied-2nd here is
**not** evidence for the earlier "Chinese models are good at cybersecurity"
thread in this project's history — that finding was specific to GLM-5.3 on
CyberGym/Semgrep, a different task, and nothing here clears significance.)

### What this sample *can* support

- **Wall time has a real ~3x spread** (98s–284s avg per attempted
  challenge) at an identical 12-round budget — 10 continuous observations
  per model, not a binary outcome, so far more statistical power than solve
  rate. GLM 5.3 Flash is slowest, consistent with its reasoning being
  mandatory (can't be disabled, per the CyberMetric project's findings for
  this same model).
- **Cost is same order of magnitude for all five** ($0.078–$0.108 for 10
  attempts each) — consistent with all 5 being "budget tier" as originally
  selected. Cost-per-solve varies more (Solar Pro4 $0.09 vs DeepSeek $0.02)
  but inherits the same n=10 instability as solve rate — a model that
  happens to solve one extra cheap challenge moves this a lot. Treat the
  totals as the trustworthy number and cost-per-solve as illustrative only.

### Per-challenge solve matrix

| Challenge | Category | Solved by |
|---|---|---|
| `2020f-rev-rap` | rev | Qwen, Luna, DeepSeek, GLM (4/5) |
| `2017q-web-orange` | web | Qwen, Solar, DeepSeek, GLM (4/5) |
| `2017f-cry-ecxor` | crypto | Luna, DeepSeek |
| `2020q-pwn-slithery` | pwn | Qwen, DeepSeek |
| `2022q-msc-ezmaze` | misc | DeepSeek, GLM |
| `2022q-msc-cattheflag`, `2022f-pwn-salt_server`, `2017q-for-missed_registration`, `2018f-rev-1nsayne`, `2021q-web-securinotes` | misc/pwn/forensics/rev/web | none |

### Reproduce

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
cd ctftiny
python3 run_all_models.py   # ~60-90 min wall clock, concurrency=3
```

## Current status

- All 5 models run on the 12-challenge sample above. Format adapter
  (`adapt_baseline_trajectory.py`) verified against CTFJudge's own
  parsing/formatting code, but the **full CTFJudge/CCI pipeline has not
  been run on any of these 60 new trajectories** — that's LLM-judge scoring
  against a reference writeup, a separate phase from the solve-rate numbers
  above, and still blocked on writeups not existing for these challenges in
  `CTFJudge/writeups/`.

### Not done yet

- Full end-to-end CCI scoring via CTFJudge on any of the 60 trajectories
  from this run (needs a challenge with both a baseline trajectory *and* an
  existing writeup — `2023q-web-smug_dino` has a writeup already in this
  fork but no baseline trajectory yet).
- A larger challenge sample. n=10 has essentially no power to separate
  budget-tier models on solve rate (see above) — distinguishing e.g. a 50%
  from a 30% true solve rate at conventional significance would need on the
  order of 50-100+ paired challenges, not 10. NYU CTF Bench's own paper
  reports full-test-split baseline numbers at `max_rounds: 30`, three times
  this run's budget.
- Token/cost calibration for the agent harness itself (the CyberMetric
  project's `calibrate_tokens.py` has no CTF-agent equivalent).
