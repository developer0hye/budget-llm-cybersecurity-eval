# Shared functions for queue1.sh / queue2.sh (sourced). One server at a time; every run resumable.
REPO="$HOME/budget-llm-cybersecurity-eval"
SERVE="$REPO/local-spark/llm-serve"
PY="$REPO/.venv/bin/python"
LOGS="$REPO/local-spark/logs"
mkdir -p "$LOGS"
T0=$(date +%s)
CUR=""   # "<target> <seqs> <util>" of the server this queue last started

log() { echo "[$(date '+%F %T')] $*"; }

# serve <llm-serve target> <SEQS> [GPU_UTIL] [fallback SEQS] [fallback GPU_UTIL]
# Starts the server unless this queue already serves it with the same settings. If the requested
# settings fail to start (e.g. not enough memory for a larger KV pool), retries with the fallback,
# which is the last setting known to work on this box.
serve() {
  local target=$1 seqs=$2 util=${3:-} fb_seqs=${4:-$2} fb_util=${5:-}
  [ "$CUR" = "$target $seqs $util" ] && return 0
  log "starting $target SEQS=$seqs GPU_UTIL=${util:-default}"
  if SEQS=$seqs GPU_UTIL=$util "$SERVE" "$target" > "$LOGS/serve-$target-s$seqs-u${util:-d}.log" 2>&1; then
    CUR="$target $seqs $util"; log "server $target ready"; return 0
  fi
  log "server $target SEQS=$seqs GPU_UTIL=${util:-default} FAILED; retrying with SEQS=$fb_seqs GPU_UTIL=${fb_util:-default}"
  if SEQS=$fb_seqs GPU_UTIL=$fb_util "$SERVE" "$target" > "$LOGS/serve-$target-s$fb_seqs-u${fb_util:-d}.log" 2>&1; then
    CUR="$target $fb_seqs $fb_util"; log "server $target ready (fallback)"; return 0
  fi
  CUR=""; log "server $target FAILED twice; skipping its runs"; return 1
}

run() {  # run <model short name> <off|on|on_card>; a second pass retries transport failures
  local m=$1 cond=$2 r=${2%_card} sampling=greedy
  [ "$cond" = on_card ] && sampling=card
  for pass in 1 2; do
    log "run $m $cond pass $pass (server: $CUR)"
    BCSE_SAMPLING=$sampling "$PY" -u "$REPO/local-spark/run_local.py" --models "$m" --reasoning "$r" \
      --concurrency 192 --out "local-spark/work_reasoning_$cond" >> "$LOGS/${m}_$cond.log" 2>&1
    grep -q "INCOMPLETE $m" "$LOGS/${m}_$cond.log" 2>/dev/null || break
  done
  log "done $m $cond: $(tail -n 6 "$LOGS/${m}_$cond.log" | tr '\r' '\n' | grep -E '^'"$m"'|wall-clock|INCOMPLETE' | tr '\n' ' ')"
}

wait_runs() {  # wait until no run_local.py is running on this box (a run started by an earlier queue)
  while pgrep -f "local-spark/run_local[.]py|bcse-local/run_local[.]py" >/dev/null; do sleep 60; done
}
