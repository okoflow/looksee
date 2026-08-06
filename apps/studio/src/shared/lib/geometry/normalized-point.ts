import { z } from "zod";
import { clamp } from "@/shared/lib/number";

const COORDINATE_DECIMALS = 3;
const COORDINATE_SCALE = 10 ** COORDINATE_DECIMALS;

const normalizedCoordinateSchema = z.number().min(0).max(1);

export const normalizedPointSchema = z.tuple([normalizedCoordinateSchema, normalizedCoordinateSchema]);

export const normalizedPolygonSchema = z.array(normalizedPointSchema);

export type NormalizedPoint = z.infer<typeof normalizedPointSchema>;
export type NormalizedPolygon = z.infer<typeof normalizedPolygonSchema>;

function roundCoordinate(value: number): number {
  return Math.round(clamp(value, 0, 1) * COORDINATE_SCALE) / COORDINATE_SCALE;
}

interface PointerPosition {
  clientX: number;
  clientY: number;
}

export function pointerToNormalizedPoint(pointer: PointerPosition, bounds: DOMRect): NormalizedPoint {
  return [
    roundCoordinate((pointer.clientX - bounds.left) / bounds.width),
    roundCoordinate((pointer.clientY - bounds.top) / bounds.height),
  ];
}

export function polygonToSvgPoints(polygon: NormalizedPolygon, width: number, height: number): string {
  return polygon
    .map(([x, y]) => {
      return `${x * width},${y * height}`;
    })
    .join(" ");
}
