"use client";

import type { ChangeEventHandler } from "react";
import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Textarea } from "@/shared/ui/textarea";
import { TEXT_LIMITS } from "@/entities/workflow";
import { CredentialSelectField } from "../../fields/credential-select-field";
import type { NodeFormProps } from "../../form-props";

export function SlackActionForm({ data, onChange }: NodeFormProps<"slack_action">) {
  const handleMessageChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
    onChange({ ...data, message_template: event.currentTarget.value });
  };

  return (
    <>
      <CredentialSelectField
        id="slack-credential"
        onChange={(credentialId) => {
          onChange({ ...data, credential_id: credentialId });
        }}
        type="slack_webhook"
        value={data.credential_id}
      />

      <Field>
        <HintedFieldLabel hint={"Placeholders: {kind}, {camera_id}, {ts}."} htmlFor="slack-message">
          Message template
        </HintedFieldLabel>

        <Textarea
          id="slack-message"
          maxLength={TEXT_LIMITS.slackMessage}
          onChange={handleMessageChange}
          rows={3}
          value={data.message_template}
        />
      </Field>
    </>
  );
}
