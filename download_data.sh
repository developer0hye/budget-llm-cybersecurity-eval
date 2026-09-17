#!/usr/bin/env bash
# Fetch CyberMetric question sets at run time rather than vendoring them.
# The upstream repo (github.com/cybermetric/CyberMetric) has no LICENSE file,
# so redistribution rights are unclear -- don't commit these JSON files.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data
for size in 80 500 2000 10000; do
  echo "Fetching CyberMetric-${size}-v1.json..."
  curl -sf -o "data/CyberMetric-${size}-v1.json" \
    "https://raw.githubusercontent.com/cybermetric/CyberMetric/main/CyberMetric-${size}-v1.json"
done
echo "Done."
