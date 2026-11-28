import type { NodeDefinition, PaletteCategory } from "@/features/workflow/node-configuration";
import { PALETTE_CATEGORY_LABELS } from "../config/palette-sections";
import { PaletteItem } from "./palette-item";

interface PaletteSectionProps {
  category: PaletteCategory;
  items: NodeDefinition[];
  licensedFeatures: string[];
}

function isLocked(definition: NodeDefinition, licensedFeatures: string[]) {
  return definition.feature !== undefined && !licensedFeatures.includes(definition.feature);
}

export function PaletteSection({ category, items, licensedFeatures }: PaletteSectionProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-muted-foreground px-1 text-xs tracking-wide uppercase">
        {PALETTE_CATEGORY_LABELS[category]}
      </span>

      <div className="flex flex-col gap-1.5">
        {items.map((definition) => {
          return (
            <PaletteItem
              definition={definition}
              key={definition.kind}
              locked={isLocked(definition, licensedFeatures)}
            />
          );
        })}
      </div>
    </div>
  );
}
