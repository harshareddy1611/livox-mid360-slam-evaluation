#!/usr/bin/env bash
# Run DLIO on Mid-360 sequence and capture TUM trajectory.
set -euo pipefail

BAG="${1:-$HOME/Downloads/IndoorOffice1_ros2_v2}"
OUT_DIR="results/indooroffice1/dlio"
[ "$BAG" = *"IndoorOffice2"* ] && OUT_DIR="results/indooroffice2/dlio"
[ "$BAG" = *"OutdoorRoad"* ] && OUT_DIR="results/outdoorroad/dlio"
mkdir -p "$OUT_DIR"

source /opt/ros/humble/setup.bash
source "$HOME/slam_ws/install/setup.bash"

echo ">>> Launch DLIO in background"
ros2 launch direct_lidar_inertial_odometry dlio.launch.py \
  pointcloud_topic:=/mid360/livox/lidar \
  imu_topic:=/mid360/livox/imu \
  rviz:=false \
  params_filepath:="$HOME/lidar-uav-nav/configs/dlio/mid360.yaml" &
DLIO_PID=$!
sleep 5

echo ">>> Recording odometry"
ros2 bag record -o "$OUT_DIR/dlio_odom" /dlio/odom_node/odom &
REC_PID=$!
sleep 1

echo ">>> Playing bag"
ros2 bag play "$BAG"
sleep 3

kill "$REC_PID" 2>/dev/null || true
kill "$DLIO_PID" 2>/dev/null || true
sleep 2

echo ">>> Converting to TUM"
evo_traj bag2 "$OUT_DIR/dlio_odom" /dlio/odom_node/odom --save_as_tum 2>/dev/null && \
  mv dlio_odom_node_odom.tum "$OUT_DIR/dlio_mid360.tum" || \
  echo "!! Check topic name — may differ from /dlio/odom_node/odom"

echo ">>> Done: $OUT_DIR"
