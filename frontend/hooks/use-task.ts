"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TaskStatus } from "@/types/api";

/** Polls a background task until it finishes. */
export function useTask(taskId: string | null | undefined) {
  return useQuery<TaskStatus>({
    queryKey: ["task", taskId],
    queryFn: () => api.get<TaskStatus>(`/tasks/${taskId}`),
    enabled: !!taskId,
    refetchInterval: (q) => (q.state.data && ["succeeded", "failed", "cancelled"].includes(q.state.data.status) ? false : 1500),
  });
}
