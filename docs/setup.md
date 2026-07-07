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

## GLIM (CPU mode for dev PC, GPU mode for Orin)

GLIM requires three system dependencies built from source: GTSAM, Iridescence, and gtsam_points.

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
```

### GLIM config deployment

Copy the configs from this repo to the GLIM install directory:

```bash
cp ~/lidar-uav-nav/configs/glim/config/* \
   ~/slam_ws/install/glim/share/glim/config/
```

### Known gotchas

- The ROS package is named `glim_ros` but the directory is `glim_ros2/` — use `--packages-select glim_ros`
- config.hpp must be manually created for gtsam_points v1.0.4 (it was added in later versions)
- GLIM reads config from its install directory, not from `--config_path` CLI arg in v1.0.0
- `glim_rosbag` takes the bag path as a plain positional argument: `ros2 run glim_ros glim_rosbag <bag_path>`
- The odometry topic is `/glim_ros/odom` (not `/odom`)
- On CPU, global mapping can be slow — run bag at 1x speed and ensure global mapping is enabled in config_ros.json

---

## LIO-SAM (incompatible — documented for reference)

LIO-SAM requires a 9-axis IMU (accelerometer + gyroscope + magnetometer providing
orientation). The Livox Mid-360's built-in IMU is 6-axis only. Despite patching
the quaternion validity check to use an identity quaternion fallback, LIO-SAM
diverges completely (APE RMSE ~328 m). Do not use with Mid-360.

---

## Replicating on Jetson Orin NX

All steps above are identical except:

1. GLIM and gtsam_points: replace `-DBUILD_WITH_CUDA=OFF` with `-DBUILD_WITH_CUDA=ON`
2. CUDA toolkit must be installed (comes with JetPack on Orin)
3. No Iridescence display needed for headless operation — can disable the viewer in config_ros.json
4. Pull this repo: `git clone https://github.com/harshareddy1611/livox-mid360-slam-evaluation`
5. Configs in `configs/` are identical — no changes needed for Mid-360

Expected improvement on Orin with GPU: GLIM global mapping runs in real time,
enabling proper loop closure on all sequences.
