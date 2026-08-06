"use client";

import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";

export interface SelectOption<T extends string> {
  description?: string;
  label: string;
  value: T;
}

interface SelectFieldProps<T extends string> {
  description?: string;
  id: string;
  label: string;
  onValueChange: (value: T) => void;
  options: readonly SelectOption<T>[];
  value: T;
}

export function SelectField<T extends string>({
  description,
  id,
  label,
  onValueChange,
  options,
  value,
}: SelectFieldProps<T>) {
  const handleValueChange = (next: T | null) => {
    if (next !== null) {
      onValueChange(next);
    }
  };

  return (
    <Field>
      <HintedFieldLabel hint={description} htmlFor={id}>
        {label}
      </HintedFieldLabel>

      <Select items={options} onValueChange={handleValueChange} value={value}>
        <SelectTrigger className="w-full" id={id}>
          <SelectValue />
        </SelectTrigger>

        <SelectContent>
          <SelectGroup>
            {options.map((option) => {
              if (option.description === undefined) {
                return (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                );
              }

              return (
                <SelectItem className="items-start" key={option.value} value={option.value}>
                  <span className="flex flex-col gap-0.5">
                    <span>{option.label}</span>

                    <span className="text-muted-foreground text-xs">{option.description}</span>
                  </span>
                </SelectItem>
              );
            })}
          </SelectGroup>
        </SelectContent>
      </Select>
    </Field>
  );
}
