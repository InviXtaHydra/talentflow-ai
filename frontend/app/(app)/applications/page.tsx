import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { ApplicationTracker } from "@/features/applications/tracker";

export const metadata: Metadata = { title: "Sollicitaties" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["candidate"]}><ApplicationTracker /></RequireRole></PageSuspense>;
}
