import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ApiMutationOptions, useInvalidatingMutation } from "@/shared/api";
import type { Credential, CredentialCreate, CredentialUpdate } from "../model/schema";
import { credentials } from "./credentials";

export const credentialQueryKeys = {
  root: ["credentials"] as const,
};

const credentialQueries = {
  list: () => {
    return queryOptions({ queryKey: credentialQueryKeys.root, queryFn: credentials.list });
  },
};

export function useCredentials() {
  return useQuery(credentialQueries.list());
}

export function useCreateCredential(options: ApiMutationOptions<Credential, CredentialCreate> = {}) {
  return useInvalidatingMutation(credentials.create, credentialQueryKeys.root, options);
}

export function useUpdateCredential(id: string, options: ApiMutationOptions<Credential, CredentialUpdate> = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CredentialUpdate) => {
      return credentials.update(id, payload);
    },
    ...options,
    onSuccess: async (...args) => {
      await queryClient.invalidateQueries({ queryKey: credentialQueryKeys.root });

      options.onSuccess?.(...args);
    },
  });
}

export function useDeleteCredential(options: ApiMutationOptions<void, string> = {}) {
  return useInvalidatingMutation(credentials.delete, credentialQueryKeys.root, options);
}
