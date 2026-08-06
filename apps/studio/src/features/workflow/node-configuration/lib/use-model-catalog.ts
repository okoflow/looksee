"use client";

import { eventKindsOfModels, modelsByIds, objectClassesOfModels, useInferenceModels } from "@/entities/inference-model";

interface ModelCatalog {
  eventKinds: string[];
  fallbackDescription: string;
  isLoading: boolean;
  objectClasses: string[];
}

function catalogFallbackDescription(hasCatalogError: boolean, hasUpstreamModel: boolean): string {
  if (hasCatalogError) {
    return "Model catalog unavailable. Enter manually.";
  }

  if (!hasUpstreamModel) {
    return "Connect a configured Detect node or enter manually.";
  }

  return "No values from the connected model. Enter manually.";
}

export function useModelCatalog(modelIds: readonly string[]): ModelCatalog {
  const models = useInferenceModels();

  const upstreamModels = modelsByIds(models.data ?? [], modelIds);
  const hasUpstreamModel = modelIds.length > 0;

  return {
    eventKinds: eventKindsOfModels(upstreamModels),
    fallbackDescription: catalogFallbackDescription(models.isError, hasUpstreamModel),
    isLoading: models.isLoading && hasUpstreamModel,
    objectClasses: objectClassesOfModels(upstreamModels),
  };
}
