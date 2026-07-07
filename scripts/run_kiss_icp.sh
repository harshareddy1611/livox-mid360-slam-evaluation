#!/usr/bin/env bash
set -euo pipefail
BAG="${1:-$HOME/Downloads/IndoorOffice1_ros2_v2}"
TOPIC="${2:-/mid360/livox/lidar}"
OUT_DIR="results/mid360"
mkdir -p "$OUT_DIR"
echo ">>> KISS-ICP on $BAG topic $TOPIC"
kiss_icp_pipeline "$BAG" --topic "$TOPIC" --max_range 60.0 --deskew --visualize=False
echo ">>> Look under ./results/ for the output folder; copying newest *tum*:"
LATEST=$(find results -iname "*tum*" -newermt '-5 minutes' | head -n1 || true)
if [ -n "${LATEST:-}" ]; then
  cp "$LATEST" "$OUT_DIR/kiss_icp_mid360.tum"
  echo ">>> Saved: $OUT_DIR/kiss_icp_mid360.tum"
else
  echo "!! No tum file auto-found. Run: find results -iname '*.txt' -o -iname '*.tum'"
fi
