import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";

import { JobDetailPage } from "@/features/jobs/job-detail";

export const metadata: Metadata = { title: "Vacature" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><JobDetailPage /></PageSuspense>;
}
