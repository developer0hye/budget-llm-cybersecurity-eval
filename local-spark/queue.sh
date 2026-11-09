#!/bin/bash
# Run the knowledge axis for every local model, one server at a time, without depending on an SSH
# session (the 2026-11-09 Wi-Fi route change dropped SSH mid-run). Each step is resumable: the
# upstream harness keys rows by (task, item), so re-running a step only sends the missing items.
#
# Order: every model with reasoning off first, fastest model first, then reasoning on in the same
# order, so results arrive from the quickest runs. Costs ~10 server switches (~5-8 min each).
#
# usage: setsid nohup ~/budget-llm-cybersecurity-eval/local-spark/queue.sh > queue.log 2>&1 < /dev/null &
set -uo pipefail

REPO="$HOME/budget-llm-cybersecurity-eval"
SERVE="$REPO/local-spark/llm-serve"
PY="$REPO/.venv/bin/python"
LOGS="$REPO/local-spark/logs"
mkdir -p "$LOGS"
T0=$(date +%s)

log() { echo "[$(date '+%F %T')] $*"; }

# Wait for a knowledge run started outside this queue (the 27B reasoning-off run) to finish.
while pgrep -f "local-spark/run_local[.]py|bcse-local/run_local[.]py" >/dev/null; do sleep 60; done

serve() {  # serve <llm-serve target> <SEQS> <served model id> ; falls back to the target's default SEQS if it fails
  local target=$1 seqs=$2
  if [ "$(curl -s -m 5 localhost:8000/v1/models | grep -o '"id":"[^"]*"' | head -1)" = "\"id\":\"$3\"" ] \
     && [ "${CUR_SEQS:-}" = "$seqs" ]; then
    log "server $target already up"; return 0
  fi
  log "starting $target SEQS=$seqs"
  if SEQS=$seqs "$SERVE" "$target" > "$LOGS/serve-$target-s$seqs.log" 2>&1; then
    CUR_SEQS=$seqs; log "server $target ready"; return 0
  fi
  log "server $target SEQS=$seqs FAILED; retrying with default SEQS"
  if "$SERVE" "$target" > "$LOGS/serve-$target-default.log" 2>&1; then
    CUR_SEQS=default; log "server $target ready (default SEQS)"; return 0
  fi
  log "server $target FAILED twice; skipping its runs"; return 1
}

run() {  # run <model short name> <off|on>; second pass retries rows that failed for transport reasons
  local m=$1 r=$2
  for pass in 1 2; do
    log "run $m reasoning=$r pass $pass"
    "$PY" -u "$REPO/local-spark/run_local.py" --models "$m" --reasoning "$r" --concurrency 64 \
      --out "local-spark/results_reasoning_$r" >> "$LOGS/${m}_$r.log" 2>&1
    (cd "$REPO" && grep -q "INCOMPLETE $m" "$LOGS/${m}_$r.log" 2>/dev/null) || break
  done
  log "done $m reasoning=$r: $(tail -n 6 "$LOGS/${m}_$r.log" | tr '\r' '\n' | grep -E '^'"$m"'|wall-clock|INCOMPLETE' | tr '\n' ' ')"
}

cd "$REPO"
CUR_SEQS=32   # the 27B server was started with SEQS=32 before this queue
# Phase A: reasoning off for every model, fastest first (user asked for the quickest results first).
serve gemma26 32 gemma-4-26b-a4b-it && run gemma-4-26b-a4b off
serve qwen38 16 qwen38-flash-next-fp4-local && run qwen3.8-flash-next off
serve gemma12 32 gemma-4-12b-it && run gemma-4-12b off
serve gemma4 32 gemma-4-31b-it && run gemma-4-31b off
# Phase B: reasoning on, same speed order (26B-A4B and Flash-Next decode 50-80 tok/s, 31B ~26).
serve gemma26 32 gemma-4-26b-a4b-it && run gemma-4-26b-a4b on
serve qwen38 16 qwen38-flash-next-fp4-local && run qwen3.8-flash-next on
serve qwen27 32 qwen38-27b && run qwen3.8-27b on
serve gemma12 32 gemma-4-12b-it && run gemma-4-12b on
serve gemma4 32 gemma-4-31b-it && run gemma-4-31b on
log "queue finished in $(( ($(date +%s) - T0) / 60 )) min"
