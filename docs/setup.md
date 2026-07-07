# Setup Guide

Complete build instructions for Ubuntu 22.04 + ROS 2 Humble.
Tested on x86_64 (dev) and replicable on Jetson Orin NX (target).

## Prerequisites

```bash
sudo apt update
sudo apt install -y ros-humble-xacro \
                   ros-humble-gps-msgs \
                   ros-humble-geographic-msgs \
                   ros-humble-robot-localization
pip install kiss-icp evo rosbags
```

## Workspace layout

Keep the colcon workspace separate from this repo:

```
~/slam_ws/              # colcon workspace — never commit, rebuild on each machine
    src/
        FAST_LIO_ROS2/
        livox_ros_driver2/
        glim/
        glim_ros2/
~/lidar-uav-nav/        # this repo — configs, scripts, results
```

---

## KISS-ICP

No colcon build needed — installs via pip:

```bash
pip install kiss-icp
kiss_icp_pipeline --help   # verify
```

---

## FAST-LIO2

Uses the Ericsii ROS2 port. Livox driver must be built first.

```bash
cd ~/slam_ws/src

# Livox ROS2 driver
git clone https://github.com/Livox-SDK/livox_ros_driver2.git
cd livox_ros_driver2
./build.sh humble
cd ..

# FAST-LIO2 ROS2 port
git clone https://github.com/Ericsii/FAST_LIO_ROS2.git --recursive

# build
cd ~/slam_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select fast_lio

# verify
source install/setup.bash
ros2 pkg executables fast_lio
# expected: fast_lio fastlio_mapping
```

### Known gotchas

- Must use the Ericsii fork — the hku-mars main branch is ROS1/catkin and will fail with a `find_package(catkin)` error
- Livox driver must be built and sourced before building FAST-LIO2
- If you get a "duplicate package names" error, check for a nested `slam_ws/` inside `~/slam_ws/` left from earlier attempts and remove it
- The `lidar_type: 4` config setting is correct for the TIERS PointCloud2 format (not Livox CustomMsg)

---

## DLIO

Uses the `feature/ros2` branch of the official VECTR-UCLA repo.

```bash
cd ~/slam_ws/src
git clone https://github.com/vectr-ucla/direct_lidar_inertial_odometry.git
cd direct_lidar_inertial_odometry && git checkout feature/ros2 && cd ..

cd ~/slam_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install \
  --packages-select direct_lidar_inertial_odometry \
  --cmake-args -DCMAKE_BUILD_TYPE=Release

# verify
source install/setup.bash
ros2 pkg executables direct_lidar_inertial_odometry
# expected: dlio_map_node, dlio_odom_node

# deploy config
cp ~/lidar-uav-nav/configs/dlio/mid360.yaml \
   ~/slam_ws/src/direct_lidar_inertial_odometry/cfg/dlio.yaml
```

### Known gotchas

- DLIO performs a 3-second IMU calibration at startup — trim the first 3s of output before evaluation using `scripts/trim_dlio.py`
- Config is read from `cfg/dlio.yaml` inside the source tree, not via a launch arg
- Output topic is `/dlio/odom_node/odom` (not `/odom`)
- On live hardware the startup calibration happens before motion, so no trimming needed

---

## GLIM (CPU mode for dev PC, GPU mode for Orin)

**On the Orin NX, use the PPA method instead — skip to the Orin section below.**

On the dev PC, GLIM requires three system dependencies built from source: GTSAM, Iridescence, and gtsam_points.

### Step 1 — GTSAM 4.2.0

```bash
cd ~
git clone https://github.com/borglab/gtsam.git
cd gtsam && git checkout 4.2.0
mkdir build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DGTSAM_BUILD_TESTS=OFF \
  -DGTSAM_BUILD_EXAMPLES_ALWAYS=OFF \
  -DGTSAM_USE_SYSTEM_EIGEN=ON \
  -DGTSAM_BUILD_WITH_MARCH_NATIVE=OFF
make -j$(nproc)
sudo make install
sudo ldconfig
```

### Step 2 — Iridescence (visualizer)

```bash
cd ~
git clone https://github.com/koide3/iridescence.git --recursive
mkdir iridescence/build && cd iridescence/build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
sudo ldconfig
```

### Step 3 — gtsam_points

Use tag v1.0.4 — compatible with GTSAM 4.2.0 and Boost 1.74 (Ubuntu 22.04 default).
The v1.2.x series has a constexpr/Boost incompatibility with this stack.

```bash
cd ~
git clone https://github.com/koide3/gtsam_points.git
cd gtsam_points && git checkout v1.0.4
mkdir build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/usr/local \
  -DBUILD_WITH_CUDA=OFF \
  -DBUILD_WITH_MARCH_NATIVE=OFF
make -j$(nproc)
sudo make install
sudo ldconfig
```

gtsam_points v1.0.4 does not generate config.hpp — create it manually:

```bash
sudo tee /usr/local/include/gtsam_points/config.hpp > /dev/null << 'HEOF'
#pragma once
// Manually created config for gtsam_points CPU-only build
#ifndef GTSAM_POINTS_USE_CUDA
// #define GTSAM_POINTS_USE_CUDA
#endif
HEOF
```

### Step 4 — GLIM + glim_ros

```bash
cd ~/slam_ws/src
git clone https://github.com/koide3/glim.git
cd glim && git checkout v1.0.0 && cd ..

git clone https://github.com/koide3/glim_ros2.git
cd glim_ros2 && git checkout v1.0.0 && cd ..

cd ~/slam_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
colcon build --symlink-install \
  --packages-select glim glim_ros \
  --cmake-args -DBUILD_WITH_CUDA=OFF \
  --no-warn-unused-cli

# verify
source install/setup.bash
ros2 pkg executables glim_ros
# expected: glim_ros glim_rosnode, glim_ros glim_rosbag, glim_ros offline_viewer

# deploy configs
cp ~/lidar-uav-nav/configs/glim/config/* \
   ~/slam_ws/install/glim/share/glim/config/
```

### Known gotchas (dev PC)

- The ROS package is named `glim_ros` but the directory is `glim_ros2/` — use `--packages-select glim_ros`
- config.hpp must be manually created for gtsam_points v1.0.4 (it was added in later versions)
- GLIM reads config from its install directory, not from `--config_path` CLI arg in v1.0.0
- The odometry topic is `/glim_ros/odom` (not `/odom`)
- On CPU, global mapping can be slow — run bag at 1x speed and ensure global mapping is enabled in config_ros.json

---

## LIO-SAM (incompatible — documented for reference)

LIO-SAM requires a 9-axis IMU (accelerometer + gyroscope + magnetometer providing
orientation). The Livox Mid-360's built-in IMU is 6-axis only. Despite patching
the quaternion validity check to use an identity quaternion fallback, LIO-SAM
diverges completely (APE RMSE ~328 m). Do not use with Mid-360.

---

## Jetson Orin NX — Quick Start

This section covers setting up the full pipeline on the Orin NX for
offline dataset evaluation (bags only, no live sensor yet).

### Step 0 — Check JetPack version first

```bash
cat /etc/nv_tegra_release
nvcc --version
```

GLIM requires **JetPack 6.x (CUDA 12.2+)**. If you have JetPack 5.x
(CUDA 11.x), upgrade via NVIDIA SDK Manager before proceeding.
JetPack 6 is a full OS reflash — plan ~2 hours including download time.

### Step 1 — Clone the repo

```bash
git clone https://github.com/harshareddy1611/livox-mid360-slam-evaluation
cd livox-mid360-slam-evaluation
```

### Step 2 — Install eval tools

```bash
pip install kiss-icp evo rosbags
```

### Step 3 — Install GLIM via PPA (GPU, no source build needed)

On JetPack 6.x with CUDA 12.2:

```bash
# add koide3's PPA
curl -s https://koide3.github.io/ppa/setup_ppa.sh | sudo bash

# install GLIM with CUDA support
sudo apt install -y libgtsam-points-cuda12.2-dev
sudo apt install -y ros-humble-glim-ros-cuda12.2

# verify
source /opt/ros/humble/setup.bash
ros2 pkg executables glim_ros
```

If your JetPack ships CUDA 12.6, replace `cuda12.2` with `cuda12.6`.

After installing, deploy the Mid-360 configs:

```bash
# find the installed GLIM config directory
GLIM_CFG=$(find /opt/ros/humble -name "config.json" -path "*/glim/*" 2>/dev/null | head -1 | xargs dirname)
echo "GLIM config dir: $GLIM_CFG"
cp ~/livox-mid360-slam-evaluation/configs/glim/config/* "$GLIM_CFG/"
```

### Step 4 — Build FAST-LIO2 and DLIO

Same as the dev PC — identical commands, no changes needed:

```bash
mkdir -p ~/slam_ws/src && cd ~/slam_ws/src

# Livox driver
git clone https://github.com/Livox-SDK/livox_ros_driver2.git
cd livox_ros_driver2 && ./build.sh humble && cd ..

# FAST-LIO2
git clone https://github.com/Ericsii/FAST_LIO_ROS2.git --recursive

# DLIO
git clone https://github.com/vectr-ucla/direct_lidar_inertial_odometry.git
cd direct_lidar_inertial_odometry && git checkout feature/ros2 && cd ..

# build all
cd ~/slam_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# deploy DLIO config
cp ~/livox-mid360-slam-evaluation/configs/dlio/mid360.yaml \
   ~/slam_ws/src/direct_lidar_inertial_odometry/cfg/dlio.yaml

# verify all three
source install/setup.bash
ros2 pkg executables fast_lio
ros2 pkg executables direct_lidar_inertial_odometry
ros2 pkg executables glim_ros
```

### Step 5 — Transfer datasets to Orin

Copy the already-converted ROS2 bags from your PC via SCP:

```bash
# run these on your PC (replace <orin-ip> with the Orin's IP)
scp -r ~/Downloads/IndoorOffice1_ros2_v2 user@<orin-ip>:~/Downloads/
scp -r ~/Downloads/IndoorOffice2_ros2    user@<orin-ip>:~/Downloads/
scp -r ~/Downloads/OutdoorRoad_cut0_ros2 user@<orin-ip>:~/Downloads/
```

Copy the converted `_ros2` directories, not the original `.bag` files —
the conversion and metadata fix are already done.

### Step 6 — Run the pipeline

Identical to the dev PC — same scripts, same configs:

```bash
cd ~/livox-mid360-slam-evaluation

# ground truth (IndoorOffice1 example)
python3 scripts/extract_gt.py ~/Downloads/IndoorOffice1_ros2_v2 \
  --topic /vrpn_client_node/unitree_b1/pose \
  --out results/gt_mid360.tum

# run methods
bash scripts/run_kiss_icp.sh ~/Downloads/IndoorOffice1_ros2_v2
bash scripts/run_fastlio2.sh ~/Downloads/IndoorOffice1_ros2_v2
bash scripts/run_glim.sh     ~/Downloads/IndoorOffice1_ros2_v2

# evaluate
bash scripts/evaluate.sh
```

### What to expect differently on the Orin vs dev PC

| Aspect | Dev PC (Intel iGPU, CPU-only) | Orin NX (GPU) |
|--------|-------------------------------|---------------|
| GLIM global mapping | Slow, may lag at 1x playback | Real-time at 1x |
| GLIM loop closure | Sometimes fires late / misses | Fires properly every scan |
| GLIM APE expected | 0.025–0.096 m (sequence dependent) | Better across all sequences |
| FAST-LIO2 | Same | Same (CPU-bound, no GPU benefit) |
| KISS-ICP | Same | Same |
| DLIO | Same | Same (CPU-bound) |

The main expected improvement is **GLIM** — GPU acceleration enables
real-time global optimization and loop closure on all sequences, giving
results closer to the theoretical best rather than the CPU-limited
results observed on the dev PC.
