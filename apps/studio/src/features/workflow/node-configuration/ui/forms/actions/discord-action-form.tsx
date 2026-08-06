"use client";

import type { ChangeEventHandler } from "react";
import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Textarea } from "@/shared/ui/textarea";
import { TEXT_LIMITS } from "@/entities/workflow";
import { CredentialSelectField } from "../../fields/credential-select-field";
import type { NodeFormProps } from "../../form-props";

export function DiscordActionForm({ data, onChange }: NodeFormProps<"discord_action">) {
  const handleMessageChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
    onChange({ ...data, message_template: event.currentTarget.value });
  };

  return (
    <>
      <CredentialSelectField
        id="discord-credential"
        onChange={(credentialId) => {
          onChange({ ...data, credential_id: credentialId });
        }}
        type="discord_webhook"
        value={data.credential_id}
      />

      <Field>
        <HintedFieldLabel hint={"Placeholders: {kind}, {camera_id}, {ts}."} htmlFor="discord-message">
          Message template
        </HintedFieldLabel>

        <Textarea
          id="discord-message"
          maxLength={TEXT_LIMITS.discordMessage}
          onChange={handleMessageChange}
          rows={3}
          value={data.message_template}
        />
      </Field>
    </>
  );
}
