#!/usr/bin/env python3
"""
Trim the first N seconds of a TUM trajectory file, relative to its own
first timestamp. Unlike trim_dlio.py (which strips zero-position startup
calibration poses), this is a plain time-based trim — used when the
platform itself was stationary for a few seconds before motion started
(e.g. drone on the ground before takeoff), so every trajectory (ground
truth and all method outputs) needs the same startup window removed
before evaluation.

Usage:
    python3 trim_startup.py <input.tum> [--out output.tum] [--trim 3.5]
"""
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default=None)
    ap.add_argument("--trim", type=float, default=3.5,
                     help="seconds to trim from the start")
    args = ap.parse_args()

    out = args.out or args.input.replace(".tum", "_trimmed.tum")
    lines = [l for l in open(args.input) if l.strip()]
    n_orig = len(lines)

    if lines:
        t_start = float(lines[0].split()[0])
        lines = [l for l in lines if float(l.split()[0]) >= t_start + args.trim]

    with open(out, 'w') as f:
        f.writelines(lines)

    print(f"Trimmed {n_orig} -> {len(lines)} poses (removed first {args.trim}s)")
    print(f"Saved to: {out}")

if __name__ == "__main__":
    main()
