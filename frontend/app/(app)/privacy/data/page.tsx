import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";

import { PrivacyDataPage } from "@/features/account/account-pages";

export const metadata: Metadata = { title: "Privacy en gegevens" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><PrivacyDataPage /></PageSuspense>;
}
