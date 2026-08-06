import { queryOptions, useQuery } from "@tanstack/react-query";
import { type ApiMutationOptions, useInvalidatingMutation } from "@/shared/api";
import type { AlertListParams, AlertScopeParams } from "../model/schema";
import { alerts } from "./alerts";

const ALERT_REFETCH_INTERVAL_MS = 5000;

export const alertQueryKeys = {
  root: ["alerts"] as const,
  list: (params: AlertListParams) => {
    return [...alertQueryKeys.root, "list", params] as const;
  },
};

const alertQueries = {
  list: (params: AlertListParams = {}) => {
    return queryOptions({
      queryKey: alertQueryKeys.list(params),
      queryFn: () => {
        return alerts.list(params);
      },
      refetchInterval: ALERT_REFETCH_INTERVAL_MS,
    });
  },
};

export function useAlerts(params: AlertListParams = {}) {
  return useQuery(alertQueries.list(params));
}

export function useDeleteAlert(options: ApiMutationOptions<void, string> = {}) {
  return useInvalidatingMutation(alerts.delete, alertQueryKeys.root, options);
}

export function useClearAlerts(options: ApiMutationOptions<void, AlertScopeParams> = {}) {
  return useInvalidatingMutation(alerts.clear, alertQueryKeys.root, options);
}
