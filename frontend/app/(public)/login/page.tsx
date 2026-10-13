import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { LoginForm } from "@/features/auth/forms";

export const metadata: Metadata = { title: "Inloggen" };

export default function Page() {
  return (
    <PageSuspense>
      <LoginForm />
    </PageSuspense>
  );
}
