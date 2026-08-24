#!/usr/bin/env bash
# Run FAST-LIO2 on Mid-360 sequence and capture TUM trajectory.
set -euo pipefail

BAG="${1:-$HOME/Downloads/IndoorOffice1_ros2_v2}"
CONFIG_FILE="${2:-mid360.yaml}"
OUT_DIR="${3:-results/indooroffice1/fastlio2}"
[ "$BAG" = *"IndoorOffice2"* ] && OUT_DIR="results/indooroffice2/fastlio2"
[ "$BAG" = *"OutdoorRoad"* ] && OUT_DIR="results/outdoorroad/fastlio2"
mkdir -p "$OUT_DIR"

source /opt/ros/humble/setup.bash
source "$HOME/slam_ws/install/setup.bash" 2>/dev/null || true
source "$HOME/Documents/ws_livox/install/setup.bash" 2>/dev/null || true
source "$HOME/FAST_LIO/install/setup.bash"

echo ">>> Launch FAST-LIO2 in background (config=$CONFIG_FILE)"
ros2 launch fast_lio mapping.launch.py rviz:=false config_file:="$CONFIG_FILE" &
FASTLIO_PID=$!
sleep 5

echo ">>> Recording odometry"
ros2 bag record -o "$OUT_DIR/fastlio2_odom" /Odometry &
REC_PID=$!
sleep 1

echo ">>> Playing bag"
ros2 bag play "$BAG"
sleep 3

kill "$REC_PID" 2>/dev/null || true
kill "$FASTLIO_PID" 2>/dev/null || true
sleep 2

echo ">>> Converting to TUM"
evo_traj bag2 "$OUT_DIR/fastlio2_odom" /Odometry --save_as_tum 2>/dev/null && \
  mv Odometry.tum "$OUT_DIR/fastlio2_mid360.tum" || \
  echo "!! Check topic name — may differ from /Odometry"

echo ">>> Done: $OUT_DIR"
