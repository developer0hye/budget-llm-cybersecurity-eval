# Shared functions for queue1.sh / queue2.sh (sourced). One server at a time; every run resumable.
REPO="$HOME/budget-llm-cybersecurity-eval"
SERVE="$REPO/local-spark/llm-serve"
PY="$REPO/.venv/bin/python"
LOGS="$REPO/local-spark/logs"
mkdir -p "$LOGS"
T0=$(date +%s)
CUR=""   # "<target> <seqs>" of the server this queue last started

log() { echo "[$(date '+%F %T')] $*"; }

serve() {  # serve <llm-serve target> <SEQS>; no restart if this queue already serves it
  local target=$1 seqs=$2
  [ "$CUR" = "$target $seqs" ] && return 0
  log "starting $target SEQS=$seqs"
  if SEQS=$seqs "$SERVE" "$target" > "$LOGS/serve-$target-s$seqs.log" 2>&1; then
    CUR="$target $seqs"; log "server $target ready"; return 0
  fi
  log "server $target SEQS=$seqs FAILED; retrying with default SEQS"
  if "$SERVE" "$target" > "$LOGS/serve-$target-default.log" 2>&1; then
    CUR="$target default"; log "server $target ready (default SEQS)"; return 0
  fi
  CUR=""; log "server $target FAILED twice; skipping its runs"; return 1
}

run() {  # run <model short name> <off|on|on_card>; a second pass retries transport failures
  local m=$1 cond=$2 r=${2%_card} sampling=greedy
  [ "$cond" = on_card ] && sampling=card
  for pass in 1 2; do
    log "run $m $cond pass $pass"
    BCSE_SAMPLING=$sampling "$PY" -u "$REPO/local-spark/run_local.py" --models "$m" --reasoning "$r" \
      --concurrency 64 --out "local-spark/work_reasoning_$cond" >> "$LOGS/${m}_$cond.log" 2>&1
    grep -q "INCOMPLETE $m" "$LOGS/${m}_$cond.log" 2>/dev/null || break
  done
  log "done $m $cond: $(tail -n 6 "$LOGS/${m}_$cond.log" | tr '\r' '\n' | grep -E '^'"$m"'|wall-clock|INCOMPLETE' | tr '\n' ' ')"
}

wait_runs() {  # wait until no run_local.py is running on this box (a run started by an earlier queue)
  while pgrep -f "local-spark/run_local[.]py|bcse-local/run_local[.]py" >/dev/null; do sleep 60; done
}
