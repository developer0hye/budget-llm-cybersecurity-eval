# Run notes

Operational details, deviations and incidents behind [README.md](README.md).
Each section is linked from the README. Numbers here are recomputable from the
committed logs unless a section says otherwise.

## Models considered and not run

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

## GPT-6 Luna

GPT-6 Luna ($0.10/$0.50) appeared on OpenRouter on
2026-09-23 and was added after the first four models' knowledge results
had been analysed. GPT-5.6 Luna stays, because it is the only model with
a same-model Cybench anchor.

**GPT-6 Luna was added after the first four models' results had been
analysed.** It was released on OpenRouter on 2026-09-23. The addition
grows the between-model family from 6 to 10 pairs, so the Bonferroni
threshold tightens from 0.0083 to 0.005. That changes one earlier call:
DeepSeek vs GLM on CTI-RCM (p = 0.0063) was significant among four models
and is not among five. Everything else was run and scored exactly as for
the other four.

## DeepSeek provider

DeepSeek's first-party endpoint is excluded by this account's OpenRouter privacy setting, because that endpoint may train on prompts (the routing error reads "Paid model training violation"). DeepSeek therefore runs on StreamLake fp8, the provider that served most of its pilot traffic (171/600).

## AthenaBench harness

Harness code for AthenaBench was written and then removed; its extractor matched upstream on 62,499 released responses.

## Reasoning non-termination

Why non-termination gets its own category: in the pilot, GLM hit the cap
on 86/600 calls, 85 with empty content. The captured reasoning shows two
distinct failure modes:

- **Oscillation (GLM).** 65–111 `Wait`/`Actually`/`reconsider` per trace.
  The model commits to an answer and reopens it, up to 11 times in one
  trace.
- **Degenerate enumeration (Qwen, CTI-MCQ item 1060).** The model lists
  non-existent ATT&CK IDs, `M4671? M4672? … M4820`, until the 16,000-token
  cap.

These two descriptions come from reasoning traces captured by re-running
truncated pilot items (9 GLM calls, 4 Qwen calls) with the reasoning text
returned. Those captures are not in the committed logs, which store the
visible response, `finish_reason` and token usage, not the reasoning text.
The truncation counts above are recomputable from `knowledge/pilot/`.

## Knowledge axis: empty-content failure

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

- 61 returned content on retry.
- 5 came back with `finish_reason: "length"` (the 16,000-token cap) and
  are counted as `no_answer_truncated`.
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

### What "reasoning on" meant per model

`reasoning: {enabled: true}` is OpenRouter's medium effort. It **allows**
reasoning; it does not force it.

- GPT-5.6 Luna used 0 reasoning tokens on 19/996 WMDP rows and 138/2,500
  CTI-MCQ rows (adaptive reasoning).
- Solar, DeepSeek and GLM reasoned on every row that returned usage.
- With reasoning off, Solar, Luna and DeepSeek used 0 reasoning tokens on
  every row.

## Knowledge pilot

[`knowledge/pilot/`](knowledge/pilot/) holds 3,000 calls: 200 seeded-random
items per original task, run **before** the design above was fixed. It
differs from the full run in four ways:

- it includes Qwen3.8 Flash, since dropped;
- providers were unpinned;
- `max_tokens` was 8000;
- WMDP computation items were included.

It is kept because it is the evidence for three decisions: the WMDP cut,
the 16000 cap, and provider pinning. Do not cite its accuracies.

## Agentic axis: context compaction

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

## Agentic axis: timeouts and re-runs

The idle timeout only arms
  after a call's first streamed chunk (inspect_ai 0.3.268), so it
  abandons a call that stalls mid-stream. A call that never streams at
  all is caught only by the 900 s `attempt_timeout`. The first full pass used a 300 s total-time `attempt_timeout`;
  samples that hit it at least once were re-run under the new setting
  (Solar Pro 4 19, GLM 5.3 Flash 13, GPT-6 Luna 4, DeepSeek V4.1 Flash 3).

## Agentic axis: network policy details

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
- **Why the change:** a first run with Docker's unrestricted egress
  showed agents reaching public code hosts on 2 of 39 samples. That run
  is kept in `agentic/logs_unrestricted_network/` as design data and is
  not scored.

## Agentic axis: cluster

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

## Legacy log paths

Before publication, local absolute paths in `legacy/ctftiny/` logs were
normalised: the run host's home directory became `$HOME`, the repository
checkout became `/path/to/repo`, and a log folder named after the local
user became `logs_baseline/user/`. 47 legacy files changed; no figure
depends on these strings, and no file outside `legacy/` was touched.
