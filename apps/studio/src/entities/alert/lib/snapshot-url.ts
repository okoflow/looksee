import { getApiUrl } from "@/shared/config";

export function resolveSnapshotUrl(path: string | null | undefined): string | null {
  if (path === null || path === undefined || path === "") {
    return null;
  }

  return `${getApiUrl()}${path}`;
}
