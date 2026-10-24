"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import type { PropsWithChildren } from "react";
import { useState } from "react";
import { createQueryClient } from "@/shared/api";
import { TooltipProvider } from "@/shared/ui/tooltip";

export function AppProviders({ children }: PropsWithChildren) {
  const [client] = useState(() => {
    return createQueryClient();
  });

  return (
    <QueryClientProvider client={client}>
      <TooltipProvider delay={200}>{children}</TooltipProvider>
    </QueryClientProvider>
  );
}
