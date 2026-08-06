import { z } from "zod";

export const MEASUREMENT_FILTERS_FEATURE = "measurement_filters";
export const ENTERPRISE_INTEGRATIONS_FEATURE = "enterprise_integrations";

export type LicensedFeature = typeof ENTERPRISE_INTEGRATIONS_FEATURE | typeof MEASUREMENT_FILTERS_FEATURE;

export const entitlementsSchema = z.object({
  edition: z.enum(["community", "enterprise"]),
  features: z.array(z.string()),
});

export type Entitlements = z.infer<typeof entitlementsSchema>;
