#!/usr/bin/env bash
# Run GLIM on Mid-360 sequence and capture TUM trajectory.
# Records /glim_ros/odom_corrected (post loop-closure, globally optimized) —
# this is GLIM's actual value-add over plain odometry, use it for evaluation.
set -euo pipefail

BAG="${1:-$HOME/Downloads/IndoorOffice1_ros2_v2}"
CONFIG_PATH="${2:-}"
OUT_DIR="${3:-results/indooroffice1/glim}"
[ "$BAG" = *"IndoorOffice2"* ] && OUT_DIR="results/indooroffice2/glim"
[ "$BAG" = *"OutdoorRoad"* ] && OUT_DIR="results/outdoorroad/glim"
mkdir -p "$OUT_DIR"

source /opt/ros/humble/setup.bash

echo ">>> Launch GLIM in background (headless — standard_viewer must be disabled in config_ros.json; config_path=${CONFIG_PATH:-default})"
if [ -n "$CONFIG_PATH" ]; then
  ros2 run glim_ros glim_rosnode --ros-args -p config_path:="$CONFIG_PATH" &
else
  ros2 run glim_ros glim_rosnode &
fi
GLIM_PID=$!
sleep 8

echo ">>> Recording odometry"
ros2 bag record -o "$OUT_DIR/glim_odom" /glim_ros/odom_corrected /glim_ros/odom &
REC_PID=$!
sleep 1

echo ">>> Playing bag"
ros2 bag play "$BAG"
sleep 5

kill "$REC_PID" 2>/dev/null || true
kill "$GLIM_PID" 2>/dev/null || true
sleep 2

echo ">>> Converting to TUM"
evo_traj bag2 "$OUT_DIR/glim_odom" /glim_ros/odom_corrected --save_as_tum 2>/dev/null && \
  mv glim_ros_odom_corrected.tum "$OUT_DIR/glim_mid360.tum" || \
  echo "!! Check topic name — may differ from /glim_ros/odom_corrected"

echo ">>> Done: $OUT_DIR"
