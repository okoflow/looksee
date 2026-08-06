import { api, uuidSchema } from "@/shared/api";
import {
  type WorkflowCreate,
  type WorkflowUpdate,
  workflowCreateSchema,
  workflowSchema,
  workflowsSchema,
  workflowUpdateSchema,
} from "../model/schema";

export const workflows = {
  list: async () => {
    const payload: unknown = await api.get("workflows").json();

    return workflowsSchema.parse(payload);
  },
  getById: async (id: string) => {
    const workflowId = uuidSchema.parse(id);
    const payload: unknown = await api.get(`workflows/${workflowId}`).json();

    return workflowSchema.parse(payload);
  },
  create: async (payload: WorkflowCreate) => {
    const body = workflowCreateSchema.parse(payload);
    const response: unknown = await api.post("workflows", { json: body }).json();

    return workflowSchema.parse(response);
  },
  update: async (id: string, payload: WorkflowUpdate) => {
    const body = workflowUpdateSchema.parse(payload);
    const response: unknown = await api.patch(`workflows/${id}`, { json: body }).json();

    return workflowSchema.parse(response);
  },
  delete: async (id: string) => {
    await api.delete(`workflows/${id}`);
  },
};
