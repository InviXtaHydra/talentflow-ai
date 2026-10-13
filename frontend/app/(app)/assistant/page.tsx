import type { Metadata } from "next";

import { PageSuspense } from "@/components/page-suspense";
import { RequireRole } from "@/components/require-role";
import { AssistantPage } from "@/features/assistant/assistant-page";

export const metadata: Metadata = { title: "Carrière-assistent" };

// Rendered by the client-side app shell after the session is known (no instant static shell).
export const instant = false;

export default function Page() {
  return <PageSuspense><RequireRole roles={["candidate"]}><AssistantPage /></RequireRole></PageSuspense>;
}
