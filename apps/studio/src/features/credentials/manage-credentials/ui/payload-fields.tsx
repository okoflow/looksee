"use client";

import { Field, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import type { CredentialType } from "@/entities/credential";
import { PAYLOAD_FIELDS } from "../config/payload-fields";

interface PayloadFieldsProps {
  draft: Record<string, string>;
  idPrefix: string;
  onChange: (draft: Record<string, string>) => void;
  type: CredentialType;
}

export function PayloadFields({ draft, idPrefix, onChange, type }: PayloadFieldsProps) {
  return (
    <>
      {PAYLOAD_FIELDS[type].map((field) => {
        const id = `${idPrefix}-${field.key}`;

        return (
          <Field key={field.key}>
            <FieldLabel htmlFor={id}>{field.label}</FieldLabel>

            <Input
              id={id}
              onChange={(event) => {
                onChange({ ...draft, [field.key]: event.currentTarget.value });
              }}
              placeholder={field.placeholder}
              required={field.required}
              type={field.kind}
              value={draft[field.key] ?? ""}
            />
          </Field>
        );
      })}
    </>
  );
}
