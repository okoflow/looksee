import type { ChangeEventHandler } from "react";
import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Input } from "@/shared/ui/input";
import type { PresetField } from "../config/presets";

interface PresetParamFieldProps {
  field: PresetField;
  onChange: (key: string, value: string) => void;
  value: string | number | undefined;
}

export function PresetParamField({ field, onChange, value }: PresetParamFieldProps) {
  const id = `preset-${field.key}`;

  const handleChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    onChange(field.key, event.currentTarget.value);
  };

  return (
    <Field>
      <HintedFieldLabel hint={field.description} htmlFor={id}>
        {field.label}
      </HintedFieldLabel>

      <Input
        id={id}
        max={field.max}
        min={field.min}
        onChange={handleChange}
        type="number"
        value={value ?? field.defaultValue}
      />
    </Field>
  );
}
