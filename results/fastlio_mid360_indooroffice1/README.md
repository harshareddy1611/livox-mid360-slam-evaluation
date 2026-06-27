# FAST-LIO2 Evaluation on Livox MID360 (IndoorOffice1)

## System

- Ubuntu 22.04
- ROS2 Humble
- FAST-LIO2 (ROS2)
- Livox MID360
- EVO for evaluation

## Dataset

- IndoorOffice1
- Duration: 66.2 s
- Ground Truth Path Length: 35.316 m
- Estimated Path Length: 32.288 m

## Metrics

### Absolute Pose Error (APE)

| Metric | Value |
|---------|--------|
| Mean | 0.053 m |
| RMSE | 0.060 m |
| Median | 0.053 m |
| Max | 0.145 m |
| Std | 0.028 m |

### Relative Pose Error (RPE)

| Metric | Value |
|---------|--------|
| Mean | 0.086 m |
| RMSE | 0.113 m |
| Median | 0.072 m |
| Max | 0.363 m |
| Std | 0.074 m |

## Alignment

SE(3) Umeyama alignment:

```text
Rotation:
[[-0.99774732  0.0540252   0.03976891]
 [-0.05348651 -0.99846347  0.01448781]
 [ 0.04049051  0.01232807  0.99910387]]

Translation:
[ 6.11004699 15.67821613  1.19195216]

Scale correction:
1.0

