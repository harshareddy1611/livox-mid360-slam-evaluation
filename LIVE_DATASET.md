# Live Drone Dataset (Livox Mid-360 + Pixhawk)

In addition to the offline TIERS benchmark (see [`README.md`](README.md)), this
repo evaluates the same four methods on **live recordings from an actual UAV
platform**: a Livox Mid-360 mounted alongside a Pixhawk flight controller,
flown inside a VICON-tracked indoor arena. Unlike the TIERS runs, all four
methods here — including **GLIM in GPU mode** — run directly on the Jetson
Orin NX, the platform's actual target hardware.

## Results

APE RMSE (translation, meters) across 7 clean sequences:

<!-- TODO: fill in once scripts/run_drone_batch.sh completes -->

| Method | batch1_00 | batch1_07 | batch2_01 | batch2_02 | batch2_03 | batch2_04 | batch2_05 | Average |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| KISS-ICP | | | | | | | | |
| DLIO | | | | | | | | |
| FAST-LIO2 | | | | | | | | |
| GLIM (GPU) | | | | | | | | |

## Environment

| | |
|:---:|:---:|
| ![](docs/images/batch2_env_1.jpg) | ![](docs/images/batch2_env_2.jpg) |

Indoor VICON-tracked arena with an obstacle course (rope-frame gates, cones,
a wooden pallet, stacked boxes) — ceiling-mounted VICON cameras visible on
the truss.

## Map reconstruction

<!-- TODO: point cloud map render(s) vs. environment photo, once map export
     is set up (FAST-LIO2's pcd_save_en output and/or GLIM's /tmp/dump map) -->

## Dataset

Two recording sessions, 7 sequences total, flown in the same indoor
VICON-tracked arena:

| Sequence | Duration |
|----------|:---:|
| batch1_00 | 78.0 s |
| batch1_07 | 64.5 s |
| batch2_01 | 72.3 s |
| batch2_02 | 76.0 s |
| batch2_03 | 62.2 s |
| batch2_04 | 41.8 s |
| batch2_05 | 59.5 s |

All sequences publish `/livox/lidar` (10 Hz, same per-point timestamp fields
as the Mid-360 TIERS data) and `/livox/imu` (200 Hz nominal).

**Ground truth**: `/mavros/local_position/pose` — the Pixhawk EKF's fusion of
VICON pose with onboard IMU/barometer, ~30 Hz. An alternative topic,
`/vicon/drone/drone/pose`, gives pure unfused VICON at ~120 Hz for
cross-checking.

**Startup trim**: the drone sat stationary on the ground for the first ~3.5s
of every recording before takeoff. This period is trimmed from ground truth
and every method's output before evaluation via `scripts/trim_startup.py` —
a plain time-based trim, distinct from `trim_dlio.py`'s zero-position
calibration-artifact trim used for the TIERS dataset.

## Reproducing

```bash
# batch run: all 7 clean sequences x all 4 methods, with GT extraction,
# startup trimming, and evo evaluation
bash scripts/run_drone_batch.sh
```

Or per-method, with the drone dataset's topics/configs:

```bash
python3 scripts/extract_gt.py <bag> --topic /mavros/local_position/pose --out gt_raw.tum
python3 scripts/trim_startup.py gt_raw.tum --out gt.tum --trim 3.5

bash scripts/run_kiss_icp.sh  <bag> /livox/lidar
bash scripts/run_fastlio2.sh  <bag> drone.yaml
bash scripts/run_dlio.sh      <bag> /livox/lidar /livox/imu
bash scripts/run_glim.sh      <bag> configs/glim/config_drone
```

## Platform

Jetson Orin NX (JetPack 6.2, CUDA 12.6), Ubuntu 22.04, ROS 2 Humble,
Livox Mid-360 + Pixhawk — GLIM runs in GPU mode.

## Author

Harsha Reddy
