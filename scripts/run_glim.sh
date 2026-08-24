#!/usr/bin/env bash
# Run GLIM on Mid-360 sequence and capture TUM trajectory.
# Records /glim_ros/odom_corrected (post loop-closure, globally optimized) —
# this is GLIM's actual value-add over plain odometry, use it for evaluation.
set -eo pipefail  # no -u: ROS2 setup.bash references unset vars internally

BAG="${1:-$HOME/Downloads/IndoorOffice1_ros2_v2}"
CONFIG_PATH="${2:-}"
OUT_DIR="${3:-results/indooroffice1/glim}"
[ "$BAG" = *"IndoorOffice2"* ] && OUT_DIR="results/indooroffice2/glim"
[ "$BAG" = *"OutdoorRoad"* ] && OUT_DIR="results/outdoorroad/glim"
mkdir -p "$OUT_DIR"

source /opt/ros/humble/setup.bash
export PATH="$HOME/.local/bin:$PATH"  # pip-installed evo_traj etc.

# The old ~/glim_ws build was chained as an underlay into other workspaces
# (e.g. FAST_LIO/install/setup.bash) at build time, so sourcing them puts
# glim_ws ahead of /opt/ros/humble in AMENT_PREFIX_PATH and `ros2 run`
# silently resolves glim_ros to the stale CPU-only build instead of the
# PPA GPU package. Strip it out so the PPA package always wins.
export AMENT_PREFIX_PATH="$(echo "$AMENT_PREFIX_PATH" | tr ':' '\n' | grep -v '/glim_ws/' | paste -sd: -)"

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

# GLIM runs slower than real-time on this hardware, so it's still working
# through its backlog when playback ends. A fixed sleep here silently
# truncates the trajectory to whatever GLIM happened to reach — wait until
# its output topic actually goes idle (no new message for 6s) instead.
echo ">>> Waiting for GLIM to drain its processing backlog"
python3 "$(dirname "$0")/wait_for_topic_drain.py" /glim_ros/odom_corrected \
  --msg-type nav_msgs/msg/Odometry --idle 6 --max-wait 600

kill "$REC_PID" 2>/dev/null || true
kill "$GLIM_PID" 2>/dev/null || true
# ros2 run's glim_rosnode PID may not be the actual node process; make sure
# it's actually gone before moving to the next dataset.
pkill -f '[g]lim_rosnode' 2>/dev/null || true
sleep 2

echo ">>> Converting to TUM"
evo_traj bag2 "$OUT_DIR/glim_odom" /glim_ros/odom_corrected --save_as_tum 2>/dev/null && \
  mv glim_ros_odom_corrected.tum "$OUT_DIR/glim_mid360.tum" || \
  echo "!! Check topic name — may differ from /glim_ros/odom_corrected"

echo ">>> Done: $OUT_DIR"
