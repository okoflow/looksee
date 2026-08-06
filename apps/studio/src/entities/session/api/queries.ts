import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ApiMutationOptions } from "@/shared/api";
import type { LoginInput, SessionUser, SetupInput } from "../model/schema";
import { getSessionUser, login, logout, setupOwner } from "./session";

export const sessionQueryKeys = {
  root: ["session"] as const,
};

const sessionQueries = {
  current: () => {
    return queryOptions({
      queryKey: sessionQueryKeys.root,
      queryFn: getSessionUser,
      staleTime: 60_000,
      retry: false,
    });
  },
};

export function useSessionUser() {
  return useQuery(sessionQueries.current());
}

function useSessionMutation<TInput>(
  mutationFn: (input: TInput) => Promise<SessionUser>,
  options: ApiMutationOptions<SessionUser, TInput>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    ...options,
    onSuccess: (...args) => {
      const [user] = args;

      queryClient.setQueryData(sessionQueryKeys.root, user);

      options.onSuccess?.(...args);
    },
  });
}

export function useLogin(options: ApiMutationOptions<SessionUser, LoginInput> = {}) {
  return useSessionMutation(login, options);
}

export function useSetupOwner(options: ApiMutationOptions<SessionUser, SetupInput> = {}) {
  return useSessionMutation(setupOwner, options);
}

export function useLogout(options: ApiMutationOptions<void, void> = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    ...options,
    onSuccess: (...args) => {
      queryClient.clear();

      options.onSuccess?.(...args);
    },
  });
}
