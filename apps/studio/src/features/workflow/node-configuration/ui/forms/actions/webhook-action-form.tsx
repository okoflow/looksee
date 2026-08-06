"use client";

import type { ChangeEventHandler } from "react";
import { Field, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { TEXT_LIMITS } from "@/entities/workflow";
import { SelectField, type SelectOption } from "../../fields/select-field";
import type { NodeFormProps } from "../../form-props";

type WebhookMethod = NodeFormProps<"webhook_action">["data"]["method"];

const WEBHOOK_METHOD_OPTIONS: readonly SelectOption<WebhookMethod>[] = [
  { label: "POST", value: "POST" },
  { label: "GET", value: "GET" },
  { label: "PUT", value: "PUT" },
];

export function WebhookActionForm({ data, onChange }: NodeFormProps<"webhook_action">) {
  const handleUrlChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    onChange({ ...data, url: event.currentTarget.value });
  };

  const handleMethodChange = (method: WebhookMethod) => {
    onChange({ ...data, method });
  };

  return (
    <>
      <Field>
        <FieldLabel htmlFor="webhook-url">URL</FieldLabel>

        <Input
          id="webhook-url"
          maxLength={TEXT_LIMITS.sourceUrl}
          onChange={handleUrlChange}
          placeholder="https://example.com/hook"
          value={data.url}
        />
      </Field>

      <SelectField
        id="webhook-method"
        label="Method"
        onValueChange={handleMethodChange}
        options={WEBHOOK_METHOD_OPTIONS}
        value={data.method}
      />
    </>
  );
}
