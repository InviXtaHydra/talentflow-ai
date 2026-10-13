import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";

import { NotificationsPage } from "@/features/account/account-pages";

export const metadata: Metadata = { title: "Meldingen" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><NotificationsPage /></PageSuspense>;
}
