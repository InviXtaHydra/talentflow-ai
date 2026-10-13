import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";

import { CompanyDirectory } from "@/features/companies/company-pages";

export const metadata: Metadata = { title: "Bedrijven" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><CompanyDirectory /></PageSuspense>;
}
