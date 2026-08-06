import { api } from "@/shared/api";
import { entitlementsSchema } from "../model/schema";

export async function getEntitlements() {
  const payload: unknown = await api.get("entitlements").json();

  return entitlementsSchema.parse(payload);
}
