# Dataset: TIERS LiDAR Variability

Download `IndoorOffice1` from the TIERS dataset:
https://github.com/TIERS/tiers-lidars-dataset

The bag ships as a ROS1 `.bag`. Convert to ROS2 with:

```bash
pip install rosbags
rosbags-convert --src IndoorOffice1_dataset.bag --dst IndoorOffice1_ros2_v2
```

Then fix a metadata issue caused by rosbags writing `offered_qos_profiles: []`,
which ROS2 Humble rejects:

```bash
sed -i 's/offered_qos_profiles: \[\]/offered_qos_profiles: ""/' \
  IndoorOffice1_ros2_v2/metadata.yaml
```

Verify the conversion preserved per-point timestamps (needed for deskew):

```bash
ros2 bag play IndoorOffice1_ros2_v2 --topics /mid360/livox/lidar --loop &
ros2 topic echo /mid360/livox/lidar --once | grep -A10 "fields:"
# expect: x y z intensity tag line timestamp
```
