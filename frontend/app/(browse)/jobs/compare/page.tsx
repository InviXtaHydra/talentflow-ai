import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";

import { JobCompare } from "@/features/jobs/job-compare";

export const metadata: Metadata = { title: "Vacatures vergelijken" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><JobCompare /></PageSuspense>;
}
