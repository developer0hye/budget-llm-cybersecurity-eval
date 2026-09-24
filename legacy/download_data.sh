#!/usr/bin/env bash
# Fetch CyberMetric question sets at run time rather than vendoring them.
# The upstream repo (github.com/cybermetric/CyberMetric) has no LICENSE file,
# so redistribution rights are unclear -- don't commit these JSON files.
set -euo pipefail
cd "$(dirname "$0")"
# Pinned to the upstream commit the documented runs (2026-09-17/18) fetched.
# Upstream edited question text in place on 2026-05-27 (e.g. 97faa42 changed
# 2 lines of the 2000-question file), so fetching `main` is not reproducible.
CYBERMETRIC_COMMIT=294662b03be73a9c7c73918f687882c1ba637c47
mkdir -p data
for size in 80 500 2000 10000; do
  echo "Fetching CyberMetric-${size}-v1.json..."
  curl -sf -o "data/CyberMetric-${size}-v1.json" \
    "https://raw.githubusercontent.com/cybermetric/CyberMetric/${CYBERMETRIC_COMMIT}/CyberMetric-${size}-v1.json"
done
echo "Done."
