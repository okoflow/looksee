import { api } from "@/shared/api";
import {
  type AlertListParams,
  type AlertScopeParams,
  alertListParamsSchema,
  alertScopeParamsSchema,
  alertsSchema,
} from "../model/schema";

function definedSearchParams(params: AlertListParams): Record<string, string | number> {
  const entries: [string, string | number][] = [];

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      entries.push([key, value]);
    }
  }

  return Object.fromEntries(entries);
}

export const alerts = {
  list: async (params: AlertListParams = {}) => {
    const searchParams = definedSearchParams(alertListParamsSchema.parse(params));
    const payload: unknown = await api.get("alerts", { searchParams }).json();

    return alertsSchema.parse(payload);
  },
  delete: async (id: string) => {
    await api.delete(`alerts/${id}`);
  },
  clear: async (params: AlertScopeParams = {}) => {
    const searchParams = definedSearchParams(alertScopeParamsSchema.parse(params));

    await api.delete("alerts", { searchParams });
  },
};
