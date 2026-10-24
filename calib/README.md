# Livingroom splat calibration

`public/Livingroom-in-Taipei.metric.ply` (same bytes in `media/`) is the splat the viewer loads. The original capture, `Livingroom-in-Taipei.ply`, is unchanged in both directories.

The capture is rolled 180° about Z relative to three.js, so +Y points down. It is also tilted about 0.9°, yawed about 3.1°, and stored in arbitrary units. `correct.py` rotates positions, per-splat quaternions, and spherical-harmonic bands into a Y-up frame, then scales to meters. `transform.json` is the recorded matrix and the camera the viewer uses.

## Frame

- Right-handed, Y-up, matching three.js and `@mkkellogg/gaussian-splats-3d`.
- Origin on the floor, directly under the tuned viewing position.
- −Z toward the TV wall. The camera at the origin looks toward −Z.
- Meters. Scale `0.675` comes from the 65-inch 16:9 TV (visible panel 1.439 × 0.809 m, diagonal 1.651 m).

Viewer camera (`metric_camera` / `metric_lookat` in `transform.json`):

- position `[0, 1.074, 0]`
- look-at `[-0.708, 0.628, -1.943]`
- `cameraUp: [0, 1, 0]`

Head-tracking gains are the previous arbitrary-unit gains times 0.675: `XY_RESPONSE_BASE = 0.405` (was 0.6), `DEPTH_SCALE = 1.01` (was 1.5). With head Z at the calibration value −0.366, camera Z is 0.

## Transform

`correct.py` builds one rigid transform, then a uniform scale. Numbers below are the ones baked into `transform.json`.

1. **Roll.** `R0 = diag(-1, -1, 1)`, a 180° rotation about Z. In the file, +Y is down and +X is left.
2. **Level.** Measured gravity "up" in the R0 frame is `[-0.00246845, 0.99986862, -0.01601998]` (flat horizontal splats and vertical-surface normals). `R1` rotates that vector onto +Y.
3. **Yaw.** Fitted TV-wall planes have `atan2(nx, nz) = -3.1°` in the R0 frame. `R2` is a rotation about Y that turns the wall normal onto +Z, so the wall faces the viewer.
4. **Origin.** The old tuned camera `(0.72, 0.31, 0.05)` is mapped by `R = R2 R1 R0`. Translation puts that point's XZ on the origin and puts the floor (height −1.90 along "up" in the R0 frame) on Y = 0.
5. **Scale.** Positions are multiplied by `S = 0.675`. The file stores log-scales, so `scale_0/1/2` each gain `log(S)`. Quaternions are left-multiplied by the rotation quaternion. SH bands 1 and 2 (the `f_rest_*` coefficients) are rotated with the real 3DGS basis; `f_dc_*` is band 0 and is unchanged.

`T` in `transform.json` is the rigid step. `T_metric` is `diag(S, S, S, 1) · T`. Euler angles of `R` are about `[-0.91°, -3.101°, 179.858°]`.

## TV scale

`tv_measure.py` measures an orthographic front render of the pre-scale corrected splat (`0.005` units/pixel, view center `(−2.2, 1.2)`). That PNG (`calib/tv_front_ortho.png`) is not in the repo. `tv_measure.json` is the measurement that was used:

| Edge | Width | Height | Diagonal | Aspect |
| --- | ---: | ---: | ---: | ---: |
| Outer (bezel included) | 2.155 | 1.215 | 2.474 | 1.774 |
| Inner (bright screen) | 2.040 | 1.165 | 2.349 | 1.751 |

The outer edge matches 16:9 and is treated as the panel plus about 7 mm of bezel per side:

`S = (1.439 + 0.015) / 2.155 = 0.675`

Cross-checks in the script comments: height `(0.809 + 0.015) / 1.215 = 0.678`, diagonal `(1.651 + 0.02) / 2.474 = 0.675`. The inner edge alone would give about 0.70, which is why the outer edge was used. `tv_scale_estimates` in `transform.json` records those raw ratios before the 7 mm bezel allowance.

## Regenerate

Python 3 and `numpy`. From the repo root:

```bash
python3 calib/correct.py
```

Paths are relative to the repo. The script reads `media/Livingroom-in-Taipei.ply`, writes the pre-scale intermediate to `calib/Livingroom-in-Taipei.corrected.ply` (gitignored), writes `public/Livingroom-in-Taipei.metric.ply`, copies it to `media/`, and rewrites `calib/transform.json`.

A re-run reproduces `transform.json` exactly, and the PLY positions, scales, and SH coefficients. Quaternion values can move by about 1e-10 on a single component depending on the BLAS build. The committed metric PLY is the file from the correction archive, not a re-encode.

Re-measuring the TV also needs Pillow and `calib/tv_front_ortho.png`:

```bash
python3 calib/tv_measure.py
```

The original scripts used absolute paths under `/workspace/spatial-editor/`. Only those paths were retargeted; the rotation, SH fit, and scale are the same.
