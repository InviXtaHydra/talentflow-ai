import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { VerifyEmail } from "@/features/auth/forms";

export const metadata: Metadata = { title: "E-mailadres bevestigen" };

export default function Page() {
  return (
    <PageSuspense>
      <VerifyEmail />
    </PageSuspense>
  );
}
