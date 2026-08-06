import { getApiUrl } from "@/shared/config";

export function assetContentUrl(key: string): string {
  return `${getApiUrl()}/assets/${key}/content`;
}
