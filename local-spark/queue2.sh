#!/bin/bash
# Spark-2 share (2026-11-09 plan). Waits for the Gemma 4 26B-A4B greedy reasoning-on run started by
# an earlier queue (32 server sequences), then runs the rest with 64 server sequences (22:55: test
# whether throughput improves; each falls back to 32 if the server does not start).
# usage: setsid nohup local-spark/queue2.sh > queue2.log 2>&1 < /dev/null &
set -uo pipefail
. "$(dirname "$0")/queue_common.sh"
cd "$REPO"
wait_runs
serve gemma26 128 "" 64 && { run gemma-4-26b-a4b on; run gemma-4-26b-a4b on_card; }   # A/B 23:00: 32 -> 908, 64 -> 1267, 128 -> 1657, 256 -> 1425 tok/s
serve gemma4 128 "" 64 && run gemma-4-31b off
serve qwen27 128 "" 64 && { run qwen3.8-27b on; run qwen3.8-27b on_card; }
serve gemma12 128 "" 64 && { run gemma-4-12b on; run gemma-4-12b on_card; }
serve gemma4 128 "" 64 && run gemma-4-31b on_card   # moved from spark-1 to balance the boxes
log "queue2 finished in $(( ($(date +%s) - T0) / 60 )) min"
