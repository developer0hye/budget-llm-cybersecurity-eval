"""Models under test and per-provider quirks, shared by every harness in this repo."""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Short name -> OpenRouter model ID. Selection criterion: the budget-tier
# model of each provider, in the same OpenRouter price band as Solar Pro 4
# (checked 2026-09-17).
MODELS = {
    "solar-pro4": "upstage/solar-pro4",
    "gpt-5.6-luna": "openai/gpt-5.6-luna",
    # Added 2026-09-25, after the first knowledge-axis results were analysed
    # (OpenRouter listed it 2026-09-23; $0.10 in / $0.50 out per 1M). GPT-5.6
    # Luna stays: it is the only model with a same-model Cybench anchor
    # (arXiv:2607.15263).
    "gpt-6-luna": "openai/gpt-6-luna",
    "deepseek-v4.1-flash": "deepseek/deepseek-v4.1-flash",
    "glm-5.3-flash": "z-ai/glm-5.3-flash",
}
# Also considered on 2026-09-24, in Qwen's place:
# - mistralai/mistral-small-2603 (Mistral Small 4, $0.15 in / $0.60 out per
#   1M), the only Mistral model in the band. Dropped: every request returned
#   HTTP 429 with limit_source "upstream_provider_shared_pool" (20/20
#   sequential calls at 1/s), i.e. OpenRouter's shared Mistral quota was
#   exhausted, not this harness's concurrency.
# - No Anthropic or xAI model is in the band: the cheapest current ones are
#   Claude Haiku 4.5 ($1 / $5) and Grok 4.3 ($1.25 / $2.50).
# qwen/qwen3.8-flash was dropped on 2026-09-24, before any full-run result was
# analysed: with reasoning on, its call latency put the full knowledge run at
# ~8 h against 2-4 h for the other models (0 x 429 at 6/20/40 in flight --
# latency, not rate limiting). Its pilot rows remain in knowledge/pilot/.

# Endpoints that reject `reasoning: {enabled: false}` with
# "Reasoning is mandatory for this endpoint and cannot be disabled."
REASONING_MANDATORY = {"z-ai/glm-5.3-flash"}

# Per-model in-flight request caps below the global --concurrency (none needed
# for the current models).
MODEL_CONCURRENCY_CAP: dict[str, int] = {}

# Every model is pinned to one OpenRouter provider with fallbacks off.
# Unpinned, the 2026-09-24 pilot was served by 25 providers for GLM and 18 for
# DeepSeek (different hardware, quantization and serving stacks), while the
# other three only have first-party endpoints. Four are first-party (Z.AI
# serves GLM at fp8). DeepSeek's own endpoint is excluded by this account's
# OpenRouter privacy setting (it may train on paid prompts: "Paid model
# training violation"), so DeepSeek is pinned to StreamLake (fp8), the provider
# that served most of its pilot calls (171/600).
PROVIDER = {
    "upstage/solar-pro4": "upstage",
    "openai/gpt-5.6-luna": "openai",
    "openai/gpt-6-luna": "openai",
    "deepseek/deepseek-v4.1-flash": "streamlake",
    "z-ai/glm-5.3-flash": "z-ai",
}
