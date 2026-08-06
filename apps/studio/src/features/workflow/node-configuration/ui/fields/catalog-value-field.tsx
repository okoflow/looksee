"use client";

import type { ChangeEventHandler } from "react";
import { Field, FieldDescription, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";

interface CatalogValueFieldProps {
  catalogOptions: string[];
  currentValue: string | null;
  fallbackDescription: string;
  formatOption?: (value: string) => string;
  id: string;
  isLoading: boolean;
  label: string;
  maxLength: number;
  normalizeManualValue: (value: string) => string;
  onChange: (value: string | null) => void;
}

export function CatalogValueField({
  catalogOptions,
  currentValue,
  fallbackDescription,
  formatOption = identity,
  id,
  isLoading,
  label,
  maxLength,
  normalizeManualValue,
  onChange,
}: CatalogValueFieldProps) {
  const isManualEntry = shouldUseManualEntry(isLoading, catalogOptions);
  const selectItems = [
    { label: isLoading ? "Loading model…" : "Not configured", value: null },
    ...withCurrentOption(catalogOptions, currentValue).map((option) => {
      return { label: formatOption(option), value: option };
    }),
  ];
  const isUnavailable = isUnavailableValue(currentValue, catalogOptions);

  const handleManualChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    const normalized = normalizeManualValue(event.currentTarget.value);

    onChange(normalized === "" ? null : normalized);
  };

  return (
    <Field data-invalid={isUnavailable}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>

      {isManualEntry ? (
        <Input
          id={id}
          maxLength={maxLength}
          onChange={handleManualChange}
          placeholder="Enter a value"
          value={currentValue ?? ""}
        />
      ) : (
        <Select disabled={isLoading} items={selectItems} onValueChange={onChange} value={currentValue}>
          <SelectTrigger aria-invalid={isUnavailable ? true : undefined} className="w-full" id={id}>
            <SelectValue />
          </SelectTrigger>

          <SelectContent>
            <SelectGroup>
              {selectItems.map((option) => {
                return (
                  <SelectItem key={option.value ?? "not-configured"} value={option.value}>
                    {option.label}
                  </SelectItem>
                );
              })}
            </SelectGroup>
          </SelectContent>
        </Select>
      )}

      {isManualEntry ? <FieldDescription>{fallbackDescription}</FieldDescription> : null}

      {isUnavailable ? <FieldDescription>Value unavailable for this model.</FieldDescription> : null}
    </Field>
  );
}

function identity(value: string): string {
  return value;
}

function shouldUseManualEntry(isLoading: boolean, options: string[]): boolean {
  return !isLoading && options.length === 0;
}

function isUnavailableValue(current: string | null, options: string[]): boolean {
  if (current === null || options.length === 0) {
    return false;
  }

  return !options.includes(current);
}

function withCurrentOption(options: string[], current: string | null): string[] {
  if (current === null || options.includes(current)) {
    return options;
  }

  return [current, ...options];
}
