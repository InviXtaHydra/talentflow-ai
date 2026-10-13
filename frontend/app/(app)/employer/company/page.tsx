import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { CompanySettingsPage } from "@/features/employer/employer-pages";

export const metadata: Metadata = { title: "Bedrijfsprofiel" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["employer", "admin"]}><CompanySettingsPage /></RequireRole></PageSuspense>;
}
