"use client";

import type { ChangeEventHandler } from "react";
import { Field, FieldLabel } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import { TEXT_LIMITS } from "@/entities/workflow";
import { CredentialSelectField } from "../../fields/credential-select-field";
import type { NodeFormProps } from "../../form-props";

export function EmailActionForm({ data, onChange }: NodeFormProps<"email_action">) {
  const handleToChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    onChange({ ...data, to: event.currentTarget.value });
  };

  const handleSubjectChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    onChange({ ...data, subject_template: event.currentTarget.value });
  };

  const handleBodyChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
    onChange({ ...data, body_template: event.currentTarget.value });
  };

  return (
    <>
      <CredentialSelectField
        id="email-credential"
        onChange={(credentialId) => {
          onChange({ ...data, credential_id: credentialId });
        }}
        type="smtp"
        value={data.credential_id}
      />

      <Field>
        <FieldLabel htmlFor="email-to">To</FieldLabel>

        <Input
          id="email-to"
          maxLength={TEXT_LIMITS.emailTo}
          onChange={handleToChange}
          placeholder="alerts@example.com"
          type="email"
          value={data.to}
        />
      </Field>

      <Field>
        <FieldLabel htmlFor="email-subject">Subject</FieldLabel>

        <Input
          id="email-subject"
          maxLength={TEXT_LIMITS.emailSubject}
          onChange={handleSubjectChange}
          value={data.subject_template}
        />
      </Field>

      <Field>
        <HintedFieldLabel
          hint={"Placeholders: {kind}, {camera_id}, {ts}, {count}, {snapshot_url}."}
          htmlFor="email-body"
        >
          Body
        </HintedFieldLabel>

        <Textarea
          id="email-body"
          maxLength={TEXT_LIMITS.emailBody}
          onChange={handleBodyChange}
          rows={4}
          value={data.body_template}
        />
      </Field>
    </>
  );
}
