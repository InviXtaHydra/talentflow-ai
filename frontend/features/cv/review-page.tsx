"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";

import { PageHeader, QueryError } from "@/components/page-header";
import { PageSkeleton } from "@/components/page-suspense";
import { Alert, Spinner } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import type { CvDocumentDetail } from "@/types/api";

import { ExtractionReview } from "./extraction-review";

export function CvReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const doc = useQuery({
    queryKey: ["cv", id],
    queryFn: () => api.get<CvDocumentDetail>(`/cvs/${id}`),
    refetchInterval: (q) => (q.state.data && ["pending", "processing"].includes(q.state.data.extraction_status) ? 2000 : false),
  });
  if (doc.error) return <QueryError error={doc.error} onRetry={() => doc.refetch()} />;
  if (!doc.data) return <PageSkeleton />;
  const d = doc.data;
  return (
    <>
      <PageHeader title="Herkende gegevens nakijken" description={d.original_filename} />
      {["pending", "processing"].includes(d.extraction_status) && <Spinner label="Je cv wordt nog verwerkt…" />}
      {(d.extraction_status === "failed" || d.extraction_status === "needs_ocr") && <Alert tone="danger" title="Dit cv kon niet gelezen worden">{d.extraction_error}</Alert>}
      {d.extraction_status === "completed" && <ExtractionReview doc={d} onConfirmed={() => router.push("/profile")} />}
    </>
  );
}
