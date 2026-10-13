import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { NewJobPage } from "@/features/employer/job-form";

export const metadata: Metadata = { title: "Nieuwe vacature" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["employer", "admin"]}><NewJobPage /></RequireRole></PageSuspense>;
}
