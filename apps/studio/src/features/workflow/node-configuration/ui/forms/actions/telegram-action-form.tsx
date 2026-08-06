"use client";

import type { ChangeEventHandler } from "react";
import { Field, FieldLabel } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import { TEXT_LIMITS } from "@/entities/workflow";
import { CredentialSelectField } from "../../fields/credential-select-field";
import type { NodeFormProps } from "../../form-props";

export function TelegramActionForm({ data, onChange }: NodeFormProps<"telegram_action">) {
  const handleChatIdChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    onChange({ ...data, chat_id: event.currentTarget.value });
  };

  const handleMessageChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
    onChange({ ...data, message_template: event.currentTarget.value });
  };

  return (
    <>
      <CredentialSelectField
        id="telegram-credential"
        onChange={(credentialId) => {
          onChange({ ...data, credential_id: credentialId });
        }}
        type="telegram_bot"
        value={data.credential_id}
      />

      <Field>
        <FieldLabel htmlFor="telegram-chat-id">Chat ID</FieldLabel>

        <Input
          id="telegram-chat-id"
          maxLength={TEXT_LIMITS.telegramChatId}
          onChange={handleChatIdChange}
          placeholder="-100123..."
          value={data.chat_id}
        />
      </Field>

      <Field>
        <HintedFieldLabel hint={"Placeholders: {kind}, {camera_id}, {ts}."} htmlFor="telegram-message">
          Message template
        </HintedFieldLabel>

        <Textarea
          id="telegram-message"
          maxLength={TEXT_LIMITS.telegramMessage}
          onChange={handleMessageChange}
          rows={3}
          value={data.message_template}
        />
      </Field>
    </>
  );
}
