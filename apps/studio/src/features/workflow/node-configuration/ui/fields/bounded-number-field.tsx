"use client";

import type { ChangeEventHandler } from "react";
import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Input } from "@/shared/ui/input";
import type { NumericLimits } from "@/entities/workflow";
import { clampToLimits, isDraftNumberValid, parseDraftNumber } from "../../lib/draft-number";
import { useDraftValue } from "../../lib/use-draft-value";

interface BoundedNumberFieldProps {
  description?: string;
  id: string;
  isInteger?: boolean;
  label: string;
  limits: NumericLimits;
  onCommit: (value: number) => void;
  step?: number;
  value: number;
}

export function BoundedNumberField({
  description,
  id,
  isInteger = false,
  label,
  limits,
  onCommit,
  step = 1,
  value,
}: BoundedNumberFieldProps) {
  const { draft, handleKeyDown, resetDraft, setDraft } = useDraftValue(String(value));

  const parsed = parseDraftNumber(draft);
  const isInvalid = !isDraftNumberValid(parsed, limits, isInteger);

  const handleCommit = () => {
    if (parsed === null) {
      resetDraft();

      return;
    }

    const bounded = clampToLimits(isInteger ? Math.round(parsed) : parsed, limits);

    setDraft(String(bounded));

    if (bounded !== value) {
      onCommit(bounded);
    }
  };

  const handleChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    setDraft(event.currentTarget.value);
  };

  return (
    <Field data-invalid={isInvalid}>
      <HintedFieldLabel hint={description} htmlFor={id}>
        {label}
      </HintedFieldLabel>

      <Input
        aria-invalid={isInvalid ? true : undefined}
        id={id}
        max={limits.max}
        min={limits.min}
        onBlur={handleCommit}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        step={step}
        type="number"
        value={draft}
      />
    </Field>
  );
}
