"use client";

import type { ChangeEventHandler } from "react";
import { arraysShallowEqual } from "@/shared/lib/arrays-shallow-equal";
import {
  Combobox,
  ComboboxChip,
  ComboboxChips,
  ComboboxChipsInput,
  ComboboxCollection,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxItem,
  ComboboxList,
  useComboboxAnchor,
} from "@/shared/ui/combobox";
import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Input } from "@/shared/ui/input";
import { parseClassList, serializeClassList } from "../../../lib/class-list";
import { useDraftValue } from "../../../lib/use-draft-value";
import { useModelCatalog } from "../../../lib/use-model-catalog";
import type { NodeFormProps } from "../../form-props";

interface ClassFilterFormProps extends NodeFormProps<"class_filter"> {
  modelIds: readonly string[];
}

export function ClassFilterForm({ data, modelIds, onChange }: ClassFilterFormProps) {
  const { fallbackDescription, isLoading, objectClasses } = useModelCatalog(modelIds);

  const handleClassesChange = (classes: string[]) => {
    onChange({ ...data, classes });
  };

  if (objectClasses.length === 0 && !isLoading) {
    return (
      <ManualClassesField
        classes={data.classes}
        fallbackDescription={fallbackDescription}
        onCommit={handleClassesChange}
      />
    );
  }

  return (
    <CatalogClassesField
      catalogClasses={objectClasses}
      classes={data.classes}
      isLoading={isLoading}
      onChange={handleClassesChange}
    />
  );
}

interface CatalogClassesFieldProps {
  catalogClasses: string[];
  classes: string[];
  isLoading: boolean;
  onChange: (classes: string[]) => void;
}

function CatalogClassesField({ catalogClasses, classes, isLoading, onChange }: CatalogClassesFieldProps) {
  const anchor = useComboboxAnchor();

  return (
    <Field>
      <HintedFieldLabel hint="Any match passes; empty = any class." htmlFor="class-filter-classes">
        Classes
      </HintedFieldLabel>

      <Combobox items={catalogClasses} multiple onValueChange={onChange} value={classes}>
        <ComboboxChips ref={anchor}>
          {classes.map((className) => {
            return <ComboboxChip key={className}>{className}</ComboboxChip>;
          })}

          <ComboboxChipsInput
            disabled={isLoading}
            id="class-filter-classes"
            placeholder={placeholderText(isLoading, classes.length)}
          />
        </ComboboxChips>

        <ComboboxContent anchor={anchor}>
          <ComboboxEmpty>No matching classes.</ComboboxEmpty>

          <ComboboxList>
            <ComboboxCollection>
              {(className: string) => {
                return (
                  <ComboboxItem key={className} value={className}>
                    {className}
                  </ComboboxItem>
                );
              }}
            </ComboboxCollection>
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
    </Field>
  );
}

function placeholderText(isLoading: boolean, selectedCount: number): string {
  if (isLoading) {
    return "Loading model…";
  }

  return selectedCount === 0 ? "Add class…" : "";
}

interface ManualClassesFieldProps {
  classes: string[];
  fallbackDescription: string;
  onCommit: (classes: string[]) => void;
}

function ManualClassesField({ classes, fallbackDescription, onCommit }: ManualClassesFieldProps) {
  const { draft, handleKeyDown, setDraft } = useDraftValue(serializeClassList(classes));

  const handleChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    setDraft(event.currentTarget.value);
  };

  const handleCommit = () => {
    const next = parseClassList(draft);

    setDraft(serializeClassList(next));

    if (!arraysShallowEqual(next, classes)) {
      onCommit(next);
    }
  };

  return (
    <Field>
      <HintedFieldLabel
        hint={`Comma-separated; any match passes. ${fallbackDescription}`}
        htmlFor="class-filter-classes"
      >
        Classes
      </HintedFieldLabel>

      <Input
        id="class-filter-classes"
        onBlur={handleCommit}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="person, car, dog"
        value={draft}
      />
    </Field>
  );
}
