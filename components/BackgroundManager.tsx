import React from "react";
import { motion, MotionValue, useTransform, useSpring } from "motion/react";
import { StandaloneSplatViewer } from "./StandaloneSplatViewer";

export type BackgroundType =
  | "original"
  | "bg"
  | "bg1"
  | "mixed-reality";

interface BackgroundManagerProps {
  type: BackgroundType;
  headX: MotionValue<number>;
  headY: MotionValue<number>;
  headZ?: MotionValue<number>;
  smoothingEnabled?: boolean;
  parallaxIntensity?: number;
  renderMode?: "gltf" | "splat";
  onCameraUpdate?: (cam: { x: number; y: number; z: number }, target: { x: number; y: number; z: number }) => void;
  debugCameraControls?: boolean;
}

export const BackgroundManager: React.FC<BackgroundManagerProps> = ({
  type,
  headX,
  headY,
  headZ,
  smoothingEnabled = false, // Default to OFF per user request
  parallaxIntensity = 50,
  renderMode = "gltf",
  onCameraUpdate,
  debugCameraControls = false,
}) => {
  console.log("BackgroundManager rendering type:", type);
  // Smooth the raw input
  const smoothX = useSpring(headX, { stiffness: 60, damping: 20 });
  const smoothY = useSpring(headY, { stiffness: 60, damping: 20 });
  const smoothZ = useSpring(headZ || 0, { stiffness: 40, damping: 20 });

  // Use smoothed or raw based on setting
  const effectiveX = smoothingEnabled ? smoothX : headX;
  const effectiveY = smoothingEnabled ? smoothY : headY;
  const effectiveZ = smoothingEnabled ? smoothZ : headZ;

  // Transform to pixel offset
  const parallaxX = useTransform(effectiveX, (value) => value * parallaxIntensity);
  const parallaxY = useTransform(effectiveY, (value) => value * -parallaxIntensity);

  if (type === "original") {
    return (
      <>
        {/* visionOS-style background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-gray-800 via-gray-900 to-black z-0" />

        {/* Subtle particle/light effect in background */}
        <div className="absolute inset-0 z-0 opacity-20">
          {Array.from({ length: 8 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-48 h-48 rounded-full bg-gradient-to-r from-blue-400/30 to-purple-400/30 blur-3xl"
              initial={{
                x: Math.random() * 100 - 50 + "%",
                y: Math.random() * 100 - 50 + "%",
                scale: Math.random() * 0.5 + 0.5,
              }}
              animate={{
                x: [
                  Math.random() * 100 - 50 + "%",
                  Math.random() * 100 - 50 + "%",
                  Math.random() * 100 - 50 + "%",
                ],
                y: [
                  Math.random() * 100 - 50 + "%",
                  Math.random() * 100 - 50 + "%",
                  Math.random() * 100 - 50 + "%",
                ],
              }}
              transition={{
                duration: 20 + Math.random() * 30,
                repeat: Infinity,
                repeatType: "reverse",
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
      </>
    );
  }

  // Mixed Reality Mode (formerly Livingroom) - Uses standalone viewer
  if (type === "mixed-reality") {
    return (
      <div className="absolute inset-0 z-0 bg-black">
        <StandaloneSplatViewer
          url="Livingroom-in-Taipei.metric.ply"
          className="w-full h-full"
          headX={effectiveX}
          headY={effectiveY}
          headZ={effectiveZ}
          onCameraUpdate={onCameraUpdate}
          debugCameraControls={debugCameraControls}
        />
      </div>
    );
  }

  const imageSrc = type === "bg" ? "media/bg.webp" : "media/bg1.webp";

  return (
    <div className="absolute inset-0 z-0">
      <motion.img
        key={imageSrc}
        src={imageSrc}
        alt="Background"
        className="w-full h-full object-cover"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1 }}
      />
      <div className="absolute inset-0 bg-black/60" />{" "}
      {/* Darker overlay for better text contrast */}
    </div>
  );
};
