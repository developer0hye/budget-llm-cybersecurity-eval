#!/bin/bash
# Spark-2 share (2026-11-09 22:40 plan). Waits for the Gemma 4 26B-A4B reasoning-on run started by
# the previous queue, then runs the rest: greedy (protocol) first, model-card sampling right after
# on the same server.
# usage: setsid nohup local-spark/queue2.sh > queue2.log 2>&1 < /dev/null &
set -uo pipefail
. "$(dirname "$0")/queue_common.sh"
cd "$REPO"
wait_runs
CUR="gemma26 32"  # started by the previous queue
serve gemma26 32 && run gemma-4-26b-a4b on_card
serve gemma4 32 && run gemma-4-31b off
serve qwen27 32 && { run qwen3.8-27b on; run qwen3.8-27b on_card; }
serve gemma12 32 && { run gemma-4-12b on; run gemma-4-12b on_card; }
log "queue2 finished in $(( ($(date +%s) - T0) / 60 )) min"
