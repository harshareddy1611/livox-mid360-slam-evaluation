#!/usr/bin/env bash
set -euo pipefail
OUT_DIR="results/mid360"
GT="$OUT_DIR/gt_mid360.tum"
TDIFF=0.02
[ -f "$GT" ] || { echo "!! Missing $GT — run extract_gt.py first"; exit 1; }
for name in kiss_icp fastlio2 glim; do
  f="$OUT_DIR/${name}_mid360.tum"
  [ -f "$f" ] || { echo "-- skip $name (no $f)"; continue; }
  echo "=== $name APE ==="
  evo_ape tum "$GT" "$f" --align --t_max_diff "$TDIFF" \
    --save_results "$OUT_DIR/ape_${name}.zip" \
    --plot_mode xy --save_plot "$OUT_DIR/ape_${name}.png" || true
  echo "=== $name RPE ==="
  evo_rpe tum "$GT" "$f" --align --t_max_diff "$TDIFF" \
    --save_results "$OUT_DIR/rpe_${name}.zip" || true
done
ls "$OUT_DIR"/ape_*.zip >/dev/null 2>&1 && \
  evo_res "$OUT_DIR"/ape_*.zip --save_table "$OUT_DIR/ape_comparison.csv" \
    --save_plot "$OUT_DIR/ape_comparison.png" || true
echo ">>> Results in $OUT_DIR/"
