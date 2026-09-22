# Agent instructions

This repo is a benchmark report: two evaluations of the same 5 budget-tier
models, one on cybersecurity knowledge (CyberMetric MCQ), one on agentic
CTF-solving (NYU CTF Bench via a tool-using agent). Everything here is read
by practitioners in cybersecurity, AI evaluation, and agentic AI, and is
meant to be citable. Write for that reader.

## Write documentation in the field's own vocabulary

Use the terms a cybersecurity / AI / agentic-AI practitioner already uses.
Do not translate them down into consumer phrasing, and do not invent
project-local synonyms for concepts that already have names.

- **Evaluation**: solve rate, pass@1, attempted vs. no-log, paired/matched
  data, McNemar's exact test, discordant pairs, Bonferroni correction,
  sensitivity check, confound, contamination, held-out split. Say "not
  significant (p=0.18)", never "basically the same".
- **Agentic AI**: agent loop, tool-use, trajectory, rounds (`max_rounds`),
  token/cost budget, reasoning tokens, provider default, harness, judge
  (LLM-as-judge), finish reason, MCP server, hook, sandbox.
- **Security**: LaunchDaemon/LaunchAgent, TCC prompt, ad-hoc code signature,
  Team ID, notarization, C2 beacon, persistence, container escape, Docker
  socket mount, privilege escalation, supply chain, IOC, quarantine flag.
- **Infrastructure**: port binding, bind probe, lock contention, deadlock,
  concurrency, ENOSPC, image pull vs. build, compose project.

Name things exactly: model IDs (`deepseek/deepseek-v4.1-flash`), upstream
commits (`1eef031`), file paths, flags (`--force-recreate`), CVE or bug
identifiers, dates in ISO form. A reader should be able to act on the text
without asking what was meant.

Assume domain fluency — do not explain what a CTF or a p-value is. Do
explain anything specific to *this* project: why a knob was set the way it
was, what a number's denominator is, what a caveat costs the conclusion.

No marketing adjectives ("powerful", "cutting-edge", "seamless") and no
hedging filler. Claims carry a number, a test, or a file reference.

## Numbers are claims, and claims get verified

- Every figure in a README must be recomputable from the committed
  `.jsonl` / `.json` data. Before publishing a number, recompute it from
  the raw rows rather than copying it from an earlier draft.
- State the denominator whenever a rate is reported (of attempted? of 200?),
  and the sample size for every statistical test.
- When a methodological judgement could change a conclusion (how timeouts
  or API errors are counted, which subset is compared), report the
  sensitivity check alongside the headline, not instead of it.

## Report infrastructure failures, do not launder them

Failed jobs, deadlocks, rate limits and broken challenge images are part of
the result. Diagnose the root cause, fix it, re-run, and write down what
happened — including what it would have looked like if left unfixed. A row
that failed for infrastructure reasons is never silently counted as a model
failure.

## Third-party code

Vendoring is a redistribution decision, not a convenience. Check the
upstream LICENSE before copying code into this repo; if there is none, ship
a patch plus clone instructions instead (see
`ctftiny/ctfjudge-openrouter.patch`). Retain upstream license files for code
that is vendored, and pin the upstream commit in the README.
