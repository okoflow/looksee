import { cn } from "@/shared/lib/cn";
import { type NormalizedPolygon, polygonToSvgPoints } from "@/shared/lib/geometry";

interface ShapeOverlayProps {
  className?: string;
  points: NormalizedPolygon;
  shape: "line" | "polygon";
}

export function ShapeOverlay({ className, points, shape }: ShapeOverlayProps) {
  if (points.length < 2) {
    return null;
  }

  const svgPoints = polygonToSvgPoints(points, 1, 1);

  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 h-full w-full"
      preserveAspectRatio="none"
      viewBox="0 0 1 1"
    >
      {shape === "polygon" ? (
        <polygon
          className={cn("fill-primary/15 stroke-2 stroke-primary", className)}
          points={svgPoints}
          vectorEffect="non-scaling-stroke"
        />
      ) : (
        <polyline
          className={cn("fill-none stroke-2 stroke-primary", className)}
          points={svgPoints}
          vectorEffect="non-scaling-stroke"
        />
      )}
    </svg>
  );
}
