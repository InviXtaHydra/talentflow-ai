import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { ForgotPasswordForm } from "@/features/auth/forms";

export const metadata: Metadata = { title: "Wachtwoord vergeten" };

export default function Page() {
  return (
    <PageSuspense>
      <ForgotPasswordForm />
    </PageSuspense>
  );
}
