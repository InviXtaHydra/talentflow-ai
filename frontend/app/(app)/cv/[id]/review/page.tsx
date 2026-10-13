import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { CvReviewPage } from "@/features/cv/review-page";

export const metadata: Metadata = { title: "Cv nakijken" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["candidate"]}><CvReviewPage /></RequireRole></PageSuspense>;
}
