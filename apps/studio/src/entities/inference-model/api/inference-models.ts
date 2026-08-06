import { api } from "@/shared/api";
import { inferenceModelsSchema } from "../model/schema";

export async function listInferenceModels() {
  const payload: unknown = await api.get("models").json();

  return inferenceModelsSchema.parse(payload);
}
