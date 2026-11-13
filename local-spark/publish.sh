#!/bin/bash
# Copy every *complete* local run (4,496 scored rows, no transport errors) from the device's
# working dirs into local-spark/results_reasoning_{off,on,on_card}/ and recompute the analysis, so
# the committed tables never mix in a run that is still going. Partial runs stay out until done.
# Runs finished on the second Spark are copied into this box's working dirs first (by hand).
set -euo pipefail
REPO="$HOME/budget-llm-cybersecurity-eval"
cd "$REPO"
for r in off on on_card; do
  src="local-spark/work_reasoning_$r"; dst="local-spark/results_reasoning_$r"
  [ -L "$dst" ] && rm "$dst"
  [ -d "$src" ] || continue
  mkdir -p "$dst"
  for f in "$src"/*.jsonl; do
    [ -e "$f" ] || continue
    n=$(.venv/bin/python -c "import json,sys;rows=[json.loads(l) for l in open(sys.argv[1])];print(sum(1 for x in rows if not x['error']) if len({(x['task'],x['item']) for x in rows})==4496 else 0)" "$f")
    if [ "$n" = 4496 ]; then cp "$f" "$dst/"; echo "published $dst/$(basename "$f")"; else echo "skip $f (not complete: $n)"; fi
  done
  cp "$src/run_config.json" "$dst/" 2>/dev/null || true
done
A=".venv/bin/python local-spark/analyze_spark.py"
$A off --json local-spark/analysis_reasoning_off.json > local-spark/analysis_reasoning_off.txt
if ls local-spark/results_reasoning_on/*.jsonl >/dev/null 2>&1; then
  $A on --json local-spark/analysis_reasoning_on.json --compare-off > local-spark/analysis_reasoning_on.txt
fi
if ls local-spark/results_reasoning_on_card/*.jsonl >/dev/null 2>&1; then
  $A on_card --json local-spark/analysis_reasoning_on_card.json --compare-off --compare-greedy \
    > local-spark/analysis_reasoning_on_card.txt
fi
echo done
