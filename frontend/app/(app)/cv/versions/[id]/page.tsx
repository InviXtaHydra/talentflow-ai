import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { CvVersionEditor } from "@/features/cv/version-editor";

export const metadata: Metadata = { title: "Cv bewerken" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["candidate"]}><CvVersionEditor /></RequireRole></PageSuspense>;
}
