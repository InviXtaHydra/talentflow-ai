import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RegisterForm } from "@/features/auth/forms";

export const metadata: Metadata = { title: "Account aanmaken" };

export default function Page() {
  return (
    <PageSuspense>
      <RegisterForm />
    </PageSuspense>
  );
}
