#!/usr/bin/env python3
"""Extract mocap PoseStamped ground truth into TUM format.
TUM: timestamp tx ty tz qx qy qz qw
Works with modern rosbags (AnyReader API). Requires: pip install rosbags"""
import argparse
from pathlib import Path
from rosbags.highlevel import AnyReader

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bag")
    ap.add_argument("--topic", default="/vrpn_client_node/unitree_b1/pose")
    ap.add_argument("--out", default="gt_tum.txt")
    args = ap.parse_args()
    n = 0
    with AnyReader([Path(args.bag)]) as reader, open(args.out, "w") as f:
        conns = [c for c in reader.connections if c.topic == args.topic]
        if not conns:
            avail = sorted({c.topic for c in reader.connections})
            raise SystemExit("Topic not found. Available:\n  " + "\n  ".join(avail))
        for conn, _t, raw in reader.messages(connections=conns):
            m = reader.deserialize(raw, conn.msgtype)
            t = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
            p, q = m.pose.position, m.pose.orientation
            f.write(f"{t:.9f} {p.x:.6f} {p.y:.6f} {p.z:.6f} {q.x:.6f} {q.y:.6f} {q.z:.6f} {q.w:.6f}\n")
            n += 1
    print(f"Wrote {n} poses to {args.out}")

if __name__ == "__main__":
    main()
