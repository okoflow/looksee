"use client";

import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { CREDENTIAL_TYPE_LABELS, type CredentialType, useCredentials } from "@/entities/credential";

interface CredentialSelectFieldProps {
  id: string;
  onChange: (credentialId: string) => void;
  type: CredentialType;
  value: string;
}

export function CredentialSelectField({ id, onChange, type, value }: CredentialSelectFieldProps) {
  const credentials = useCredentials();

  const options = (credentials.data ?? []).filter((credential) => {
    return credential.type === type;
  });

  const hint = `Stored ${CREDENTIAL_TYPE_LABELS[type]} credentials; manage them on the Credentials page.`;

  if (!credentials.isPending && options.length === 0) {
    return (
      <Field>
        <HintedFieldLabel hint={hint} htmlFor={id}>
          Credential
        </HintedFieldLabel>

        <p className="text-muted-foreground text-sm">
          No {CREDENTIAL_TYPE_LABELS[type]} credentials yet — add one on the{" "}
          <a className="underline underline-offset-2" href="/credentials" rel="noreferrer" target="_blank">
            Credentials
          </a>{" "}
          page.
        </p>
      </Field>
    );
  }

  const items = options.map((credential) => {
    return { value: credential.id, label: credential.name };
  });

  return (
    <Field>
      <HintedFieldLabel hint={hint} htmlFor={id}>
        Credential
      </HintedFieldLabel>

      <Select
        items={items}
        onValueChange={(next: string | null) => {
          if (next !== null) {
            onChange(next);
          }
        }}
        value={value === "" ? null : value}
      >
        <SelectTrigger className="w-full" id={id}>
          <SelectValue placeholder="Select a credential" />
        </SelectTrigger>

        <SelectContent>
          {items.map((item) => {
            return (
              <SelectItem key={item.value} value={item.value}>
                {item.label}
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </Field>
  );
}
