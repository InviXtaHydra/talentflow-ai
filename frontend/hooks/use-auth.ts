"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { PublicConfig, User } from "@/types/api";

export function useMe() {
  return useQuery<User | null>({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api.get<User>("/auth/me");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 60_000,
  });
}

export function usePublicConfig() {
  return useQuery<PublicConfig>({ queryKey: ["config"], queryFn: () => api.get<PublicConfig>("/config"), staleTime: 300_000 });
}

export function useLogout() {
  const qc = useQueryClient();
  return async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      qc.clear();
      window.location.assign(new URL("/login", window.location.origin).toString());
    }
  };
}

export function homeFor(user: User): string {
  if (user.role === "admin") return "/admin";
  if (user.role === "employer") return "/employer";
  return user.onboarding_completed ? "/dashboard" : "/onboarding";
}
