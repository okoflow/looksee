"use client";

import type { ChangeEventHandler } from "react";
import { Field, FieldDescription, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import {
  SOURCE_TYPE_DESCRIPTIONS,
  SOURCE_TYPE_LABELS,
  type SourceType,
  sourceTypeSchema,
  TEXT_LIMITS,
} from "@/entities/workflow";
import { AssetPickerField } from "../../fields/asset-picker-field";
import { SelectField, type SelectOption } from "../../fields/select-field";
import type { NodeFormProps } from "../../form-props";

const URL_PLACEHOLDERS: Record<SourceType, string> = {
  rtsp: "rtsp://host:554/stream",
  rtmp: "rtmp://host/live/key",
  srt: "srt://host:9999",
  webrtc: "",
  whep: "https://host:8889/stream/whep",
  file: "",
};

const URL_DESCRIPTIONS: Partial<Record<SourceType, string>> = {
  whep: "WHEP endpoint of a remote WebRTC server.",
};

const SOURCE_TYPE_OPTIONS: readonly SelectOption<SourceType>[] = sourceTypeSchema.options.map((sourceType) => {
  return {
    description: SOURCE_TYPE_DESCRIPTIONS[sourceType],
    label: SOURCE_TYPE_LABELS[sourceType],
    value: sourceType,
  };
});

export function CameraSourceForm({ data, onChange }: NodeFormProps<"camera_source">) {
  const handleNameChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    onChange({ ...data, name: event.currentTarget.value });
  };

  const handleUrlChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    onChange({ ...data, url: event.currentTarget.value });
  };

  const handleAssetChange = (key: string) => {
    onChange({ ...data, url: key });
  };

  const handleSourceTypeChange = (sourceType: SourceType) => {
    if (sourceType === data.source_type) {
      return;
    }

    onChange({ ...data, source_type: sourceType, url: "" });
  };

  const isWebrtcSource = data.source_type === "webrtc";
  const isFileSource = data.source_type === "file";
  const isUrlSource = !(isWebrtcSource || isFileSource);

  return (
    <>
      <Field>
        <FieldLabel htmlFor="camera-name">Name</FieldLabel>

        <Input id="camera-name" maxLength={TEXT_LIMITS.cameraName} onChange={handleNameChange} value={data.name} />
      </Field>

      <SelectField
        id="camera-source-type"
        label="Source"
        onValueChange={handleSourceTypeChange}
        options={SOURCE_TYPE_OPTIONS}
        value={data.source_type}
      />

      {isWebrtcSource ? <FieldDescription>Start the workflow, then publish from Live.</FieldDescription> : null}

      {isFileSource ? <AssetPickerField id="camera-asset" onValueChange={handleAssetChange} value={data.url} /> : null}

      {isUrlSource ? (
        <Field>
          <FieldLabel htmlFor="camera-url">URL</FieldLabel>

          <Input
            id="camera-url"
            maxLength={TEXT_LIMITS.sourceUrl}
            onChange={handleUrlChange}
            placeholder={URL_PLACEHOLDERS[data.source_type]}
            value={data.url}
          />

          {URL_DESCRIPTIONS[data.source_type] ? (
            <FieldDescription>{URL_DESCRIPTIONS[data.source_type]}</FieldDescription>
          ) : null}
        </Field>
      ) : null}
    </>
  );
}
