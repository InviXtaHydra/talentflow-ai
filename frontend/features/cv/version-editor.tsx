"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Copy, Lock, Save } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { PageSkeleton } from "@/components/page-suspense";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Alert } from "@/components/ui/feedback";
import { Input } from "@/components/ui/input";
import { api, errorMessage } from "@/lib/api";
import type { CvContent, CvTemplate, CvVersionDetail } from "@/types/api";

import { CvContentEditor } from "./cv-editor";
import { CvPreview } from "./cv-preview";
import { useDraft } from "@/hooks/use-draft";

export function CvVersionEditor() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const key = ["cv-version", id];
  const query = useQuery({ queryKey: key, queryFn: () => api.get<CvVersionDetail>(`/cv-versions/${id}`) });
  const v = query.data;
  const [local, setLocal] = useDraft(v, v?.updated_at, (x: CvVersionDetail) => ({ content: x.content as CvContent, title: x.title, template: x.template }));
  const draft = local?.content ?? null;
  const title = local?.title ?? "";
  const template: CvTemplate = local?.template ?? "modern";
  const setDraft = (content: CvContent) => setLocal((l) => ({ ...l, content }));
  const setTitle = (t: string) => setLocal((l) => ({ ...l, title: t }));
  const setTemplate = (tpl: CvTemplate) => setLocal((l) => ({ ...l, template: tpl }));

  const save = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch<CvVersionDetail>(`/cv-versions/${id}`, body),
    onSuccess: (data) => { qc.setQueryData(key, data); qc.invalidateQueries({ queryKey: ["cv-versions"] }); toast.success("Opgeslagen"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const duplicate = useMutation({
    mutationFn: () => api.post<{ id: string }>(`/cv-versions/${id}/duplicate`),
    onSuccess: (data) => router.push(`/cv/versions/${data.id}`),
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (query.error) return <QueryError error={query.error} onRetry={() => query.refetch()} />;
  if (!v || !draft) return <PageSkeleton />;
  if (v.kind === "optimized") { router.replace(`/cv/optimizations/${id}`); return null; }
  const readOnly = v.kind === "original";
  const dirty = JSON.stringify(draft) !== JSON.stringify(v.content) || title !== v.title;

  return (
    <div className="flex flex-col gap-6">
      <Link href="/cv" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-text"><ArrowLeft className="size-4" />Mijn cv&apos;s</Link>
      <PageHeader title={readOnly ? v.title : <Input value={title} onChange={(e) => setTitle(e.target.value)} aria-label="Titel" className="h-11 text-lg font-semibold" />}
        actions={readOnly ? <Button loading={duplicate.isPending} onClick={() => duplicate.mutate()}><Copy />Kopie maken om te bewerken</Button> : (
          <Button disabled={!dirty} loading={save.isPending} onClick={() => save.mutate({ content: draft, title })}><Save />{dirty ? "Opslaan" : "Opgeslagen"}</Button>
        )} />
      {readOnly && <Alert tone="neutral" title="Origineel cv"><Lock className="mr-1 inline size-3.5" />Je origineel wordt nooit gewijzigd. Maak een kopie om aanpassingen te doen.</Alert>}
      <div className="grid gap-6 xl:grid-cols-[1fr_400px]">
        <CvContentEditor value={draft} onChange={setDraft} readOnly={readOnly} />
        <div className="xl:sticky xl:top-6 xl:self-start">
          <Card>
            <CardHeader title="Voorbeeld" description={dirty ? "Sla op om het voorbeeld bij te werken." : undefined} />
            <CardBody>
              <CvPreview basePath={`/cv-versions/${id}`} template={template} version={v.updated_at}
                onTemplateChange={(tpl) => { setTemplate(tpl); save.mutate({ template: tpl }); }} />
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
