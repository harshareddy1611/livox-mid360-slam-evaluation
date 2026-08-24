#!/usr/bin/env bash
# Batch-run all 4 methods on all clean drone-dataset sequences and evaluate.
# Usage: bash scripts/run_drone_batch.sh
set -o pipefail  # no -u/-e: ROS2 setup.bash references unset vars, and we want to continue past per-method failures

REPO="$HOME/livox-mid360-slam-evaluation"
GLIM_CFG="$REPO/configs/glim/config_drone"
GT_TOPIC="/mavros/local_position/pose"
LIDAR_TOPIC="/livox/lidar"
IMU_TOPIC="/livox/imu"
TRIM=3.5
TMAXDIFF=0.05

DATA="$HOME/Downloads/drone_dataset"
declare -A datasets=(
  [batch1_00]="$DATA/batch1/lidar_dataset_00"
  [batch1_07]="$DATA/batch1/lidar_dataset_07"
  [batch2_01]="$DATA/batch2/lidar_dataset_21_08_26_01"
  [batch2_02]="$DATA/batch2/lidar_dataset_21_08_26_02"
  [batch2_03]="$DATA/batch2/lidar_dataset_21_08_26_03"
  [batch2_04]="$DATA/batch2/lidar_dataset_21_08_26_04"
  [batch2_05]="$DATA/batch2/lidar_dataset_21_08_26_05"
)

cd "$REPO"
source /opt/ros/humble/setup.bash
source "$HOME/Documents/ws_livox/install/setup.bash" 2>/dev/null || true
source "$HOME/FAST_LIO/install/setup.bash" 2>/dev/null || true
source "$HOME/slam_ws/install/setup.bash" 2>/dev/null || true
export PATH="$HOME/.local/bin:$PATH"

for name in "${!datasets[@]}"; do
  bag="${datasets[$name]}"
  OUT="$REPO/results/drone/$name"
  mkdir -p "$OUT"
  echo "=========================================="
  echo "=== $name ($bag) ==="
  echo "=========================================="

  echo ">>> GT extraction"
  python3 scripts/extract_gt.py "$bag" --topic "$GT_TOPIC" --out "$OUT/gt_raw.tum"
  python3 scripts/trim_startup.py "$OUT/gt_raw.tum" --out "$OUT/gt.tum" --trim $TRIM

  echo ">>> KISS-ICP"
  mkdir -p "$OUT/kiss_icp"
  bash scripts/run_kiss_icp.sh "$bag" "$LIDAR_TOPIC" "$OUT/kiss_icp"
  [ -f "$OUT/kiss_icp/kiss_icp_mid360.tum" ] && \
    python3 scripts/trim_startup.py "$OUT/kiss_icp/kiss_icp_mid360.tum" --out "$OUT/kiss_icp/trimmed.tum" --trim $TRIM

  echo ">>> FAST-LIO2"
  bash scripts/run_fastlio2.sh "$bag" drone.yaml "$OUT/fastlio2"
  [ -f "$OUT/fastlio2/fastlio2_mid360.tum" ] && \
    python3 scripts/trim_startup.py "$OUT/fastlio2/fastlio2_mid360.tum" --out "$OUT/fastlio2/trimmed.tum" --trim $TRIM

  echo ">>> DLIO"
  bash scripts/run_dlio.sh "$bag" "$LIDAR_TOPIC" "$IMU_TOPIC" "$OUT/dlio"
  [ -f "$OUT/dlio/dlio_mid360.tum" ] && \
    python3 scripts/trim_startup.py "$OUT/dlio/dlio_mid360.tum" --out "$OUT/dlio/trimmed.tum" --trim $TRIM

  echo ">>> GLIM"
  bash scripts/run_glim.sh "$bag" "$GLIM_CFG" "$OUT/glim"
  [ -f "$OUT/glim/glim_mid360.tum" ] && \
    python3 scripts/trim_startup.py "$OUT/glim/glim_mid360.tum" --out "$OUT/glim/trimmed.tum" --trim $TRIM

  echo ">>> Evaluation"
  for m in kiss_icp fastlio2 dlio glim; do
    f="$OUT/$m/trimmed.tum"
    if [ -f "$f" ]; then
      evo_ape tum "$OUT/gt.tum" "$f" --align --t_max_diff $TMAXDIFF \
        --save_results "$OUT/ape_${m}.zip" --plot_mode xy --save_plot "$OUT/ape_${m}.png" \
        || echo "!! evo_ape failed for $m on $name"
      evo_rpe tum "$OUT/gt.tum" "$f" --align --t_max_diff $TMAXDIFF \
        --save_results "$OUT/rpe_${m}.zip" \
        || echo "!! evo_rpe failed for $m on $name"
    else
      echo "!! Missing $f, skipping eval for $m on $name"
    fi
  done

  if ls "$OUT"/ape_*.zip >/dev/null 2>&1; then
    evo_res "$OUT"/ape_*.zip --save_table "$OUT/ape_comparison.csv" --save_plot "$OUT/ape_comparison.png" \
      || echo "!! evo_res comparison failed for $name"
  fi

  echo ">>> Done: $name"
done

echo "ALL DATASETS COMPLETE"
