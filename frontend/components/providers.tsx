"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { Toaster } from "sonner";

import { ApiError } from "@/lib/api";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
          },
        },
        mutationCache: new MutationCache({
          onError: (error) => {
            // A 401 during a mutation means the session expired.
            if (error instanceof ApiError && error.status === 401 && typeof window !== "undefined") {
              window.location.assign(new URL(`/login?next=${encodeURIComponent(window.location.pathname)}`, window.location.origin).toString());
            }
          },
        }),
      }),
  );
  return (
    <QueryClientProvider client={client}>
      {children}
      <Toaster position="bottom-right" richColors closeButton />
    </QueryClientProvider>
  );
}
