#!/usr/bin/env python3
"""
Trim DLIO TUM trajectory to remove startup IMU calibration poses.

DLIO performs a ~3 second IMU calibration at startup where it publishes
poses at the origin (0,0,0). These inflate APE metrics significantly.
This script removes zero-position poses and the first N seconds after
the first valid pose.

Usage:
    python3 trim_dlio.py <input.tum> [--out output.tum] [--trim 3.0]
"""
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default=None)
    ap.add_argument("--trim", type=float, default=3.0,
                    help="seconds to trim after first valid pose")
    args = ap.parse_args()

    out = args.out or args.input.replace(".tum", "_trimmed.tum")
    lines = open(args.input).readlines()
    n_orig = len(lines)

    # step 1: strip zero-position poses (calibration period)
    lines = [l for l in lines if
             abs(float(l.split()[1])) > 0.01 or
             abs(float(l.split()[2])) > 0.01 or
             abs(float(l.split()[3])) > 0.01]

    # step 2: trim first N seconds after first valid pose
    if lines:
        t_start = float(lines[0].split()[0])
        lines = [l for l in lines
                 if float(l.split()[0]) >= t_start + args.trim]

    with open(out, 'w') as f:
        f.writelines(lines)

    print(f"Trimmed {n_orig} -> {len(lines)} poses")
    print(f"Saved to: {out}")

if __name__ == "__main__":
    main()
