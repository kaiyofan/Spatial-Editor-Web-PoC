import React, { useEffect, useRef, useCallback } from 'react';
import * as GaussianSplats3D from '@mkkellogg/gaussian-splats-3d';
import { MotionValue } from 'motion/react';

interface StandaloneSplatViewerProps {
    url: string;
    className?: string;
    headX?: MotionValue<number>;
    headY?: MotionValue<number>;
    headZ?: MotionValue<number>;
    onCameraUpdate?: (cam: { x: number; y: number; z: number }, target: { x: number; y: number; z: number }) => void;
    debugCameraControls?: boolean;
}

/**
 * Standalone Gaussian Splat Viewer with Head Tracking Support.
 * 
 * Uses the EXACT same approach as the working splat-test.html Safe Mode.
 * Creates its own canvas and render loop - does NOT integrate with R3F.
 */
export const StandaloneSplatViewer: React.FC<StandaloneSplatViewerProps> = ({
    url,
    className = '',
    headX,
    headY,
    headZ,
    onCameraUpdate,
    debugCameraControls = false,
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const viewerRef = useRef<any>(null);
    // User-verified camera defaults for head tracking base position
    const baseCameraRef = useRef({ x: 0, y: 1.074, z: 0 });
    const baseTargetRef = useRef({ x: -0.708, y: 0.628, z: -1.943 });

    useEffect(() => {
        if (!containerRef.current) return;

        // Clear any previous viewer
        if (viewerRef.current) {
            viewerRef.current.dispose();
            viewerRef.current = null;
        }

        console.log('[StandaloneSplatViewer] Initializing with Safe Mode...');

        // EXACT settings from working splat-test.html Safe Mode
        const viewer = new GaussianSplats3D.Viewer({
            // Camera - corrected (metric) splat is +Y up, so no camera flip needed
            'cameraUp': [0, 1, 0],
            'useBuiltInControls': debugCameraControls,
            // Corrected metric frame (calib/transform.json metric_camera / metric_lookat).
            // v2 is in this same frame; see calib/README_v2.md.
            'initialCameraPosition': [0, 1.074, 0],
            'initialCameraLookAt': [-0.708, 0.628, -1.943],
            // v2 SPZ stores SH degree 2. The viewer defaults to 0 and would drop those bands.
            'sphericalHarmonicsDegree': 2,
            // Safe Mode settings - CRITICAL for localhost without COOP/COEP
            'useWorker': false,
            'gpuAcceleratedSort': false,
            'sharedMemoryForWorkers': false,
            // Mount to our container
            'rootElement': containerRef.current,
        });

        viewerRef.current = viewer;

        // 0.4.7 maps a .spz path to SceneFormat.Spz. Pass the format anyway so a
        // renamed or query-suffixed URL still decodes as SPZ.
        const isSpz = url.split('?')[0].toLowerCase().endsWith('.spz');
        viewer.addSplatScene(url, {
            'splatAlphaRemovalThreshold': 1, // Matches Safe Mode
            'showLoadingUI': true,
            ...(isSpz ? { 'format': GaussianSplats3D.SceneFormat.Spz } : {}),
        })
            .then(() => {
                console.log('[StandaloneSplatViewer] Loaded successfully!');
                viewer.start();

                // Force camera to our calculated initial position just in case
                // But DO NOT overwrite baseCameraRef - we need that to stay fixed at 0.02
            })
            .catch((err: any) => {
                console.error('[StandaloneSplatViewer] Load failed:', err);
            });

        // Cleanup on unmount
        return () => {
            console.log('[StandaloneSplatViewer] Disposing...');
            if (viewerRef.current) {
                viewerRef.current.dispose();
                viewerRef.current = null;
            }
        };
    }, [url, debugCameraControls]);

    // Head tracking effect - apply head position to camera
    // VisionOS-like "window into virtual world" approach
    // Face position = Camera position (1:1 mapping)
    useEffect(() => {
        if (!headX || !headY) return;

        // Base response scales
        const XY_RESPONSE_BASE = 0.405; // 0.6 * 0.675 metric scale
        const DEPTH_SCALE = 1.01;      // 1.5 * 0.675 metric scale

        let animationId: number;

        const updateCamera = () => {
            const viewer = viewerRef.current;
            if (!viewer || !viewer.camera) {
                animationId = requestAnimationFrame(updateCamera);
                return;
            }

            // Get head position (X, Y, Z) - already normalized -1 to 1
            const hx = headX.get();
            const hy = headY.get();
            const hz = headZ?.get() || 0;  // From face width: positive = closer

            // Distance-aware X/Y response:
            // When closer (hz > 0), reduce X/Y effect (you're "inside" the scene)
            // When further (hz < 0), increase X/Y effect (normal window parallax)
            // Range: 0.3 (very close) to 1.0 (normal distance)
            const distanceFactor = Math.max(0.3, 1.0 - hz * 0.5);
            const xyResponse = XY_RESPONSE_BASE * distanceFactor;

            // 1:1 Head-Coupled Perspective
            // Camera follows head position, target stays FIXED at base
            // This creates the "window into virtual world" parallax effect

            // Calculate target camera position
            // MediaPipe landmarks are in the un-mirrored webcam frame: x grows to the image right
            // (= user's left), y grows downward. Corrected scene is +X right, +Y up, so camera
            // follows head: head right -> hx < 0 -> +X; head up -> hy < 0 -> +Y.
            const targetX = baseCameraRef.current.x - hx * xyResponse;
            const targetY = baseCameraRef.current.y - hy * xyResponse;

            // Absolute Z calibration: camera at base z (0) when HeadZ is -0.366
            // Ignore baseCameraRef.z because viewer seems to overwrite it
            const CALIBRATED_CAM_Z = 0;
            const CALIBRATED_HEAD_Z = -0.366;
            // Diff from calibration point
            const headZDiff = hz - CALIBRATED_HEAD_Z;
            // Apply scale (negative because closer head (positive diff) means closer camera (negative Z change))
            const targetZ = CALIBRATED_CAM_Z - headZDiff * DEPTH_SCALE;

            // DIRECT UPDATE - No internal smoothing
            // We rely on the BackgroundManager to pass in smoothed MotionValues
            viewer.camera.position.x = targetX;
            viewer.camera.position.y = targetY;
            viewer.camera.position.z = targetZ;
            const t0 = baseTargetRef.current;
            viewer.camera.lookAt(t0.x, t0.y, t0.z);

            // KEY DIFFERENCE: Target stays FIXED at base position
            // This is what creates the parallax "window" effect
            // When you move left, scene shifts right (like peering through a window)

            // Report camera position for UI display
            if (onCameraUpdate && viewer.camera) {
                const p = viewer.camera.position;
                const t = viewer.controls?.target || { x: 0, y: 0, z: 0 };
                onCameraUpdate(
                    { x: p.x, y: p.y, z: p.z },
                    { x: t.x, y: t.y, z: t.z }
                );
            }

            animationId = requestAnimationFrame(updateCamera);
        };

        animationId = requestAnimationFrame(updateCamera);

        return () => {
            if (animationId) cancelAnimationFrame(animationId);
        };
    }, [headX, headY, onCameraUpdate]);

    return (
        <div ref={containerRef} className={`relative ${className}`} style={{ width: '100%', height: '100%' }}>

        </div>
    );
};
