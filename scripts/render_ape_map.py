"""
Render an evo-style "ape_map" plot (trajectory colored by per-pose APE
error) using evo's core alignment/metrics API directly, bypassing evo's
own plotting module -- which unconditionally imports mpl_toolkits.mplot3d
and crashes on this system (matplotlib/mpl_toolkits version conflict).
"""
import argparse

from evo.core import sync, metrics
from evo.tools import file_interface


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gt_tum")
    ap.add_argument("est_tum")
    ap.add_argument("out_png")
    ap.add_argument("--title", default="")
    ap.add_argument("--max-diff", type=float, default=0.05)
    args = ap.parse_args()

    traj_ref = file_interface.read_tum_trajectory_file(args.gt_tum)
    traj_est = file_interface.read_tum_trajectory_file(args.est_tum)

    traj_ref, traj_est = sync.associate_trajectories(traj_ref, traj_est, max_diff=args.max_diff)

    ape_metric = metrics.APE(metrics.PoseRelation.translation_part)
    data = (traj_ref, traj_est)
    ape_metric.process_data(data)

    # process_data internally aligns traj_est to traj_ref (SE3, no scale)
    # and stores the aligned trajectory back onto traj_est's positions via
    # metrics.APE -- but to get the aligned positions for plotting we align
    # explicitly the same way evo's main.py does before calling APE.
    import copy
    from evo.core import trajectory
    traj_est_aligned = copy.deepcopy(traj_est)
    traj_est_aligned.align(traj_ref, correct_scale=False)

    ape_metric2 = metrics.APE(metrics.PoseRelation.translation_part)
    ape_metric2.process_data((traj_ref, traj_est_aligned))
    errors = ape_metric2.error
    rmse = ape_metric2.get_statistic(metrics.StatisticsType.rmse)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    ref_xy = traj_ref.positions_xyz[:, :2]
    est_xy = traj_est_aligned.positions_xyz[:, :2]

    fig, ax = plt.subplots(figsize=(6, 5.5))
    ax.plot(ref_xy[:, 0], ref_xy[:, 1], '--', color='gray', linewidth=1, label='ground truth', zorder=1)
    sc = ax.scatter(est_xy[:, 0], est_xy[:, 1], c=errors, cmap='jet', s=6, zorder=2)
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_aspect('equal')
    ax.legend(loc='best', fontsize=8)
    title = args.title or f"APE RMSE: {rmse:.3f}m"
    ax.set_title(title)
    plt.colorbar(sc, label='APE (m)', shrink=0.85)
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=140, facecolor='white')
    print(f"rmse={rmse:.4f} Saved {args.out_png}")


if __name__ == "__main__":
    main()
