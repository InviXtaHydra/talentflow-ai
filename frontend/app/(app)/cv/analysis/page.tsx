import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { CvAnalysisPage } from "@/features/cv/analysis-page";

export const metadata: Metadata = { title: "Cv-analyse" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["candidate"]}><CvAnalysisPage /></RequireRole></PageSuspense>;
}
