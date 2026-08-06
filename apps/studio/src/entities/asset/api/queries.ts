import { queryOptions, useQuery } from "@tanstack/react-query";
import { type ApiMutationOptions, useInvalidatingMutation } from "@/shared/api";
import type { Asset } from "../model/schema";
import { assets } from "./assets";

export const assetQueryKeys = {
  root: ["assets"] as const,
};

const assetQueries = {
  list: () => {
    return queryOptions({
      queryKey: assetQueryKeys.root,
      queryFn: () => {
        return assets.list();
      },
    });
  },
};

export function useAssets() {
  return useQuery(assetQueries.list());
}

export function useUploadAsset(options: ApiMutationOptions<Asset, File> = {}) {
  return useInvalidatingMutation(assets.upload, assetQueryKeys.root, options);
}

export function useDeleteAsset(options: ApiMutationOptions<void, string> = {}) {
  return useInvalidatingMutation(assets.delete, assetQueryKeys.root, options);
}
