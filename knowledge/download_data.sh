#!/usr/bin/env bash
# Fetch the knowledge-axis task files at run time, pinned by HuggingFace
# dataset revision and checked by SHA-256.
#   WMDP-cyber  cais/wmdp          MIT
#   CTIBench    AI4Sec/cti-bench   CC BY-NC-SA 4.0 -- not compatible with this
#               repo's Apache-2.0, so neither dataset is committed.
set -euo pipefail
cd "$(dirname "$0")/.."
WMDP_REV=7125571f22f032c56415e7980f48d877dd830ff8       # 2024-04-27
CTIBENCH_REV=9237e1636ee3e168fbe5ebdcc1c571de0525e568   # 2024-08-17
HF=https://huggingface.co/datasets
mkdir -p data
while read -r sha out url; do
  echo "Fetching ${out}..."
  curl -sfL -o "data/${out}" "${url}"
  echo "${sha}  data/${out}" | sha256sum -c --quiet
done <<SUMS
ec65f7ba4a9cd1ef368618ebd2b90b6d930f9b9f053f67a926b82fd71d87b4fe wmdp-cyber.parquet ${HF}/cais/wmdp/resolve/${WMDP_REV}/wmdp-cyber/test-00000-of-00001.parquet
11e0af8db2dae9706c6e79901d2390bcdf9746e8feccbd9ba10682df649bcc6a cti-mcq.tsv ${HF}/AI4Sec/cti-bench/resolve/${CTIBENCH_REV}/cti-mcq.tsv
ed7d7fa79fc912c627f96e229eaa38b3c4b6be813d834d434580be6d4703d700 cti-rcm.tsv ${HF}/AI4Sec/cti-bench/resolve/${CTIBENCH_REV}/cti-rcm.tsv
SUMS
echo "Done."
