#!/bin/bash
# Spark-1 share (2026-11-09 22:40 plan): Qwen3.8-Flash-Next and Gemma 4 31B reasoning-on runs,
# greedy (protocol) then model-card sampling on the same server. Waits for the Flash-Next
# reasoning-off run started by the previous queue.
# usage: setsid nohup local-spark/queue1.sh > queue1.log 2>&1 < /dev/null &
set -uo pipefail
. "$(dirname "$0")/queue_common.sh"
cd "$REPO"
wait_runs
CUR="qwen38 16"   # the Flash-Next server was started with SEQS=16 by the previous queue
serve qwen38 16 && { run qwen3.8-flash-next on; run qwen3.8-flash-next on_card; }
serve gemma4 32 && { run gemma-4-31b on; run gemma-4-31b on_card; }
log "queue1 finished in $(( ($(date +%s) - T0) / 60 )) min"
