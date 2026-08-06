"use client";

import { PencilIcon } from "lucide-react";
import { DialogDescription, DialogHeader, DialogTitle } from "@/shared/ui/dialog";
import { WORKFLOW_PRESETS, type WorkflowPreset } from "../config/presets";
import { PresetCard } from "./preset-card";

interface PresetGalleryStepProps {
  onSelectPreset: (preset: WorkflowPreset | null) => void;
}

export function PresetGalleryStep({ onSelectPreset }: PresetGalleryStepProps) {
  const handleSelectBlank = () => {
    onSelectPreset(null);
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle>New workflow</DialogTitle>

        <DialogDescription>Start from a ready-made scenario or an empty canvas.</DialogDescription>
      </DialogHeader>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <PresetCard
          description="Empty canvas — build the flow yourself in the editor."
          icon={<PencilIcon className="size-4" />}
          onClick={handleSelectBlank}
          title="Blank workflow"
        />

        {WORKFLOW_PRESETS.map((item) => {
          const Icon = item.icon;

          const handleSelect = () => {
            onSelectPreset(item);
          };

          return (
            <PresetCard
              description={item.description}
              icon={<Icon className="size-4" />}
              key={item.id}
              onClick={handleSelect}
              title={item.title}
              vertical={item.vertical}
            />
          );
        })}
      </div>
    </>
  );
}
