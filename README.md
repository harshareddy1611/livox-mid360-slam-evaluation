# Livox Mid-360 SLAM Evaluation

Benchmarking LiDAR and LiDAR-inertial odometry/SLAM methods on the
[TIERS LiDAR dataset](https://github.com/TIERS/tiers-lidars-dataset),
evaluated against motion-capture ground truth. Targets a **Jetson Orin NX +
Livox Mid-360** UAV navigation platform.

## Results

APE (translation) on `IndoorOffice1`, Mid-360, vs OptiTrack/VRPN ground truth:

| Method | Type | APE RMSE (m) | Mean (m) | Max (m) |
|--------|------|:---:|:---:|:---:|
| KISS-ICP | LiDAR-only odometry | 0.124 | 0.102 | 0.266 |
| FAST-LIO2 | LiDAR-inertial (iEKF) | **0.060** | 0.053 | 0.140 |
| GLIM | LiDAR-inertial SLAM | _pending_ | – | – |

FAST-LIO2's IMU fusion roughly halves KISS-ICP's error.
GLIM (factor-graph + loop closure) result being added.

## Trajectory plots

| KISS-ICP | FAST-LIO2 |
|:---:|:---:|
| ![](results/kiss_icp/ape_map.png) | ![](results/fastlio2/ape_map.png) |

## Dataset

`IndoorOffice1` from the TIERS dataset: Unitree B1 quadruped with Livox Avia,
Mid-360, and Ouster LiDARs + IMUs, with OptiTrack motion capture (VRPN).
This study uses the **Mid-360** streams.

| Topic | Type | Role |
|-------|------|------|
| `/mid360/livox/lidar` | PointCloud2 | LiDAR input |
| `/mid360/livox/imu` | Imu | IMU input |
| `/vrpn_client_node/unitree_b1/pose` | PoseStamped | Ground truth |

See [`data/README.md`](data/README.md) for download + conversion steps.

## Methods

- **[KISS-ICP](https://github.com/PRBonn/kiss-icp)** — LiDAR-only odometry. Baseline.
- **[FAST-LIO2](https://github.com/Ericsii/FAST_LIO_ROS2)** — tightly-coupled
  LiDAR-inertial odometry (iterated EKF).
- **[GLIM](https://github.com/koide3/glim)** — LiDAR-inertial SLAM with
  factor-graph optimization and loop closure.

## Reproducing

```bash
pip install kiss-icp evo rosbags

python3 scripts/extract_gt.py <bag> --out results/gt_mid360.tum
bash scripts/run_kiss_icp.sh <bag>
bash scripts/run_fastlio2.sh <bag>
bash scripts/run_glim.sh <bag>
bash scripts/evaluate.sh
```

See [`docs/setup.md`](docs/setup.md) for build instructions and
[`docs/workflow.md`](docs/workflow.md) for the conceptual walkthrough.

## Evaluation notes

- Per-point timestamps were lost in the initial ROS1→ROS2 conversion;
  reconverting with `rosbags-convert` recovered them (see `data/README.md`).
- Mocap and LiDAR streams have a clock offset; handled per method in
  `scripts/evaluate.sh`.

## Platform

Dev: Ubuntu 22.04, ROS 2 Humble, x86\_64.
Target: Jetson Orin NX, Ubuntu 22.04, ROS 2 Humble, Livox Mid-360.

## Author

Harsha Reddy
