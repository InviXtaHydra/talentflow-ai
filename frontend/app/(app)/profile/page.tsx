import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { ProfilePage } from "@/features/profile/profile-page";

export const metadata: Metadata = { title: "Profiel" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["candidate"]}><ProfilePage /></RequireRole></PageSuspense>;
}
