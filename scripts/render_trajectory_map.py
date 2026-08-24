"""
Build a top-down point-cloud map by transforming raw LiDAR scans into world
frame using a method's own estimated trajectory (TUM file), then rendering
a 2D scatter plot. Works identically for any method since it only needs the
method's TUM poses -- no dependency on method-specific map topics/exports.
"""
import sys
import argparse
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation, Slerp


def load_tum(path):
    rows = []
    for line in open(path):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [float(x) for x in line.split()]
        rows.append(parts)
    arr = np.array(rows)
    return arr[:, 0], arr[:, 1:4], arr[:, 4:8]  # t, xyz, quat(xyzw)


def build_pose_lookup(times, xyz, quat):
    # Some methods (e.g. DLIO's IMU-calibration startup) emit repeated/
    # non-increasing timestamps; Slerp requires strictly increasing times.
    times, uniq_idx = np.unique(times, return_index=True)
    xyz = xyz[uniq_idx]
    quat = quat[uniq_idx]
    rot = Rotation.from_quat(quat)
    slerp = Slerp(times, rot)
    t_min, t_max = times[0], times[-1]

    def lookup(t):
        tc = min(max(t, t_min), t_max)
        idx = np.searchsorted(times, tc)
        idx = min(max(idx, 1), len(times) - 1)
        t0, t1 = times[idx - 1], times[idx]
        p0, p1 = xyz[idx - 1], xyz[idx]
        alpha = 0.0 if t1 == t0 else (tc - t0) / (t1 - t0)
        pos = p0 + alpha * (p1 - p0)
        r = slerp([tc])[0]
        return pos, r.as_matrix()

    return lookup


def read_pointcloud2_xyz(msg, stride=4):
    fields = {f.name: f for f in msg.fields}
    point_step = msg.point_step
    n_points = msg.width * msg.height
    data = np.frombuffer(bytes(msg.data), dtype=np.uint8).reshape(n_points, point_step)
    x_off, y_off, z_off = fields['x'].offset, fields['y'].offset, fields['z'].offset
    xs = data[:, x_off:x_off + 4].copy().view(np.float32).ravel()
    ys = data[:, y_off:y_off + 4].copy().view(np.float32).ravel()
    zs = data[:, z_off:z_off + 4].copy().view(np.float32).ravel()
    pts = np.stack([xs, ys, zs], axis=1)
    pts = pts[::stride]
    # drop invalid/degenerate points
    finite = np.isfinite(pts).all(axis=1)
    pts = pts[finite]
    dist = np.linalg.norm(pts, axis=1)
    pts = pts[(dist > 0.1) & (dist < 60.0)]
    return pts


def robust_crop(pts, k=10.0, pad=1.0):
    """Drop sparse far-range outlier points (e.g. reflections through
    windows/doors) using a median/MAD bound per axis, keeping the dense
    room-scale cluster centered instead of stretching the plot to include
    a thin trail of stray points."""
    keep = np.ones(len(pts), dtype=bool)
    for axis in (0, 1):
        vals = pts[:, axis]
        med = np.median(vals)
        mad = np.median(np.abs(vals - med)) + 1e-6
        lo, hi = med - k * mad, med + k * mad
        keep &= (vals >= lo - pad) & (vals <= hi + pad)
    return pts[keep]


def voxel_downsample(pts, voxel_size):
    if len(pts) == 0:
        return pts
    keys = np.floor(pts / voxel_size).astype(np.int64)
    _, idx = np.unique(keys, axis=0, return_index=True)
    return pts[idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bag")
    ap.add_argument("lidar_topic")
    ap.add_argument("tum")
    ap.add_argument("out_png")
    ap.add_argument("--title", default="")
    ap.add_argument("--stride", type=int, default=4, help="keep 1/N points per scan")
    ap.add_argument("--voxel", type=float, default=0.08)
    ap.add_argument("--time-offset", type=float, default=0.0,
                     help="seconds to add to lidar msg timestamps to align with tum clock")
    args = ap.parse_args()

    from rosbags.highlevel import AnyReader
    from rosbags.typesys import Stores, get_typestore

    times, xyz, quat = load_tum(args.tum)
    lookup = build_pose_lookup(times, xyz, quat)

    typestore = get_typestore(Stores.ROS2_HUMBLE)
    all_pts = []
    n_scans = 0
    with AnyReader([Path(args.bag)], default_typestore=typestore) as reader:
        conns = [c for c in reader.connections if c.topic == args.lidar_topic]
        for conn, timestamp, rawdata in reader.messages(connections=conns):
            msg = reader.deserialize(rawdata, conn.msgtype)
            t = timestamp * 1e-9 + args.time_offset
            pos, R = lookup(t)
            pts = read_pointcloud2_xyz(msg, stride=args.stride)
            if len(pts) == 0:
                continue
            world_pts = pts @ R.T + pos
            all_pts.append(world_pts)
            n_scans += 1
            if n_scans % 50 == 0:
                merged = np.concatenate(all_pts, axis=0)
                all_pts = [voxel_downsample(merged, args.voxel)]

    if not all_pts:
        print("No points accumulated!")
        sys.exit(1)

    pts = np.concatenate(all_pts, axis=0)
    pts = voxel_downsample(pts, args.voxel)
    pts = robust_crop(pts)
    print(f"scans={n_scans} final_points={len(pts)}")

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6.5))
    sc = ax.scatter(pts[:, 0], pts[:, 1], c=pts[:, 2], s=0.15, cmap='viridis', linewidths=0)
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title(args.title or Path(args.bag).name)
    ax.set_aspect('equal')
    # Center the view on the data with a small margin, instead of letting
    # matplotlib autoscale to include any remaining sparse stray points.
    margin = 0.5
    ax.set_xlim(pts[:, 0].min() - margin, pts[:, 0].max() + margin)
    ax.set_ylim(pts[:, 1].min() - margin, pts[:, 1].max() + margin)
    plt.colorbar(sc, label='Height (m)', shrink=0.8)
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=140, facecolor='white')
    print(f"Saved {args.out_png}")


if __name__ == "__main__":
    main()
