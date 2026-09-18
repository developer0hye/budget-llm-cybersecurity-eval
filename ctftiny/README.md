# CTF-solving agent evaluation (phase 2)

Companion project to the [CyberMetric budget-model comparison](../README.md) in
this repo. CyberMetric measures pure cybersecurity *knowledge* (multiple-choice
questions); this directory sets up a pipeline to measure practical CTF-*solving*
skill for the same budget-tier models, using two existing open-source projects
from NYU's LLM-CTF group rather than building an agent harness from scratch.

**Status: infrastructure only.** This is a working, verified pipeline, not yet
a benchmark result. Only one model (Qwen3.8 Flash, the cheapest of the five)
has been run, on one challenge, as a 3-round smoke test — see
[Current status](#current-status) below.

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

## Current status

- One model (Qwen3.8 Flash), one challenge (`2021f-rev-maze`, CSAW-Finals
  2021, 500-pt reverse engineering), 3-round smoke test. Agent used
  `radare2`/`nc`/`file`/`strings` autonomously against the real binary and
  remote server; did not solve it in 3 rounds (`finish_reason: max_rounds`).
- Format adapter verified against CTFJudge's own parsing/formatting code
  (see above), but the **full CCI pipeline has not been run end-to-end** —
  no reference writeup exists for `2021f-rev-maze` in `CTFJudge/writeups/`,
  and scoring a failed (`max_rounds`) trajectory against a synthesized
  writeup wouldn't distinguish a correct adapter from a broken one anyway.
  The sanity-tested path so far is `WriteupDecomposer().analyze_writeup(...)`
  returning valid parsed JSON from Sonnet 5 via OpenRouter, plus the
  adapter-output verification above — not a real CCI score.

### Not done yet

- Running the other four models (Solar Pro4, GPT-5.6 Luna, DeepSeek V4.1
  Flash, GLM 5.3 Flash) through the same harness.
- A full end-to-end CCI run (needs a challenge with both a baseline
  trajectory *and* an existing writeup — `2023q-web-smug_dino` has a writeup
  already in this fork but no baseline trajectory yet).
- Any statistical framework for comparing CTF solve rates / CCI scores across
  models (the CyberMetric project's ~2.2pp significance threshold doesn't
  carry over directly — CTF challenge counts are much smaller than 2000
  questions, so the right test is different).
- Token/cost calibration for the agent harness itself (the CyberMetric
  project's `calibrate_tokens.py` has no CTF-agent equivalent).
