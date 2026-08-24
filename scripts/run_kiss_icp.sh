#!/usr/bin/env bash
set -eo pipefail  # no -u: ROS2 setup.bash references unset vars internally
export PATH="$HOME/.local/bin:$PATH"  # pip-installed kiss_icp_pipeline
BAG="${1:-$HOME/Downloads/IndoorOffice1_ros2_v2}"
TOPIC="${2:-/mid360/livox/lidar}"
OUT_DIR="${3:-results/mid360}"
mkdir -p "$OUT_DIR"
echo ">>> KISS-ICP on $BAG topic $TOPIC"
# kiss-icp 1.3.x dropped --max_range/--deskew/--visualize=False CLI flags;
# max_range is now set via this env var, deskew is on by default.
export kiss_icp_data='{"max_range": 60.0}'
kiss_icp_pipeline "$BAG" --topic "$TOPIC"
echo ">>> Look under ./results/ for the output folder; copying newest *tum*:"
LATEST=$(find results -iname "*tum*" -newermt '-2 minutes' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n1 | cut -d' ' -f2- || true)
if [ -n "${LATEST:-}" ]; then
  cp "$LATEST" "$OUT_DIR/kiss_icp_mid360.tum"
  echo ">>> Saved: $OUT_DIR/kiss_icp_mid360.tum"
else
  echo "!! No tum file auto-found. Run: find results -iname '*.txt' -o -iname '*.tum'"
fi
