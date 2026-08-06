import { api } from "@/shared/api";
import { assetSchema, assetsSchema } from "../model/schema";

export const assets = {
  list: async () => {
    const payload: unknown = await api.get("assets").json();

    return assetsSchema.parse(payload);
  },
  upload: async (file: File) => {
    const body = new FormData();

    body.append("file", file);

    const payload: unknown = await api.post("assets", { body }).json();

    return assetSchema.parse(payload);
  },
  delete: async (key: string) => {
    await api.delete(`assets/${key}`);
  },
};
