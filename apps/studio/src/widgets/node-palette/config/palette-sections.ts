import type { PaletteCategory } from "@/features/workflow/node-configuration";

export const PALETTE_CATEGORY_LABELS: Record<PaletteCategory, string> = {
  source: "Sources",
  detection: "Detection",
  logic: "Logic",
  object: "Object",
  spatial: "Spatial",
  temporal: "Temporal",
  action: "Actions",
};

export const PALETTE_CATEGORY_ORDER: PaletteCategory[] = [
  "source",
  "detection",
  "logic",
  "object",
  "spatial",
  "temporal",
  "action",
];
