# Workflow: what's actually happening

This document explains the pipeline conceptually so the configs and scripts make sense.

---

## 1. The pipeline

```
dataset (rosbag2)
       |
       v
[method: KISS-ICP / FAST-LIO2 / GLIM]
       |
       v
estimated trajectory (TUM format)
    timestamp tx ty tz qx qy qz qw
       |
       v
evo: align to ground truth -> APE / RPE metrics + plots
```

---

## 2. The three methods

### KISS-ICP
LiDAR-only odometry. Point-to-point ICP against a local voxel map with
adaptive thresholding and constant-velocity motion deskew. No IMU, no
extrinsics needed. Runs offline directly on the bag via CLI. This is the
baseline — it shows what you get with zero IMU fusion.

### FAST-LIO2
Tightly-coupled LiDAR-inertial odometry via an iterated error-state Kalman
filter (iEKF). The IMU propagates the state estimate at high frequency
(~200 Hz); each LiDAR scan (10 Hz) corrects it. Needs the LiDAR-to-IMU
extrinsic transform. Fast, drift-resistant, no loop closure — pure odometry.
The `extrinsic_est_en: true` setting lets the filter refine the extrinsic
online, which is safer than hardcoding an imprecise value.

### GLIM
Full LiDAR-inertial SLAM with a factor-graph back-end, loop closure, and
global optimization. Each scan contributes a factor; loop closures add
constraints between non-adjacent poses, correcting accumulated drift. This
is what makes it more accurate than FAST-LIO2 indoors — when the robot
revisits a place, GLIM detects it and snaps the trajectory together. On the
Orin NX with GPU, this runs in real time. On the dev PC (CPU only), global
mapping can lag on longer sequences.

---

## 3. Sensor topics (Mid-360)

| Topic | Type | Rate | Role |
|-------|------|------|------|
| `/mid360/livox/lidar` | PointCloud2 | 10 Hz | LiDAR input |
| `/mid360/livox/imu` | Imu | ~200 Hz | IMU (6-axis: accel + gyro) |
| `/vrpn_client_node/unitree_b1/pose` | PoseStamped | ~115 Hz | Indoor mocap GT |
| `/gnss_pose` | PoseStamped | 100 Hz | Outdoor GNSS-RTK GT (lat/lon/alt) |

The Mid-360 publishes standard `sensor_msgs/PointCloud2`, not Livox's custom
`CustomMsg` format. This is important: methods that only support `CustomMsg`
(e.g. the original Point-LIO) will not work with the TIERS dataset directly.

---

## 4. Parameters that actually matter

| Parameter | Where | What it controls |
|-----------|-------|-----------------|
| `lid_topic` / `pointCloudTopic` | all configs | must match bag topic |
| `imu_topic` | fastlio2, glim | IMU stream for state propagation |
| `lidar_type: 4` | fastlio2 | generic PointCloud2 handler (not Livox CustomMsg) |
| `timestamp_unit: 3` | fastlio2 | per-point time field is in nanoseconds |
| `blind: 0.5` | all | minimum range — rejects returns off the robot body |
| `extrinsicTrans` / `T_lidar_imu` | fastlio2, glim | LiDAR frame w.r.t. IMU frame |
| `extrinsic_est_en: true` | fastlio2 | online refinement of the extrinsic |
| `fov_degree: 360` | fastlio2 | Mid-360 is full 360-degree horizontal |
| `enable_global_mapping` | glim config_ros.json | enables loop closure |
| `BUILD_WITH_CUDA` | glim cmake | OFF on PC, ON on Orin NX |

The Mid-360 internal IMU extrinsic (used across all LIO methods):

```yaml
extrinsicTrans: [-0.011, -0.02329, 0.04412]   # meters
extrinsicRot:   identity (3x3)                  # near-zero rotation
```

---

## 5. Dataset-specific issues resolved

### Per-point timestamps
The original ROS1 bag was converted to ROS2 using a tool that dropped the
Livox-specific point fields (`line`, `timestamp`). Without `timestamp`, motion
compensation (deskew) is impossible. Fix: reconvert the ROS1 bag using
`rosbags-convert`, which preserves all fields.

Final field layout: `x y z intensity(f32) tag(u8) line(u8) timestamp(f64)`

The `timestamp` field is absolute float64 seconds (Unix-style), not a small
per-scan offset. FAST-LIO2 config uses `timestamp_unit: 3` (ns) which works
with the type-4 generic PointCloud2 handler in the Ericsii fork.

### Metadata fix
`rosbags-convert` writes `offered_qos_profiles: []` (a YAML sequence) but
ROS2 Humble's yaml-cpp parser expects a string. Fix:

```bash
sed -i 's/offered_qos_profiles: \[\]/offered_qos_profiles: ""/' metadata.yaml
```

### Indoor clock offset
The mocap system and the LiDAR recorder ran on different clocks (~21 hours
apart). KISS-ICP outputs timestamps on the bag's record clock; FAST-LIO2
and GLIM output timestamps on the LiDAR header clock (which matches the
mocap clock). Handle in evo with `--t_offset` for KISS-ICP, or `--t_max_diff`
for small mismatches with FAST-LIO2/GLIM.

### Outdoor GNSS coordinates
The `/gnss_pose` topic publishes latitude, longitude, altitude in degrees
(WGS84), not Cartesian meters. evo requires Cartesian coordinates. Convert
to local ENU (East-North-Up) using `scripts/convert_gnss_to_enu.py`, which
treats the first pose as the origin.

---

## 6. Evaluation logic

Ground truth and estimates live in different coordinate frames and use
different time bases. evo handles this:

1. Associates poses by nearest timestamp (`--t_max_diff 0.05`)
2. Aligns estimate to GT with rigid SE(3) Umeyama fit (`--align`)
   — no scale correction, LiDAR odometry is metric
3. Computes APE (global consistency) and RPE (local drift per segment)

**APE RMSE** is the headline metric — lower is better. It captures global
drift and is what gets reported in papers.

**RPE** captures local accuracy — how much error accumulates per meter
traveled. Useful for understanding how quickly each method drifts.

---

## 7. Order of operations

```bash
# 0. convert bag (ROS1 -> ROS2)
rosbags-convert --src <name>.bag --dst <name>_ros2
sed -i 's/offered_qos_profiles: \[\]/offered_qos_profiles: ""/' <name>_ros2/metadata.yaml

# 1. extract ground truth
# indoor:
python3 scripts/extract_gt.py <bag> \
  --topic /vrpn_client_node/unitree_b1/pose \
  --out results/gt.tum

# outdoor (GNSS -> ENU):
python3 scripts/extract_gt.py <bag> \
  --topic /gnss_pose \
  --out results/gt_raw.tum
python3 scripts/convert_gnss_to_enu.py results/gt_raw.tum \
  --out results/gt_enu.tum

# 2. run each method (source workspace first)
source /opt/ros/humble/setup.bash && source ~/slam_ws/install/setup.bash
bash scripts/run_kiss_icp.sh <bag>
bash scripts/run_fastlio2.sh <bag>
bash scripts/run_glim.sh <bag>

# 3. evaluate
bash scripts/evaluate.sh
```

---

## 8. What the results tell you

**KISS-ICP vs FAST-LIO2**: the gap quantifies the value of IMU fusion.
Indoors with fast motion, FAST-LIO2 is ~2x more accurate. Outdoors with
slower motion and rich geometry, the gap nearly disappears.

**FAST-LIO2 vs GLIM**: the gap quantifies the value of loop closure.
Large indoors (robot revisits areas), small outdoors (short sequence,
less revisitation).

**GLIM CPU vs GPU**: the CPU build can lag on longer sequences, causing
loop closures to fire late or miss. On the Orin NX with GPU, global mapping
runs in real time — expected to significantly improve GLIM's outdoor and
longer-sequence results.

---

## 9. Replicating on the Orin NX

This repo is the single source of truth. On the Orin:

```bash
git clone https://github.com/harshareddy1611/livox-mid360-slam-evaluation
cd lidar-uav-nav
```

Rebuild `slam_ws` following `docs/setup.md` with:
- `-DBUILD_WITH_CUDA=ON` for GLIM and gtsam_points
- Same configs from `configs/` — no sensor-specific changes needed

The Orin's real-time performance means GLIM with global mapping will run
properly during live sensor data collection, which is the ultimate goal
of this benchmark.
