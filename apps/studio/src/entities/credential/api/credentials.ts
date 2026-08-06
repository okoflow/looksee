import { api } from "@/shared/api";
import {
  type Credential,
  type CredentialCreate,
  type CredentialUpdate,
  credentialSchema,
  credentialsSchema,
} from "../model/schema";

export const credentials = {
  async list(): Promise<Credential[]> {
    const payload: unknown = await api.get("credentials").json();

    return credentialsSchema.parse(payload);
  },

  async create(input: CredentialCreate): Promise<Credential> {
    const payload: unknown = await api.post("credentials", { json: input }).json();

    return credentialSchema.parse(payload);
  },

  async update(id: string, input: CredentialUpdate): Promise<Credential> {
    const payload: unknown = await api.patch(`credentials/${id}`, { json: input }).json();

    return credentialSchema.parse(payload);
  },

  async delete(id: string): Promise<void> {
    await api.delete(`credentials/${id}`);
  },
};
