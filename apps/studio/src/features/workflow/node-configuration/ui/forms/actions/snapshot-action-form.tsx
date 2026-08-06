"use client";

import { Field, FieldContent } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Switch } from "@/shared/ui/switch";
import type { NodeFormProps } from "../../form-props";

export function SnapshotActionForm({ data, onChange }: NodeFormProps<"snapshot_action">) {
  const handleAnnotateChange = (annotate: boolean) => {
    onChange({ ...data, annotate });
  };

  return (
    <Field orientation="horizontal">
      <FieldContent>
        <HintedFieldLabel
          hint="Burns boxes and labels into the saved image. Off saves the clean frame."
          htmlFor="snapshot-annotate"
        >
          Draw detection boxes
        </HintedFieldLabel>
      </FieldContent>

      <Switch checked={data.annotate} id="snapshot-annotate" onCheckedChange={handleAnnotateChange} />
    </Field>
  );
}
