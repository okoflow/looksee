"use client";

import { Field, FieldDescription } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/toggle-group";
import { eventKindLabel } from "@/entities/inference-model";

interface DetectEventsFieldProps {
  eventKinds: string[];
  hasSelectedModel: boolean;
  onChange: (eventKinds: string[]) => void;
  value: string[];
}

export function DetectEventsField({ eventKinds, hasSelectedModel, onChange, value }: DetectEventsFieldProps) {
  return (
    <Field>
      <HintedFieldLabel hint="None selected: all events pass." id="detect-events-label">
        Events
      </HintedFieldLabel>

      {eventKinds.length > 0 ? (
        <ToggleGroup
          aria-labelledby="detect-events-label"
          className="flex-wrap justify-start"
          multiple
          onValueChange={onChange}
          size="sm"
          value={value}
          variant="outline"
        >
          {eventKinds.map((kind) => {
            return (
              <ToggleGroupItem key={kind} value={kind}>
                {eventKindLabel(kind)}
              </ToggleGroupItem>
            );
          })}
        </ToggleGroup>
      ) : (
        <FieldDescription>
          {hasSelectedModel ? "This model exposes no event kinds." : "Select a model first."}
        </FieldDescription>
      )}
    </Field>
  );
}
