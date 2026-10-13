import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { OptimizationWorkspace } from "@/features/cv/optimization-workspace";

export const metadata: Metadata = { title: "Cv-optimalisatie" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["candidate"]}><OptimizationWorkspace /></RequireRole></PageSuspense>;
}
