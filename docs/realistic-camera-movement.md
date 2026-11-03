# Realistic Camera Movement: The "Magic" Behind the Interaction

This document explains the implementation of the VisionOS-inspired head-coupled perspective interaction, which creates a highly immersive "window into a virtual world" effect using standard webcams.

## Core Concept: Head-Coupled Perspective vs. Traditional Parallax

### Traditional Parallax (The Old Way)
Most web parallax effects assume a cursor or gyroscope controls a 2D layer shift.
- **Mechanism:** Mouse moves LEFT -> Layers move RIGHT (opposite).
- **Feel:** Like looking at a 2D poster with layers.
- **Limit:** It's a screen effect, not a spatial one.

### Head-Coupled Perspective (The "Magic" Way)
We model the screen as a physical window frame. Your head position determines what angle you see through that window.
- **Mechanism:** Head moves LEFT -> Camera moves LEFT.
- **Key:** The **Camera Target** remains FIXED at the center of the window.
- **Effect:** As the camera moves left but keeps looking at the center, the objects behind the window appear to shift right naturally due to perspective projection. This creates true 3D motion parallax.

## The Pipeline

1.  **Face Tracking (`FaceTrackingManager.tsx`)**
    *   **Engine:** MediaPipe Face Landmarker.
    *   **X/Y Tracking:** Standard normalized nose tip position.
    *   **Z (Depth) Tracking:** The "Secret Sauce".
        *   MediaPipe's Z coordinate is often noisy and unreliable.
        *   **Solution:** We calculate `Face Width` (distance between cheek landmarks 234 and 454).
        *   Wider face = Closer to camera. Narrower = Further.
        *   This provides a robust, strictly physical proxy for Z-distance.

2.  **Calibration & Mapping (`StandaloneSplatViewer.tsx`)**
    *   We don't just use raw values; we calibrate them to the user's physical comfort zone.
    *   **Comfort Zone:** When the user sits at a comfortable distance (`HeadZ = -0.366` in our calibration), the metric camera sits at the floor-origin viewpoint (`CamZ = 0`, eye height 1.074 m).
    *   **Formula:**
        ```typescript
        TargetZ = CalibratedCamZ - (CurrentHeadZ - CalibratedHeadZ) * DepthScale
        ```
    *   This ensures the virtual world feels "anchored" to your physical posture.

3.  **Adaptive Smoothing (The "Silky" Feel)**
    *   Raw webcam data is noisy (jitter). Standard smoothing (Lerp) causes lag (floaty feel).
    *   **Solution:** Adaptive Lerp.
        *   **Idle:** If you are still, we use a very LOW lerp (`0.1`). This aggressively filters out all webcam noise, making the scene look rock-solid stable.
        *   **Moving:** As soon as you move, we ramp the lerp up to HIGH (`0.6`). This removes latency, making the movement feel instant and responsive.
        ```typescript
        // lerpFactor scales with distance^2
        const lerpFactor = Math.min(0.6, Math.max(0.1, distSq * 50.0));
        ```

## Comparison Summary

| Feature | Traditional Parallax | Our "Magic" Implementation |
| :--- | :--- | :--- |
| **Input** | Mouse / Gyro | Face Position (X, Y, Z) |
| **Z-Axis** | Usually Fake / Zoom | Real Physical Depth (Leaning in/out) |
| **Camera** | Fixed + Offset | Moving Camera + Fixed Target |
| **Smoothing**| Constant Lag | Adaptive (Stable when still, Fast when moving) |
| **Goal** | Visual Flair | Physical Presence |
