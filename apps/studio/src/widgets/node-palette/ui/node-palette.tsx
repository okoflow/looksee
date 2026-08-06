"use client";

import { SearchIcon } from "lucide-react";
import { type ChangeEventHandler, useState } from "react";
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/shared/ui/input-group";
import { ScrollArea } from "@/shared/ui/scroll-area";
import { useEntitlements } from "@/entities/entitlement";
import { NODE_DEFINITIONS } from "@/features/workflow/node-configuration";
import { PALETTE_CATEGORY_ORDER } from "../config/palette-sections";
import { matchesNodeQuery } from "../lib/node-search";
import { PaletteSection } from "./palette-section";

function sectionsForQuery(query: string) {
  return PALETTE_CATEGORY_ORDER.map((category) => {
    return {
      category,
      items: NODE_DEFINITIONS.filter((definition) => {
        return definition.paletteCategory === category && matchesNodeQuery(definition, query);
      }),
    };
  }).filter((section) => {
    return section.items.length > 0;
  });
}

export function NodePalette() {
  const [query, setQuery] = useState("");
  const entitlements = useEntitlements();

  const sections = sectionsForQuery(query);
  const licensedFeatures = entitlements.data?.features ?? [];

  const handleQueryChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    setQuery(event.currentTarget.value);
  };

  return (
    <aside className="flex h-full w-editor-palette shrink-0 flex-col overflow-hidden rounded-xl border bg-card">
      <div className="flex h-12 items-center border-b px-4 font-medium text-sm">Nodes</div>

      <div className="border-b p-3">
        <InputGroup>
          <InputGroupInput
            aria-label="Search nodes"
            onChange={handleQueryChange}
            placeholder="Search nodes…"
            value={query}
          />

          <InputGroupAddon>
            <SearchIcon />
          </InputGroupAddon>
        </InputGroup>
      </div>

      <ScrollArea className="min-h-0 flex-1">
        {sections.length > 0 ? (
          <div className="flex flex-col gap-4 p-3">
            {sections.map((section) => {
              return (
                <PaletteSection
                  category={section.category}
                  items={section.items}
                  key={section.category}
                  licensedFeatures={licensedFeatures}
                />
              );
            })}
          </div>
        ) : (
          <div className="p-6 text-center text-muted-foreground text-sm">No matching nodes.</div>
        )}
      </ScrollArea>
    </aside>
  );
}
