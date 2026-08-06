import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ApiMutationOptions, useInvalidatingMutation } from "@/shared/api";
import type { Workflow, WorkflowCreate, WorkflowUpdate } from "../model/schema";
import { workflows } from "./workflows";

export const workflowQueryKeys = {
  root: ["workflows"] as const,
  list: () => {
    return [...workflowQueryKeys.root, "list"] as const;
  },
  detail: (id: string) => {
    return [...workflowQueryKeys.root, "detail", id] as const;
  },
};

const workflowQueries = {
  list: () => {
    return queryOptions({ queryKey: workflowQueryKeys.list(), queryFn: workflows.list });
  },
  detail: (id: string) => {
    return queryOptions({
      queryKey: workflowQueryKeys.detail(id),
      queryFn: () => {
        return workflows.getById(id);
      },
    });
  },
};

export function useWorkflows() {
  return useQuery(workflowQueries.list());
}

export function useWorkflow(id: string) {
  return useQuery(workflowQueries.detail(id));
}

export function useCreateWorkflow(options: ApiMutationOptions<Workflow, WorkflowCreate> = {}) {
  return useInvalidatingMutation(workflows.create, workflowQueryKeys.root, options);
}

export function useUpdateWorkflow(id: string, options: ApiMutationOptions<Workflow, WorkflowUpdate> = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: WorkflowUpdate) => {
      return workflows.update(id, payload);
    },
    ...options,
    onSuccess: async (...args) => {
      const [updatedWorkflow] = args;

      queryClient.setQueryData(workflowQueryKeys.detail(id), updatedWorkflow);

      await queryClient.invalidateQueries({ queryKey: workflowQueryKeys.list() });

      options.onSuccess?.(...args);
    },
  });
}

export function useDeleteWorkflow(options: ApiMutationOptions<void, string> = {}) {
  return useInvalidatingMutation(workflows.delete, workflowQueryKeys.root, options);
}
