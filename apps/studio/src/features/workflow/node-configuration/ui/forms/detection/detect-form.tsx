"use client";

import { eventKindsOfModel, modelById, useInferenceModels } from "@/entities/inference-model";
import { CONFIDENCE_THRESHOLD_LIMITS, INFERENCE_FPS_LIMITS } from "@/entities/workflow";
import { CONFIDENCE_THRESHOLD_STEP } from "../../../config/node-catalog";
import { BoundedNumberField } from "../../fields/bounded-number-field";
import type { NodeFormProps } from "../../form-props";
import { DetectEventsField } from "./detect-events-field";
import { DetectModelField } from "./detect-model-field";

export function DetectForm({ data, onChange }: NodeFormProps<"detect">) {
  const models = useInferenceModels();

  const selectedModel = modelById(models.data, data.model_id);

  const eventKinds = Array.from(
    new Set([...(selectedModel ? eventKindsOfModel(selectedModel) : []), ...data.event_kinds])
  );

  const handleModelChange = (modelId: string | null) => {
    const model = modelById(models.data, modelId);

    if (!model) {
      return;
    }

    const supportedEventKinds = new Set(eventKindsOfModel(model));

    onChange({
      ...data,
      model_id: model.id,
      event_kinds: data.event_kinds.filter((kind) => {
        return supportedEventKinds.has(kind);
      }),
      confidence_threshold: model.recommended_confidence_threshold ?? data.confidence_threshold,
    });
  };

  const handleEventKindsChange = (eventKindsValue: string[]) => {
    onChange({ ...data, event_kinds: eventKindsValue });
  };

  const handleConfidenceCommit = (confidenceThreshold: number) => {
    onChange({ ...data, confidence_threshold: confidenceThreshold });
  };

  const handleInferenceFpsCommit = (inferenceFps: number) => {
    onChange({ ...data, inference_fps: inferenceFps });
  };

  return (
    <>
      <DetectModelField modelId={data.model_id} onChange={handleModelChange} />

      <DetectEventsField
        eventKinds={eventKinds}
        hasSelectedModel={selectedModel !== undefined}
        onChange={handleEventKindsChange}
        value={data.event_kinds}
      />

      <BoundedNumberField
        description="Detections below this confidence are dropped (0–1)."
        id="detect-confidence"
        label="Confidence"
        limits={CONFIDENCE_THRESHOLD_LIMITS}
        onCommit={handleConfidenceCommit}
        step={CONFIDENCE_THRESHOLD_STEP}
        value={data.confidence_threshold}
      />

      <BoundedNumberField
        description="How many frames per second run through the model."
        id="detect-fps"
        isInteger
        label="Checks per second"
        limits={INFERENCE_FPS_LIMITS}
        onCommit={handleInferenceFpsCommit}
        value={data.inference_fps}
      />
    </>
  );
}
