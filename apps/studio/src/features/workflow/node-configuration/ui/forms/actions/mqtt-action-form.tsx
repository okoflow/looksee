"use client";

import type { ChangeEventHandler } from "react";
import { Field, FieldLabel } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import { TEXT_LIMITS } from "@/entities/workflow";
import { CredentialSelectField } from "../../fields/credential-select-field";
import type { NodeFormProps } from "../../form-props";

export function MqttActionForm({ data, onChange }: NodeFormProps<"mqtt_action">) {
  const handleTopicChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    onChange({ ...data, topic: event.currentTarget.value });
  };

  const handlePayloadChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
    onChange({ ...data, payload_template: event.currentTarget.value });
  };

  return (
    <>
      <CredentialSelectField
        id="mqtt-credential"
        onChange={(credentialId) => {
          onChange({ ...data, credential_id: credentialId });
        }}
        type="mqtt"
        value={data.credential_id}
      />

      <Field>
        <FieldLabel htmlFor="mqtt-topic">Topic</FieldLabel>

        <Input
          id="mqtt-topic"
          maxLength={TEXT_LIMITS.mqttTopic}
          onChange={handleTopicChange}
          placeholder="looksee/events"
          value={data.topic}
        />
      </Field>

      <Field>
        <HintedFieldLabel
          hint={"Placeholders: {kind}, {camera_id}, {ts}, {count}, {snapshot_url}."}
          htmlFor="mqtt-payload"
        >
          Payload template
        </HintedFieldLabel>

        <Textarea
          id="mqtt-payload"
          maxLength={TEXT_LIMITS.mqttPayload}
          onChange={handlePayloadChange}
          placeholder="Empty = event JSON"
          rows={3}
          value={data.payload_template}
        />
      </Field>
    </>
  );
}
