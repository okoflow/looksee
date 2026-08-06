import { queryOptions, useQuery } from "@tanstack/react-query";
import { getEntitlements } from "./entitlements";

const ENTITLEMENT_STALE_TIME_MS = 60_000;

const entitlementQueryKeys = {
  root: ["entitlements"] as const,
};

const entitlementQueries = {
  current: () => {
    return queryOptions({
      queryKey: entitlementQueryKeys.root,
      queryFn: getEntitlements,
      staleTime: ENTITLEMENT_STALE_TIME_MS,
    });
  },
};

export function useEntitlements() {
  return useQuery(entitlementQueries.current());
}
