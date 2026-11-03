# 3D Gaussian Splatting (3DGS) Web Rendering

## Overview

This document explains how Gaussian Splatting rendering was implemented in this React/Vite application. It serves as a reference for future developers and AI agents.

---

## Rendering Library

**Library Used:** `@mkkellogg/gaussian-splats-3d`  
**Version:** `^0.4.6`  
**GitHub:** https://github.com/mkkellogg/GaussianSplats3D

> [!IMPORTANT]
> This library is **NOT** a Three.js addon. It creates its own renderer, scene, and camera internally. It cannot be embedded inside a React Three Fiber (`@react-three/fiber`) scene.

### Why This Library?
- Handles `.ply` and `.splat` file formats
- Built-in orbit controls
- Supports progressive loading
- Works in browsers (unlike CUDA-based renderers)

---

## Critical Architecture Decision

### ❌ Failed Approach: React Three Fiber Integration
We initially tried using `@react-three/drei`'s `<Splat>` component and wrapping the library in an R3F context. This **failed** because:

1. The library's `Viewer` class creates its own `THREE.WebGLRenderer`
2. R3F also manages its own renderer
3. Two renderers fighting causes blank screens or silent failures

### ✅ Working Approach: Standalone Viewer
The `StandaloneSplatViewer.tsx` component:
- Creates its own `<div>` container (not a `<canvas>`)
- Lets the library manage everything (renderer, camera, controls)
- Overlays on top of the React UI

```tsx
// The library creates its own canvas inside this div
<div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
```

---

## Safe Mode (Critical for Localhost)

### The Problem
Modern browsers require **Cross-Origin Isolation** headers to use `SharedArrayBuffer`:
```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Without these headers (common in dev servers), the library's worker-based rendering **hangs silently**.

### The Solution
Disable features that require `SharedArrayBuffer`:

```javascript
const viewer = new GaussianSplats3D.Viewer({
    useWorker: false,           // No web workers
    gpuAcceleratedSort: false,  // CPU sorting instead
    sharedMemoryForWorkers: false
});
```

> [!WARNING]
> Safe Mode is **slower** (~30-50% performance hit) but necessary for local development without proper COOP/COEP headers.

---

## Camera Configuration

### Coordinate System
The library uses a **right-handed** Y-up coordinate system, same as Three.js.

### Corrected metric frame
The default scene is `Livingroom-in-Taipei.v2.spz` (retrained, SH degree 2, 501,470 splats). It is already in the same Y-up meter frame as `Livingroom-in-Taipei.metric.ply`, so the camera is unchanged. `?splat=metric` (or `?splat=ply`) loads that PLY instead. The viewer is constructed with `sphericalHarmonicsDegree: 2`. The camera uses a normal up vector:

```javascript
{
    cameraUp: [0, 1, 0],
    initialCameraPosition: [0, 1.074, 0],
    initialCameraLookAt: [-0.708, 0.628, -1.943]
}
```

The origin is on the floor under the viewing position, and −Z points at the TV wall. Eye height at the calibrated pose is 1.074 m. Those two vectors are `metric_camera` and `metric_lookat` in `calib/transform.json`.

The original capture (`Livingroom-in-Taipei.ply`, still in `public/` and `media/`) is rolled 180° about Z, so +Y points down. It is also tilted about 0.9°, yawed about 3.1°, and stored in arbitrary units. While that file was on screen, the viewer compensated with `cameraUp: [0, -1, 0]` and hand-tuned coordinates (`position [0.72, 0.31, 0.05]`, look-at `[1.61, 1.02, -2.87]`). The metric file already contains that correction — positions, per-splat quaternions, and SH bands — so `cameraUp` stays `[0, 1, 0]`. See `calib/README.md` for the transform and how to regenerate it. Scale `0.675` is the 65-inch TV.

### How the viewpoint was set
1. `calib/correct.py` maps the old tuned camera and look-at through the same rotation, floor translation, and 0.675 scale.
2. `StandaloneSplatViewer.tsx` uses the mapped coordinates as the base camera and as the fixed `lookAt` target after every head-tracking update.

---

## File Format

**Default file:** `public/Livingroom-in-Taipei.v2.spz` (SPZ v2, about 15.7 MB, 501,470 splats, SH degree 2). Provenance and the COLMAP-to-metric transform are in `calib/README_v2.md`.  
**Fallback:** `public/Livingroom-in-Taipei.metric.ply` (same bytes in `media/`, about 9 MB, 55,215 splats), selected with `?splat=metric`.  
**Original capture:** `public/Livingroom-in-Taipei.ply` and `media/Livingroom-in-Taipei.ply` (unchanged)

The metric PLY is the original export after the `calib/correct.py` rotation and the 0.675 meter scale. Log-scales are shifted by `log(0.675)`. v2 was retrained from the iPhone videos and then placed in that same frame (`calib/colmap_to_metric_transform.json`). Each splat still has:

- 3D position
- Scale and quaternion (ellipsoid shape)
- Spherical harmonics (`f_dc_*`, `f_rest_*`)
- Opacity

> [!NOTE]
> `media/Livingroom-in-Taipei.spz` is an older compressed copy of the original capture. The viewer default is `public/Livingroom-in-Taipei.v2.spz`.

---

## Head Tracking Integration

The viewer's camera is updated based on head position from the `FaceTrackingManager`:

```javascript
useEffect(() => {
    if (!headX || !headY) return;
    
    const unsubX = headX.on('change', updateCamera);
    const unsubY = headY.on('change', updateCamera);
    
    function updateCamera() {
        const camX = baseCameraRef.current.x - headX.get() * xyResponse;
        const camY = baseCameraRef.current.y - headY.get() * xyResponse;
        viewer.camera.position.set(camX, camY, camZ);
        viewer.camera.lookAt(baseTarget.x, baseTarget.y, baseTarget.z);
    }
}, [headX, headY]);
```

**Key Points:**
- Base camera position is stored in a ref (doesn't change)
- Head offset is added on top of base position, then `camera.lookAt` locks onto the fixed metric target
- Gains are the old arbitrary-unit gains times 0.675: `XY_RESPONSE_BASE = 0.405`, `DEPTH_SCALE = 1.01`
- At the calibration distance (`HeadZ = -0.366`), camera Z is `0`
- Webcam X is negated so image-left (the user's right, on an unmirrored frame) moves the camera toward +X. Webcam Y is still subtracted: MediaPipe Y grows downward, which raises the camera when the head moves up. The vertical sign has not been checked with a real webcam since the model was turned upright.

---

## Component Hierarchy

```
main.tsx
  └── BackgroundManager.tsx
        └── (type === "mixed-reality")
              └── StandaloneSplatViewer.tsx
                    └── GaussianSplats3D.Viewer (internal)
```

---

## Troubleshooting Guide

| Symptom | Cause | Fix |
|---------|-------|-----|
| Blank white screen | Renderer conflict with R3F | Use standalone viewer |
| Hangs indefinitely | SharedArrayBuffer disabled | Use Safe Mode |
| Model upside-down | Original capture is on screen, or the metric file is loaded with the old `cameraUp: [0, -1, 0]` | Load `Livingroom-in-Taipei.metric.ply` with `cameraUp: [0, 1, 0]`. The metric splat is already Y-up |
| Wrong viewpoint | Camera does not match `calib/transform.json` | Use `metric_camera` `[0, 1.074, 0]` and `metric_lookat` `[-0.708, 0.628, -1.943]` |
| "Module not found" | Missing types | Add `.d.ts` shim file |

---

## Files Created/Modified

| File | Purpose |
|------|---------|
| `components/StandaloneSplatViewer.tsx` | Main viewer component |
| `src/types/gaussian-splats-3d.d.ts` | TypeScript declarations |
| `components/BackgroundManager.tsx` | Routes to viewer |
| `public/Livingroom-in-Taipei.v2.spz` | Default scene: retrained SPZ, SH degree 2 (~15.7 MB, 501k splats) |
| `public/Livingroom-in-Taipei.metric.ply` | Previous metric splat (`?splat=metric`; ~9 MB; copy in `media/`) |
| `public/Livingroom-in-Taipei.ply` | Original capture, unchanged (~9 MB; copy in `media/`) |
| `calib/` | Transform script, TV measurement, and recorded matrix |

---

## Future Improvements

1. **Enable GPU sorting in production** - Add COOP/COEP headers to production server
2. **Preload splat data** - Load in background before user switches to livingroom
3. **Multiple splat scenes** - Support loading different environments
4. **LOD system** - Load lower quality first, then refine

---

## References

- [3D Gaussian Splatting Paper](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
- [GaussianSplats3D Library](https://github.com/mkkellogg/GaussianSplats3D)
- [SharedArrayBuffer Requirements](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer#security_requirements)
