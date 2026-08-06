import type { InferenceModel } from "./schema";

function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values)).sort((left, right) => {
    return left.localeCompare(right);
  });
}

export function modelsByIds(models: readonly InferenceModel[], ids: readonly string[]): InferenceModel[] {
  const idSet = new Set(ids);

  return models.filter((model) => {
    return idSet.has(model.id);
  });
}

export function modelById(
  models: readonly InferenceModel[] | undefined,
  modelId: string | null
): InferenceModel | undefined {
  return models?.find((model) => {
    return model.id === modelId;
  });
}

export function isModelMissing(modelId: string | null, models: readonly InferenceModel[] | undefined): boolean {
  if (modelId === null || models === undefined) {
    return false;
  }

  return modelById(models, modelId) === undefined;
}

export function eventKindsOfModel(model: InferenceModel): string[] {
  return model.classes.flatMap((modelClass) => {
    return modelClass.event_kind ? [modelClass.event_kind] : [];
  });
}

export function eventKindsOfModels(models: readonly InferenceModel[]): string[] {
  return uniqueSorted(models.flatMap(eventKindsOfModel));
}

export function objectClassesOfModels(models: readonly InferenceModel[]): string[] {
  return uniqueSorted(
    models.flatMap((model) => {
      return model.classes.map((modelClass) => {
        return modelClass.label;
      });
    })
  );
}
