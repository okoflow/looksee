import ky, { type BeforeErrorState, isHTTPError, type KyInstance } from "ky";
import { z } from "zod";
import { getApiUrl } from "@/shared/config";

const VALUE_ERROR_PREFIX = /^Value error, /;

const apiErrorSchema = z.object({
  detail: z
    .union([z.string(), z.array(z.object({ loc: z.array(z.union([z.string(), z.number()])), msg: z.string() }))])
    .optional(),
});

function describeDetail(detail: string | { loc: (string | number)[]; msg: string }[]): string {
  if (typeof detail === "string") {
    return detail;
  }

  const [issue] = detail;

  if (issue === undefined) {
    return "Request failed validation";
  }

  const field = issue.loc.filter((part) => part !== "body").join(".");
  const message = issue.msg.replace(VALUE_ERROR_PREFIX, "");

  return field === "" ? message : `${field}: ${message}`;
}

function applyErrorDetail(state: BeforeErrorState): Error {
  const { error } = state;

  const parsed = isHTTPError(error) ? apiErrorSchema.safeParse(error.data) : null;
  const detail = parsed?.success ? parsed.data.detail : undefined;

  if (detail !== undefined) {
    error.message = describeDetail(detail);
  }

  return error;
}

const baseOptions = {
  timeout: 10_000,
  retry: 0,
  credentials: "include" as const,
  hooks: {
    beforeError: [applyErrorDetail],
  },
};

function instance(): KyInstance {
  return ky.create({
    ...baseOptions,
    prefix: getApiUrl(),
  });
}

export const api: KyInstance = new Proxy(ky.create(baseOptions), {
  get(_target, property) {
    const current = instance();

    const value = Reflect.get(current, property);

    return typeof value === "function" ? value.bind(current) : value;
  },
});
