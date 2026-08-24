import sys
import numpy as np
from pathlib import Path
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore

bag_path = sys.argv[1]
out_png = sys.argv[2]

typestore = get_typestore(Stores.ROS2_HUMBLE)
last_msg = None

with AnyReader([Path(bag_path)], default_typestore=typestore) as reader:
    conns = [c for c in reader.connections if c.topic == "/Laser_map"]
    print(f"Found {len(conns)} connections for /Laser_map")
    count = 0
    for conn, timestamp, rawdata in reader.messages(connections=conns):
        msg = reader.deserialize(rawdata, conn.msgtype)
        last_msg = msg
        count += 1
    print(f"Total messages: {count}")

if last_msg is None:
    print("No messages found!")
    sys.exit(1)

# Parse PointCloud2 fields manually
fields = {f.name: f for f in last_msg.fields}
print("Fields:", list(fields.keys()))
point_step = last_msg.point_step
data = np.frombuffer(bytes(last_msg.data), dtype=np.uint8)
n_points = last_msg.width * last_msg.height
print(f"n_points: {n_points}, point_step: {point_step}")

x_off = fields['x'].offset
y_off = fields['y'].offset
z_off = fields['z'].offset

pts = np.zeros((n_points, 3), dtype=np.float32)
for i, name, off in [(0, 'x', x_off), (1, 'y', y_off), (2, 'z', z_off)]:
    col = np.frombuffer(data.tobytes(), dtype=np.float32)
    # reinterpret with stride
    byte_data = data.reshape(n_points, point_step)
    pts[:, i] = byte_data[:, off:off+4].copy().view(np.float32).ravel()

print(f"Point cloud shape: {pts.shape}")
print(f"X range: {pts[:,0].min():.2f} to {pts[:,0].max():.2f}")
print(f"Y range: {pts[:,1].min():.2f} to {pts[:,1].max():.2f}")
print(f"Z range: {pts[:,2].min():.2f} to {pts[:,2].max():.2f}")

# Save raw points for reuse
np.save(out_png.replace('.png', '_points.npy'), pts)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 8))
sc = ax.scatter(pts[:, 0], pts[:, 1], c=pts[:, 2], s=0.15, cmap='viridis', linewidths=0)
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_title('FAST-LIO2 map — batch1_00 (top-down view)')
ax.set_aspect('equal')
plt.colorbar(sc, label='Z (m)')
plt.tight_layout()
plt.savefig(out_png, dpi=150)
print(f"Saved plot to {out_png}")
