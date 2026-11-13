#!/bin/bash
# Spark-1 share (2026-11-09 plan): Qwen3.8-Flash-Next reasoning-on (greedy, then model-card
# sampling) and Gemma 4 31B reasoning-on greedy. Waits for the Flash-Next reasoning-off run started
# by an earlier queue. 22:55: Flash-Next restarts with a larger KV pool (GPU_UTIL 0.9) and 32
# sequences to test whether throughput improves; falls back to the 0.8 / 16 it ran with so far.
# usage: setsid nohup local-spark/queue1.sh > queue1.log 2>&1 < /dev/null &
set -uo pipefail
. "$(dirname "$0")/queue_common.sh"
cd "$REPO"
wait_runs
serve qwen38 32 0.9 16 0.8 && { run qwen3.8-flash-next on; run qwen3.8-flash-next on_card; }
serve gemma4 128 "" 64 && run gemma-4-31b on   # its card-sampling run moved to spark-2 to balance the boxes
log "queue1 finished in $(( ($(date +%s) - T0) / 60 )) min"
