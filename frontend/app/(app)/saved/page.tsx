import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { SavedJobs } from "@/features/jobs/saved-jobs";

export const metadata: Metadata = { title: "Bewaarde vacatures" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["candidate"]}><SavedJobs /></RequireRole></PageSuspense>;
}
