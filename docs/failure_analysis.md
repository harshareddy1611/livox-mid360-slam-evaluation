# Failure Case Analysis

This document analyzes the conditions under which each LiDAR navigation
algorithm evaluated in this project fails or performs poorly. All failure
cases are grounded in experimental observations from running KISS-ICP,
DLIO, FAST-LIO2, and GLIM on the TIERS Mid-360 dataset.

---

## KISS-ICP

### What it is
LiDAR-only point-to-point ICP odometry. No IMU, no loop closure.
Baseline method.

### Failure: Fast motion and aggressive rotation
ICP assumes small motion between consecutive scans. When the robot
moves quickly or rotates fast, the initial alignment estimate (from
a constant-velocity motion model) is far from the true transformation,
causing ICP to converge to a wrong local minimum. Without IMU
pre-integration to provide a better initial guess, fast motion is a
fundamental weakness of KISS-ICP.

In the TIERS dataset the robot is a walking quadruped at low speed —
this is a favorable scenario for KISS-ICP. On a fast UAV, failure
would be expected.

### Failure: Featureless / degenerate environments
ICP scan matching requires distinctive geometric features (corners,
edges, surfaces at different angles) to constrain all 6 DOF. In
geometrically degenerate environments — long straight corridors,
open fields, tunnels — the point-to-point correspondences cannot
constrain all directions. The algorithm degenerates along the
unconstrained axis.

Example: In a long featureless corridor, ICP can determine the
robot's position perpendicular to the walls but not along the
corridor (no geometric feature distinguishes one position from
another along the corridor length).

### Failure: Drift on long trajectories
KISS-ICP has no loop closure. Small per-scan errors accumulate
over time. In IndoorOffice1 (66s, 35m path), this produces a
0.124 m RMSE — acceptable. On longer sequences, drift would
grow proportionally. The method is unsuitable for long-duration
navigation without an external correction mechanism.

### Observed in this project
KISS-ICP performs worse indoors (0.124 m) than outdoors (0.089 m)
on the TIERS dataset. This counterintuitive result is explained by
the indoor trajectory having more rotation and direction changes,
which challenges the constant-velocity model, while the outdoor
road sequence has more predictable straight-line motion.

---

## DLIO (Direct LiDAR-Inertial Odometry)

### What it is
Continuous-time LiDAR-inertial odometry. Uses IMU for motion
correction with a coarse-to-fine approach. No loop closure.

### Failure: IMU calibration at startup
DLIO requires a stationary period at startup to calibrate IMU
bias (accelerometer and gyroscope offsets). During this ~3 second
window, it publishes poses at the origin (0,0,0). If evaluation
includes this startup period, APE is severely inflated.

**Observed in this project:** Raw DLIO APE on IndoorOffice1 was
0.144 m; after trimming the 3-second startup period, it dropped
to 0.075 m — a 48% reduction caused entirely by the calibration
artifact. On live hardware (Orin NX with real sensor), the
calibration happens before the robot starts moving, so this
artifact does not occur in practice.

### Failure: Dynamic objects
DLIO does not model dynamic objects. Moving people, vehicles, or
other robots add spurious points to the scan that corrupt the
scan matching. A person walking through the scene creates ghost
point clouds that cause ICP to partially match to the person
rather than the static environment, introducing pose errors.

### Failure: Vibration and aggressive IMU noise
DLIO's continuous-time IMU integration is designed for high-bandwidth
motion. However, very high-frequency vibrations (e.g., from a
quadrotor's propellers) saturate the IMU and corrupt the bias
estimation, degrading the motion correction that is DLIO's main
advantage over KISS-ICP.

### Failure: Sparse outdoor environments
In sparse environments (open fields, parking lots), point cloud
density is low and scan matching correspondences are unreliable.
DLIO's keyframe-based map becomes sparse, reducing the accuracy
of subsequent scan matching.

**Observed in this project:** DLIO's outdoor APE (0.090 m) is
similar to KISS-ICP (0.089 m), suggesting the IMU advantage
nearly disappears on the slow, smooth outdoor road sequence.
The continuous-time benefit is most pronounced on aggressive motion,
which this dataset does not exhibit.

---

## FAST-LIO2

### What it is
Tightly-coupled LiDAR-inertial odometry via iterated extended
Kalman filter (iEKF). No loop closure.

### Failure: Fast rotation (iEKF linearization breakdown)
The iEKF linearizes the nonlinear motion model around the current
state estimate. This linearization is valid only when the motion
is small relative to the state uncertainty. During fast rotations,
the linearization error grows, the filter diverges from the true
state, and subsequent scan matches fail to correct it because the
initial alignment is too far from the true transformation.

FAST-LIO2 is specifically designed to handle faster motion than
KISS-ICP (via IMU pre-integration), but very aggressive UAV
maneuvers (rapid flips, high angular velocity) can still cause
filter divergence.

### Failure: IMU-LiDAR extrinsic miscalibration
FAST-LIO2 fuses LiDAR and IMU measurements using the known
rigid transformation between the two sensors (extrinsic). If
this extrinsic is inaccurate, the IMU pre-integration predicts
the wrong scan position, causing systematic error in every scan.
The `extrinsic_est_en: true` setting enables online refinement
to partially compensate, but large initial errors can prevent
convergence.

In this project, the Mid-360's internal IMU has a factory extrinsic
of approximately [-0.011, -0.023, 0.044] m. Using identity
(zero offset) would cause systematic drift.

### Failure: Featureless environments
Like KISS-ICP, FAST-LIO2 relies on geometric features for scan
matching. The iEKF corrects drift using LiDAR updates — if the
LiDAR scan matching is unreliable (featureless corridor), the
IMU integration drifts uncorrected between updates.

### Failure: Long trajectories without loop closure
FAST-LIO2 is pure odometry — no loop closure. Over long
trajectories, drift accumulates and cannot be corrected. This
is evident in IndoorOffice2 (longer sequence, 95s) where
FAST-LIO2's APE (0.049 m) is better than GLIM's (0.096 m) due
to GLIM's CPU loop closure lag, but would eventually be overtaken
by GLIM on very long sequences where loop closure fires properly.

### Failure: Timestamp errors
FAST-LIO2 uses per-point timestamps for motion deskewing. In this
project, the initial ROS1→ROS2 bag conversion dropped the
per-point timestamp field. Running FAST-LIO2 on the unconverted
bag would produce poor deskewing and higher APE. This was
discovered and fixed by reconverting the bag with `rosbags-convert`.

### Observed in this project
FAST-LIO2 is the most consistent method across all three sequences
(0.049–0.091 m), demonstrating that IMU fusion provides robust
performance across indoor and outdoor scenarios. It is the
recommended method for real-time UAV navigation on the Orin NX
where no prior map is available.

---

## GLIM

### What it is
Full LiDAR-inertial SLAM with GPU-accelerated factor graph
optimization and loop closure.

### Failure: CPU computational lag (observed in this project)
GLIM's global mapping module runs loop closure detection and
factor graph optimization. On the dev PC (Intel iGPU, CPU-only
build), this computation cannot keep up with 10 Hz LiDAR input
in real time. Loop closures fire late or are missed entirely,
reducing GLIM to near-odometry performance on longer sequences.

**Observed:** IndoorOffice1 APE = 0.025 m (short sequence,
loop closure fired correctly) vs IndoorOffice2 APE = 0.096 m
(longer sequence, CPU lag prevented timely loop closure).

**Expected fix on Orin NX:** GPU build enables real-time global
optimization, restoring GLIM's full SLAM capability on all
sequences.

### Failure: Insufficient loop closure candidates
Loop closure requires the robot to physically revisit a previously
mapped area. If the trajectory is a single long sweep with no
revisitation (e.g., a straight corridor or a one-way road), no
loop closure can be detected regardless of computational resources.
GLIM degrades to pure odometry performance in this case.

**Observed:** OutdoorRoad APE = 0.087 m (similar to FAST-LIO2's
0.091 m) — the short road sequence has limited revisitation, so
loop closure provides minimal benefit outdoors.

### Failure: Dynamic objects corrupting loop closure
GLIM's loop closure uses scan matching between keyframes. If
dynamic objects (people, vehicles) are present in both the query
scan and the map keyframe, they create false correspondences that
degrade the loop closure quality. GLIM has no explicit dynamic
object removal.

### Failure: Large initial pose error
GLIM's local odometry module can diverge if the initial pose
estimate is very far from the true pose (e.g., if the algorithm
is initialized in a featureless area or after a long IMU blackout).
Unlike FAST-LIO2, GLIM does not have a dedicated re-initialization
mechanism in v1.0.0.

### Failure: Version-dependency chain fragility
GLIM has strict version requirements on its dependencies (GTSAM,
gtsam_points). In this project, the latest gtsam_points (v1.2.x)
was incompatible with GTSAM 4.2.0 due to a Boost constexpr issue,
requiring pinning to v1.0.4. This dependency fragility is a
practical failure mode in production deployment — a system update
can break the build silently.

---

## LIO-SAM (attempted, fundamentally incompatible)

### Failure: 6-axis IMU incompatibility
LIO-SAM requires a 9-axis IMU that provides absolute orientation
(roll, pitch, yaw) via a magnetometer. It uses this orientation
to initialize the factor graph with a correct global heading.

The Livox Mid-360's internal IMU is 6-axis (accelerometer +
gyroscope only — no magnetometer, no orientation output). When
LIO-SAM receives an IMU message with zero quaternion (no orientation),
it either crashes or, with the identity-quaternion patch applied,
initializes with a completely wrong heading and diverges.

**Observed:** LIO-SAM APE = 328 m on IndoorOffice1 — complete
divergence. The trajectory drifted hundreds of meters from ground
truth within the 66-second sequence.

**Lesson:** Method selection must account for sensor capabilities.
LIO-SAM is well-suited for platforms with 9-axis IMUs (e.g.,
ground vehicles with VectorNav or Microstrain IMUs) but is
fundamentally inappropriate for the Mid-360's built-in IMU.

---

## General Failure Modes Applicable to All Methods

### Outdoor vegetation
Tree branches and leaves are semi-transparent to LiDAR — some
pulses pass through, some return partial reflections. This creates
noisy, inconsistent point clouds in forested areas. Scan matching
against vegetation is unreliable because the same tree looks
different in consecutive scans. All four methods would degrade
significantly in dense forest, though GLIM's robust GICP matching
is somewhat more tolerant.

### Rain and fog
Water droplets scatter LiDAR pulses, creating a noise floor of
spurious returns at all ranges. Heavy rain can completely saturate
the LiDAR return window, rendering the sensor useless. The TIERS
dataset was collected in dry indoor/outdoor conditions; none of
the evaluated methods include weather-robust pre-processing.

### Sensor noise and calibration drift
All methods assume the LiDAR and IMU are well-calibrated. Over
time, IMU biases drift (temperature-dependent) and the LiDAR
calibration shifts (mechanical vibration). Without periodic
recalibration, all methods degrade gradually. FAST-LIO2's online
extrinsic estimation (`extrinsic_est_en: true`) partially mitigates
this by continuously refining the LiDAR-IMU extrinsic during operation.

### Scale ambiguity (not applicable to LiDAR)
Scale ambiguity — the inability to determine absolute metric scale
— is a fundamental problem in monocular visual odometry but does
not affect LiDAR-based methods. LiDAR measures absolute distances
via time-of-flight. All four methods in this project produce
metric-scale trajectories. Applying scale correction during
evaluation (e.g., `evo --correct_scale`) would mask real errors
and is explicitly avoided in this project's evaluation methodology.
