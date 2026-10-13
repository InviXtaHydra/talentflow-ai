import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";

import { JobSearch } from "@/features/jobs/job-search";

export const metadata: Metadata = { title: "Vacatures" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><JobSearch /></PageSuspense>;
}
