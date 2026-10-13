import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { AdminPage } from "@/features/admin/admin-page";

export const metadata: Metadata = { title: "Beheer" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["admin"]}><AdminPage /></RequireRole></PageSuspense>;
}
