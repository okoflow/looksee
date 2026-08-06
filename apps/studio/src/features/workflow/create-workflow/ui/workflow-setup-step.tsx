"use client";

import { ArrowLeftIcon } from "lucide-react";
import type { UseFormReturn } from "react-hook-form";
import { Button } from "@/shared/ui/button";
import { DialogClose, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import type { WorkflowSetup } from "@/entities/workflow";
import type { PresetParams, WorkflowPreset } from "../config/presets";
import { PresetParamField } from "./preset-param-field";

interface WorkflowSetupStepProps {
  form: UseFormReturn<WorkflowSetup>;
  isPending: boolean;
  onBack: () => void;
  onParamChange: (key: string, value: string) => void;
  onSubmit: (values: WorkflowSetup) => void;
  params: PresetParams;
  preset: WorkflowPreset | null;
}

export function WorkflowSetupStep({
  form,
  isPending,
  onBack,
  onParamChange,
  onSubmit,
  params,
  preset,
}: WorkflowSetupStepProps) {
  return (
    <>
      <DialogHeader>
        <DialogTitle>{preset === null ? "Blank workflow" : preset.title}</DialogTitle>

        <DialogDescription>
          {preset === null
            ? "You'll build the flow in the editor."
            : "A ready-made flow will appear in the editor — tune it there."}
        </DialogDescription>
      </DialogHeader>

      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FieldGroup>
          <Field data-invalid={form.formState.errors.name !== undefined}>
            <FieldLabel htmlFor="workflow-name">Name</FieldLabel>

            <Input
              id="workflow-name"
              placeholder="PPE on Gate 1"
              {...form.register("name")}
              aria-invalid={form.formState.errors.name === undefined ? undefined : true}
            />

            {form.formState.errors.name === undefined ? null : (
              <FieldDescription>{form.formState.errors.name.message}</FieldDescription>
            )}
          </Field>

          <Field>
            <FieldLabel htmlFor="workflow-description">Description (optional)</FieldLabel>

            <Textarea
              id="workflow-description"
              placeholder="What does this workflow do?"
              {...form.register("description")}
            />
          </Field>

          {preset?.fields.map((field) => {
            return (
              <PresetParamField field={field} key={field.key} onChange={onParamChange} value={params[field.key]} />
            );
          })}
        </FieldGroup>

        {preset?.hint ? <p className="mt-3 text-muted-foreground text-xs">{preset.hint}</p> : null}

        <DialogFooter className="mt-4">
          <Button onClick={onBack} type="button" variant="ghost">
            <ArrowLeftIcon data-icon="inline-start" />
            Back
          </Button>

          <DialogClose render={<Button type="button" variant="ghost" />}>Cancel</DialogClose>

          <Button disabled={isPending} type="submit">
            Create
          </Button>
        </DialogFooter>
      </form>
    </>
  );
}
