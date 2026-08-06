import { queryOptions, useQuery } from "@tanstack/react-query";
import { listInferenceModels } from "./inference-models";

const INFERENCE_MODEL_REFETCH_INTERVAL_MS = 15_000;

const inferenceModelQueryKeys = {
  root: ["inference-models"] as const,
  list: () => {
    return [...inferenceModelQueryKeys.root, "list"] as const;
  },
};

const inferenceModelQueries = {
  list: () => {
    return queryOptions({
      queryKey: inferenceModelQueryKeys.list(),
      queryFn: listInferenceModels,
      refetchInterval: INFERENCE_MODEL_REFETCH_INTERVAL_MS,
      refetchOnWindowFocus: true,
    });
  },
};

export function useInferenceModels() {
  return useQuery(inferenceModelQueries.list());
}
