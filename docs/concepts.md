# Fundamental Concepts in LiDAR-Based Navigation

This document explains the core concepts used in LiDAR-based navigation
systems, grounded in the algorithms evaluated in this project
(KISS-ICP, DLIO, FAST-LIO2, GLIM) on the TIERS Mid-360 dataset.

---

## Localization

Localization is the process of determining the position and orientation
(pose) of a robot within a known or unknown environment. In LiDAR-based
systems, localization is achieved by matching incoming point clouds
against a reference — either a pre-built map (map-based localization)
or an incrementally built local map (odometry-based localization).

In this project, all four methods perform **simultaneous localization**
as part of their odometry pipeline — the robot does not have a prior map,
so it builds and localizes within its own map at the same time.

---

## Mapping

Mapping is the process of building a representation of the environment
from sensor data. In LiDAR-based systems, this typically means
accumulating point clouds into a consistent 3D map. The quality of
the map depends on the accuracy of the pose estimates — a small
localization error leads to misaligned point clouds and a blurry map.

FAST-LIO2 and GLIM both maintain a global point cloud map. KISS-ICP
maintains a local voxel map only. DLIO maintains a keyframe-based map.

---

## SLAM (Simultaneous Localization and Mapping)

SLAM is the problem of building a map of an unknown environment while
simultaneously localizing within it. It is inherently circular: good
localization requires a good map, and a good map requires good
localization. Modern SLAM systems solve this with probabilistic
frameworks (factor graphs, Kalman filters) that jointly optimize
both estimates.

In this project:
- **KISS-ICP and FAST-LIO2** are **odometry** systems, not full SLAM —
  they build a local map and estimate pose but have no global
  consistency mechanism.
- **GLIM** is a full **SLAM** system — it adds loop closure and global
  optimization on top of odometry, correcting accumulated drift when
  the robot revisits a place.

---

## Odometry

Odometry is the estimation of a robot's pose change over time using
sensor measurements. LiDAR odometry estimates motion by matching
consecutive point clouds (scan matching). Inertial odometry uses IMU
measurements to integrate acceleration and angular velocity into a pose
estimate. LiDAR-inertial odometry (LIO) fuses both.

All four methods in this project produce odometry estimates — a
trajectory of poses over time. The key difference is whether they
also perform global optimization (SLAM) or not.

**Drift accumulation** is the fundamental limitation of pure odometry:
small errors in each pose estimate accumulate over time, causing the
trajectory to deviate progressively from ground truth. This is why
APE (absolute pose error) grows with trajectory length in odometry-only
systems, while loop closure in SLAM systems can correct and reset the
accumulated drift.

---

## Local Map vs Global Map

A **local map** contains only the recent surroundings of the robot,
typically within a fixed spatial radius. It is computationally cheap
to maintain and search, but it discards information about places the
robot has already visited. KISS-ICP uses a local voxel map — once
a region is outside the robot's neighborhood, its points are removed.

A **global map** retains all accumulated sensor data across the entire
trajectory. It enables loop closure (recognizing a previously visited
place) but is more expensive to maintain. FAST-LIO2 maintains a global
ikd-tree map; GLIM maintains a global factor graph with keyframes.

The distinction matters for long-term accuracy: local maps accumulate
drift freely, while global maps with loop closure can correct it.

---

## Pose Estimation

Pose estimation is the computation of a 6-DOF pose (3D position +
3D orientation) of the robot at each timestep. In LiDAR systems,
pose estimation is done by scan matching — finding the rigid
transformation that best aligns the current scan with the map.

**FAST-LIO2** estimates pose via an iterated extended Kalman filter
(iEKF), propagating the state with IMU at high frequency and
correcting it with each LiDAR scan.

**KISS-ICP** estimates pose via point-to-point ICP, without any IMU.

**DLIO** estimates pose via a continuous-time formulation that
interpolates the IMU trajectory between scan timestamps, allowing
precise motion compensation.

**GLIM** estimates pose via direct scan-to-map matching factors in
a factor graph, jointly optimized with loop closure constraints.

---

## Point Cloud Processing

A point cloud is a set of 3D points measured by a LiDAR sensor.
Raw point clouds require several processing steps before use in
navigation:

**Deskewing (motion compensation):** During a single scan, the LiDAR
rotates and the robot moves. This means different points in the same
scan were measured from different positions, causing distortion.
Deskewing corrects this by using per-point timestamps and IMU
measurements to transform all points to a common reference time.
In this project, per-point timestamps were lost in the initial
ROS1→ROS2 conversion and had to be recovered via reconversion.

**Downsampling / voxelization:** Point clouds contain millions of
points. Voxel grid downsampling reduces density while preserving
geometric structure, improving computational efficiency. KISS-ICP
uses `voxel_size = 0.5 m`; FAST-LIO2 uses `filter_size_surf = 0.5 m`.

**Range filtering:** Returns too close (robot body) or too far
(noise) are removed. In this project, `min_range = 0.5 m` removes
returns from the Unitree B1's body; `max_range = 60 m` removes
noise at the Mid-360's range limit.

---

## Scan Matching: ICP and NDT

Scan matching finds the rigid transformation (rotation + translation)
that best aligns two point clouds.

**ICP (Iterative Closest Point)** finds correspondences between
nearest-neighbor points and minimizes the sum of squared distances.
It iterates until convergence. KISS-ICP uses point-to-point ICP
with an adaptive threshold. GLIM uses voxelized GICP (Generalized ICP),
which additionally uses surface normal covariances for more robust
matching.

**NDT (Normal Distributions Transform)** subdivides space into voxels
and represents each voxel as a Gaussian distribution of points. Matching
is done by maximizing the likelihood of scan points under these
distributions. NDT is generally more robust to noise than ICP but
heavier computationally.

In this project, all methods use ICP variants. NDT is not used but
is common in autonomous driving applications (e.g., Autoware).

**Convergence and degeneracy:** Scan matching can fail or produce poor
results when the environment is geometrically degenerate — for example,
a long featureless corridor where all surfaces are parallel. In this
case, ICP cannot determine translation along the corridor axis. This
is a known failure mode for all four methods evaluated here.

---

## Trajectory Alignment

Ground truth trajectories (from motion capture or GNSS) and odometry
trajectories live in different coordinate frames with different origins
and orientations. To compute meaningful error metrics, they must be
aligned.

**Umeyama alignment** (SE(3)) finds the optimal rigid transformation
(rotation + translation, no scale) that minimizes the sum of squared
distances between corresponding poses. This is what `evo` uses with
the `--align` flag.

**Scale alignment** additionally estimates a scale factor. We
deliberately do NOT use scale alignment in this project (`evo` uses
`--align` not `--align --correct_scale`). The reason: LiDAR odometry
is a metric system — distances are measured in real meters from the
time-of-flight measurement. There should be no scale ambiguity. If
scale alignment were needed, it would indicate a fundamental problem
with the sensor or algorithm, not just a coordinate frame mismatch.

**Timestamp association:** GT and odometry may run at different rates
and on different clocks. `evo` associates poses by nearest timestamp
(`--t_max_diff`). In this project, the indoor mocap and LiDAR clocks
were offset by ~21 hours (different time sources), requiring explicit
offset handling per method.

---

## Evaluation Metrics: ATE and RPE

**ATE (Absolute Trajectory Error)** — also called APE (Absolute Pose
Error) in `evo` — measures the global consistency of a trajectory.
After alignment, it computes the distance between each estimated pose
and the corresponding ground truth pose, then reports statistics
(RMSE, mean, max). ATE captures drift accumulation over the full
trajectory and is the primary metric reported in this project.

**RPE (Relative Pose Error)** measures local accuracy — how much
error accumulates per unit distance or per time step, independent of
global alignment. RPE is less sensitive to initialization errors and
better captures the local smoothness of the trajectory. It is
particularly relevant for evaluating drift rate.

In this project:
- GLIM achieves the best ATE (0.025 m on IndoorOffice1) due to loop closure
- FAST-LIO2 achieves the most consistent ATE across sequences (0.049–0.091 m)
- KISS-ICP shows the highest drift in indoor sequences (0.124 m) but
  is competitive outdoors (0.089 m) where geometry is richer

---

## Drift Accumulation

Drift is the progressive accumulation of pose estimation errors over
time. Even small per-scan errors (millimeters) compound into large
global errors (meters) over long trajectories. Drift is the fundamental
challenge in odometry-only systems.

In this project, FAST-LIO2 and DLIO (odometry only) show drift on
longer sequences. GLIM's loop closure mechanism detects when the robot
returns to a previously visited place and adds a constraint that
corrects the accumulated drift globally — this is why GLIM performs
significantly better on IndoorOffice1 (0.025 m) where the robot
revisits areas, compared to FAST-LIO2 (0.060 m) which drifts freely.

---

## Loop Closure

Loop closure is the detection and correction of the robot returning
to a previously visited location. When detected, a constraint is added
to the factor graph connecting the current pose to the earlier pose,
and the global trajectory is re-optimized to satisfy both the
sequential odometry constraints and the loop closure constraint.

Loop closure requires a global map (to recognize previously visited
places) and a global optimizer (to adjust the entire trajectory).
This is why only GLIM among the four methods benefits from loop closure.

In this project, loop closure is the primary reason for GLIM's
superior accuracy indoors. Outdoors (short 66s sequence with limited
revisitation), the benefit is smaller. On the CPU dev machine, loop
closure sometimes fires late due to computational lag — the Orin NX
GPU build is expected to close this gap.

---

## Scale Ambiguity

Scale ambiguity refers to the inability to determine the absolute
scale of a map from measurements alone. It is a fundamental problem
in **visual odometry** (monocular cameras cannot determine real-world
scale from images alone) but does **not** affect LiDAR odometry.

LiDAR measures distance via time-of-flight: distance = (speed of light
× time) / 2. This is an absolute metric measurement — a 1-meter
distance in the real world corresponds to exactly 1 meter in the
point cloud. Therefore, LiDAR-based methods have no scale ambiguity
and scale alignment should not be applied when evaluating them.

This is why all evaluations in this project use `--align` (rigid SE(3))
and not `--align --correct_scale` (similarity transform with scale).
Applying scale alignment to a LiDAR system would mask real errors and
produce artificially low ATE numbers.
