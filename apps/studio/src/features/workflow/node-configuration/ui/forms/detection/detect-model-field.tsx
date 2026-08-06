"use client";

import { Field, FieldDescription, FieldLabel } from "@/shared/ui/field";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { isModelMissing, useInferenceModels } from "@/entities/inference-model";

interface DetectModelFieldProps {
  modelId: string | null;
  onChange: (modelId: string | null) => void;
}

export function DetectModelField({ modelId, onChange }: DetectModelFieldProps) {
  const models = useInferenceModels();

  const { isLoading } = models;
  const isUnavailable = isModelMissing(modelId, models.data);
  const isInvalid = isUnavailable || models.isError;

  const modelItems = [
    { label: isLoading ? "Loading models…" : "Select a model", value: null },
    ...(isUnavailable ? [{ label: `${modelId} (unavailable)`, value: modelId }] : []),
    ...(models.data?.map((model) => {
      return { label: model.name, value: model.id };
    }) ?? []),
  ];

  return (
    <Field data-invalid={isInvalid}>
      <FieldLabel htmlFor="detect-model">Model</FieldLabel>

      <Select
        disabled={isLoading || models.data?.length === 0}
        items={modelItems}
        onValueChange={onChange}
        value={modelId}
      >
        <SelectTrigger aria-invalid={isInvalid ? true : undefined} className="w-full" id="detect-model">
          <SelectValue />
        </SelectTrigger>

        <SelectContent>
          <SelectGroup>
            {modelItems.map((model) => {
              return (
                <SelectItem
                  disabled={model.value === null || (isUnavailable && model.value === modelId)}
                  key={model.value ?? "placeholder"}
                  value={model.value}
                >
                  {model.label}
                </SelectItem>
              );
            })}
          </SelectGroup>
        </SelectContent>
      </Select>

      {models.isError ? <FieldDescription>Couldn't load models.</FieldDescription> : null}

      {models.data?.length === 0 ? <FieldDescription>No usable models installed.</FieldDescription> : null}

      {isUnavailable ? <FieldDescription>Selected model is not installed.</FieldDescription> : null}
    </Field>
  );
}
