import {
  type MutationFunction,
  QueryClient,
  type UseMutationOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

export type ApiMutationOptions<TData, TVariables> = Omit<UseMutationOptions<TData, Error, TVariables>, "mutationFn">;

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: false,
        retry: 1,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}

export function useInvalidatingMutation<TData, TVariables>(
  mutationFn: MutationFunction<TData, TVariables>,
  invalidateKey: readonly unknown[],
  options: ApiMutationOptions<TData, TVariables> = {}
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    ...options,
    onSuccess: async (...args) => {
      await queryClient.invalidateQueries({ queryKey: invalidateKey });

      options.onSuccess?.(...args);
    },
  });
}
