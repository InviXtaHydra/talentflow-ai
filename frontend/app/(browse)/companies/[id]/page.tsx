import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";

import { CompanyProfile } from "@/features/companies/company-pages";

export const metadata: Metadata = { title: "Bedrijf" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><CompanyProfile /></PageSuspense>;
}
