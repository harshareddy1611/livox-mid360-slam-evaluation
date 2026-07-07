# Livox Mid-360 SLAM Evaluation

Benchmarking LiDAR and LiDAR-inertial odometry/SLAM methods on the
[TIERS LiDAR dataset](https://github.com/TIERS/tiers-lidars-dataset),
evaluated against motion-capture ground truth. Targets a **Jetson Orin NX +
Livox Mid-360** UAV navigation platform.

## Results

APE (translation) on `IndoorOffice1`, Mid-360, vs OptiTrack/VRPN ground truth
(SE(3) Umeyama alignment):

| Method | Type | APE RMSE (m) | Mean (m) | Median (m) | Max (m) |
|--------|------|:---:|:---:|:---:|:---:|
| KISS-ICP | LiDAR-only odometry | 0.124 | 0.102 | 0.099 | 0.266 |
| FAST-LIO2 | LiDAR-inertial (iEKF) | 0.060 | 0.053 | 0.053 | 0.140 |
| **GLIM** | **LiDAR-inertial SLAM** | **0.025** | **0.023** | **0.021** | **0.101** |

GLIM's factor-graph optimization with loop closure achieves **5× lower error**
than LiDAR-only KISS-ICP. IMU fusion (FAST-LIO2) halves the LiDAR-only error.
GLIM's full SLAM pipeline further halves FAST-LIO2's error.

## Trajectory comparison

![All methods vs ground truth](results/comparison/all_methods_xy_trajectories.png)

| KISS-ICP | FAST-LIO2 | GLIM |
|:---:|:---:|:---:|
| ![](results/kiss_icp/ape_map.png) | ![](results/fastlio2/ape_map.png) | ![](results/glim/ape_map.png) |

## Dataset

`IndoorOffice1` from the TIERS dataset: Unitree B1 quadruped with Livox Avia,
Mid-360, and Ouster LiDARs + IMUs, with OptiTrack motion capture (VRPN).
This study uses the **Mid-360** streams to match the target UAV hardware.

| Topic | Type | Role |
|-------|------|------|
| `/mid360/livox/lidar` | PointCloud2 | LiDAR input |
| `/mid360/livox/imu` | Imu | IMU input |
| `/vrpn_client_node/unitree_b1/pose` | PoseStamped | Ground truth |

See [`data/README.md`](data/README.md) for download and conversion steps.

## Methods

- **[KISS-ICP](https://github.com/PRBonn/kiss-icp)** — point-to-point ICP
  odometry, LiDAR-only, no IMU. Robust baseline.
- **[FAST-LIO2](https://github.com/Ericsii/FAST_LIO_ROS2)** — tightly-coupled
  LiDAR-inertial odometry via an iterated error-state Kalman filter.
- **[GLIM](https://github.com/koide3/glim)** — LiDAR-inertial SLAM with
  GPU-accelerated factor-graph optimization and loop closure (CPU build on
  dev machine; GPU on Orin NX).

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

- **Point timestamps:** initial ROS1→ROS2 conversion dropped per-point
  `timestamp` and `line` fields; reconverting with `rosbags-convert` recovered
  them, enabling motion compensation in all three methods.
- **Clock alignment:** mocap and LiDAR streams use different time bases;
  handled per-method in evaluation (KISS-ICP needs explicit offset;
  FAST-LIO2 and GLIM carry correct header stamps).
- **GLIM on CPU:** dev machine has Intel iGPU only; GLIM runs CPU mode
  (`-DBUILD_WITH_CUDA=OFF`). Orin NX target uses GPU mode for real-time
  operation.

## Platform

Dev: Ubuntu 22.04, ROS 2 Humble, x86\_64 (Intel iGPU).
Target: Jetson Orin NX, Ubuntu 22.04, ROS 2 Humble, Livox Mid-360.

## Author

Harsha Reddy
