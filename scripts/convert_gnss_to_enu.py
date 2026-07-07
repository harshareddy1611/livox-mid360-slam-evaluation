#!/usr/bin/env python3
"""
Convert GNSS lat/lon/alt TUM file to local ENU TUM file.
Uses the first pose as the origin.
Requires: pip install pyproj
"""
import argparse
import math

def lla_to_enu(lat, lon, alt, lat0, lon0, alt0):
    """Convert lat/lon/alt to local ENU coordinates."""
    # WGS84 parameters
    a = 6378137.0  # semi-major axis
    f = 1/298.257223563  # flattening
    b = a * (1 - f)
    e2 = 1 - (b/a)**2

    def to_ecef(lat, lon, alt):
        lat_r = math.radians(lat)
        lon_r = math.radians(lon)
        N = a / math.sqrt(1 - e2 * math.sin(lat_r)**2)
        x = (N + alt) * math.cos(lat_r) * math.cos(lon_r)
        y = (N + alt) * math.cos(lat_r) * math.sin(lon_r)
        z = (N * (1 - e2) + alt) * math.sin(lat_r)
        return x, y, z

    x, y, z = to_ecef(lat, lon, alt)
    x0, y0, z0 = to_ecef(lat0, lon0, alt0)
    dx, dy, dz = x-x0, y-y0, z-z0

    lat0_r = math.radians(lat0)
    lon0_r = math.radians(lon0)

    e = -math.sin(lon0_r)*dx + math.cos(lon0_r)*dy
    n = -math.sin(lat0_r)*math.cos(lon0_r)*dx \
        -math.sin(lat0_r)*math.sin(lon0_r)*dy \
        +math.cos(lat0_r)*dz
    u = math.cos(lat0_r)*math.cos(lon0_r)*dx \
        +math.cos(lat0_r)*math.sin(lon0_r)*dy \
        +math.sin(lat0_r)*dz

    return e, n, u

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default="gt_enu.tum")
    args = ap.parse_args()

    lines = open(args.input).readlines()
    # get origin from first pose
    first = list(map(float, lines[0].split()))
    lat0, lon0, alt0 = first[1], first[2], first[3]
    print(f"Origin: lat={lat0:.6f} lon={lon0:.6f} alt={alt0:.3f}")

    with open(args.out, 'w') as f:
        for line in lines:
            parts = list(map(float, line.strip().split()))
            t = parts[0]
            lat, lon, alt = parts[1], parts[2], parts[3]
            qx, qy, qz, qw = parts[4], parts[5], parts[6], parts[7]
            e, n, u = lla_to_enu(lat, lon, alt, lat0, lon0, alt0)
            f.write(f"{t:.9f} {e:.6f} {n:.6f} {u:.6f} "
                    f"{qx:.6f} {qy:.6f} {qz:.6f} {qw:.6f}\n")

    # report path length
    import math
    poses = [list(map(float, l.split())) for l in open(args.out).readlines()]
    dist = sum(math.sqrt((poses[i][1]-poses[i-1][1])**2 +
                         (poses[i][2]-poses[i-1][2])**2 +
                         (poses[i][3]-poses[i-1][3])**2)
               for i in range(1, len(poses)))
    print(f"Wrote {len(poses)} poses to {args.out}")
    print(f"Path length in ENU: {dist:.2f} m")

if __name__ == "__main__":
    main()
