# Livingroom-in-Taipei.v2.spz

Gaussian-splat scene of the Taipei living room, retrained (v2) and aligned to the viewer's metric frame.

## Drop-in usage
- **Same metric frame as `Livingroom-in-Taipei.metric.ply`** (meters, Y-up; the TV is the 65" 16:9 reference, center ≈ (-1.062, 0.992, -1.93)). Existing viewer camera values (e.g. position (0, 1.074, 0), look-at (-0.708, 0.628, -1.943)) apply unchanged.
- Format: SPZ v2 (gzip), **SH degree 2** stored. Load with `sphericalHarmonicsDegree: 2` (the @mkkellogg/gaussian-splats-3d viewer caps at 2).
- **501,470 splats, 15,667,694 bytes (15.7 MB)**.

## Source and training
- Source: two iPhone spatial videos (MV-HEVC, clipA 21.0 s / clipB 18.3 s). Both eyes were extracted, giving 236 images (118 stereo pairs, `L_`/`R_`).
- Poses: COLMAP (pycolmap 4.2.1), PINHOLE cameras, `sparse/0`.
- Training: Brush v0.3.0 (Windows, RTX 4050 6 GB), export at step 40000:
  ```
  brush_app.exe livingroom_brush_dataset.zip --total-steps 40000 --growth-stop-iter 30000 \
    --growth-grad-threshold 2e-5 --growth-select-fraction 0.2 --lr-coeffs-sh-scale 10 \
    --sh-degree 3 --max-splats 1200000 --max-resolution 1920 --export-every 5000
  ```
  (`--sh-degree 3 --max-splats 1200000 --max-resolution 1920` are the dataset README's base flags and are assumed. The other flags are the v2 changes.) Raw export: 588,813 splats, SH3.

## Transform COLMAP/Brush-export frame -> metric viewer frame
`X_metric = s * R * X_colmap + t`, with s = 0.952244 (full values in `colmap_to_metric_transform.json`):
```
T (4x4, includes scale) =
[[ 0.951984  0.016730 -0.014637 -0.509278]
 [ 0.014631 -0.943625 -0.126991  1.237564]
 [-0.016736  0.126732 -0.943625  0.690168]
 [ 0         0         0         1       ]]
```
The transform is applied to positions. Covariances are rotated (R Σ Rᵀ, i.e. the quaternions are rotated) and log-scales get +ln s. SH bands 1–3 are rotated exactly (error ~1e-14).

How the transform was found and checked: the up-vector comes from horizontal surfaces, followed by a yaw/scale search and 4-DOF ICP against the old metric splat. The metric scale comes from the TV (65", 16:9). Checked by ICP on v2: median 18.5 mm vs the old splat and 7.4 mm vs v1; the residual correction was negligible.

## Pruning (reflection-safe "light prune")
- **Protected (never pruned):** splats in the TV cone seen from the viewing position (0, 1.074, 0) whose ray hits the plane z = -1.93 within ±0.8 m in x of the TV center and ±0.48 m in y, AND that sit at or behind z < -1.88. These carry the TV reflection: 90,170 splats.
- **Removed (outside the protected zone):** opacity < 0.02, OR (opacity < 0.05 AND largest axis < 5 mm). That is 87,343 splats (14.8%), about 0.7% of total opacity×area.
- No distance or room-box pruning.
- Rendered PSNR vs unpruned v2: 41.5–44.1 dB (main/head/TV views), 39.7 dB (overview).
- A more aggressive prune (opacity < 0.05 everywhere outside the protected zone, plus large far floaters) was tested and rejected: 29.8–34.8 dB, with visible change on the TV.

## Encoding
- SPZ v2 with 12 fractional position bits (~0.24 mm grid).
- SH degree 2 kept, degree 3 dropped. SH stored at full 8-bit precision; this is still a valid SPZ, just coarser buckets were not used (the standard encoder uses 5-bit/4-bit buckets).
- Any scale axis smaller than e^-10 m (0.045 mm) is clamped to 0.045 mm, which is the SPZ format's floor.

## Verification
Decoded with @mkkellogg/gaussian-splats-3d 0.4.7 `SpzLoader.loadFromFileData` in Node 20. The only shims were `window` and a Node-only fix so DecompressionStream accepts ArrayBuffer chunks. Compared against the source PLY:
- Count 501,470 = 501,470.
- Position error ≤ 0.12 mm.
- Quaternion |dot| p1 0.998.
- Color error median 0.5/255; alpha error median 0.25/255.
- SH deg1–2 error median 0.002 (corr 0.9994).
