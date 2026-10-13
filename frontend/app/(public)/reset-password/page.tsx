import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { ResetPasswordForm } from "@/features/auth/forms";

export const metadata: Metadata = { title: "Nieuw wachtwoord" };

export default function Page() {
  return (
    <PageSuspense>
      <ResetPasswordForm />
    </PageSuspense>
  );
}
