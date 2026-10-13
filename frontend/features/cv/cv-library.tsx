"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FilePlus2, FileText, RefreshCw, ScanSearch, Sparkles, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Badge, EmptyState, Skeleton } from "@/components/ui/feedback";
import { MatchScore } from "@/features/jobs/match-score";
import { api, errorMessage } from "@/lib/api";
import { fileSize, formatDate, relativeTime } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { CvDocument, CvDocumentDetail, CvVersionSummary } from "@/types/api";

import { CvUpload } from "./upload";

const extractionTone = { pending: "neutral", processing: "accent", completed: "success", needs_ocr: "warning", failed: "danger" } as const;

export function CvLibrary() {
  const router = useRouter();
  const qc = useQueryClient();
  const docs = useQuery({ queryKey: ["cvs"], queryFn: () => api.get<CvDocument[]>("/cvs"), refetchInterval: (q) => (q.state.data?.some((d) => ["pending", "processing"].includes(d.extraction_status)) ? 3000 : false) });
  const versions = useQuery({ queryKey: ["cv-versions"], queryFn: () => api.get<CvVersionSummary[]>("/cv-versions"), refetchInterval: (q) => (q.state.data?.some((v) => v.status === "generating") ? 3000 : false) });
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const [toDelete, setToDelete] = React.useState<{ kind: "doc" | "version"; id: string; name: string } | null>(null);

  const remove = useMutation({
    mutationFn: (target: { kind: "doc" | "version"; id: string }) => api.delete(target.kind === "doc" ? `/cvs/${target.id}` : `/cv-versions/${target.id}`),
    onSuccess: () => { setToDelete(null); qc.invalidateQueries({ queryKey: ["cvs"] }); qc.invalidateQueries({ queryKey: ["cv-versions"] }); toast.success("Verwijderd"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const fromProfile = useMutation({
    mutationFn: () => api.post<{ id: string }>("/cv-versions", { title: "Mijn cv", template: "modern", language: "nl" }),
    onSuccess: (data) => router.push(`/cv/versions/${data.id}`),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const reextract = useMutation({
    mutationFn: (cvId: string) => api.post(`/cvs/${cvId}/retry-extraction`),
    onSuccess: (_d, cvId) => { toast.success("Je cv wordt opnieuw herkend"); qc.invalidateQueries({ queryKey: ["cvs"] }); router.push(`/cv/${cvId}/review`); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const analyze = useMutation({
    mutationFn: (cvId: string) => api.post(`/cvs/${cvId}/analyze`),
    onSuccess: () => { toast.success("Analyse gestart"); router.push("/cv/analysis"); },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const onUploaded = React.useCallback((doc: CvDocumentDetail) => {
    setUploadOpen(false);
    router.push(`/cv/${doc.id}/review`);
  }, [router]);

  const optimized = (versions.data ?? []).filter((v) => v.kind === "optimized");
  const own = (versions.data ?? []).filter((v) => v.kind !== "optimized");

  return (
    <>
      <PageHeader title="Mijn cv's" description="Je geüploade cv's, je eigen versies en de versies die je per vacature liet afstemmen."
        actions={<>
          <Button variant="secondary" loading={fromProfile.isPending} onClick={() => fromProfile.mutate()}><FilePlus2 />Cv maken van profiel</Button>
          <Button onClick={() => setUploadOpen(true)}><Upload />Cv uploaden</Button>
        </>} />

      <div className="flex flex-col gap-6">
        <Card>
          <CardHeader title="Per vacature afgestemd" description="Elke versie is apart bewaard; je origineel blijft ongewijzigd." />
          <CardBody>
            {versions.error ? <QueryError error={versions.error} /> : !versions.data ? <Skeleton className="h-24" /> : optimized.length === 0 ? (
              <EmptyState icon={Sparkles} title="Nog geen afgestemde cv's" description="Open een vacature en kies ‘Optimaliseer mijn cv voor deze vacature’."
                action={<Button asChild variant="secondary"><Link href="/jobs">Vacatures bekijken</Link></Button>} />
            ) : (
              <ul className="divide-y divide-border">
                {optimized.map((v) => (
                  <li key={v.id} className="flex flex-wrap items-center gap-4 py-3">
                    <div className="min-w-0 flex-1">
                      <Link href={`/cv/optimizations/${v.id}`} className="font-medium text-text hover:text-accent">{v.target_job_title ?? v.title}</Link>
                      <p className="text-sm text-muted">{v.target_company_name} · {relativeTime(v.created_at)}{v.last_exported_at && " · gedownload"}</p>
                    </div>
                    {v.status === "generating" && <Badge tone="accent">Wordt gemaakt…</Badge>}
                    {v.status === "failed" && <Badge tone="danger">Mislukt</Badge>}
                    {v.is_simulated && <Badge>Demo</Badge>}
                    {v.status === "ready" && <div className="flex items-center gap-1 text-xs text-muted"><MatchScore score={v.score_before} size={36} label={false} />→<MatchScore score={v.score_after} size={36} label={false} /></div>}
                    <div className="flex gap-1">
                      <Button asChild size="sm" variant="secondary"><Link href={`/cv/optimizations/${v.id}`}>Openen</Link></Button>
                      <Button size="icon" variant="ghost" aria-label="Verwijderen" onClick={() => setToDelete({ kind: "version", id: v.id, name: v.title })}><Trash2 /></Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader title="Geüploade cv's" description="Originele bestanden, privé bewaard." />
            <CardBody>
              {docs.error ? <QueryError error={docs.error} /> : !docs.data ? <Skeleton className="h-24" /> : docs.data.length === 0 ? (
                <EmptyState icon={FileText} title="Nog geen cv geüpload" action={<Button size="sm" onClick={() => setUploadOpen(true)}>Cv uploaden</Button>} />
              ) : (
                <ul className="divide-y divide-border">
                  {docs.data.map((d) => (
                    <li key={d.id} className="flex flex-col gap-2 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium text-text">{d.original_filename}</p>
                          <p className="text-xs text-muted">{fileSize(d.size_bytes)} · {formatDate(d.created_at)}{d.is_demo && " · demo"}</p>
                        </div>
                        <Badge tone={extractionTone[d.extraction_status]}>{t(`enums.extraction.${d.extraction_status}`)}</Badge>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {d.extraction_status === "completed" && <Button asChild size="sm" variant={d.confirmed_at ? "ghost" : "primary"}><Link href={`/cv/${d.id}/review`}>{d.confirmed_at ? "Opnieuw nakijken" : "Nakijken en bevestigen"}</Link></Button>}
                        {!d.is_demo && ["completed", "failed"].includes(d.extraction_status) && (
                          <Button size="sm" variant="ghost" loading={reextract.isPending && reextract.variables === d.id} onClick={() => reextract.mutate(d.id)}><RefreshCw />Opnieuw herkennen</Button>
                        )}
                        {d.confirmed_at && <Button size="sm" variant="ghost" loading={analyze.isPending && analyze.variables === d.id} onClick={() => analyze.mutate(d.id)}><ScanSearch />Analyseren</Button>}
                        <Button asChild size="sm" variant="ghost"><a href={`/api/v1/cvs/${d.id}/file`} target="_blank" rel="noreferrer"><Download />Origineel</a></Button>
                        <Button size="sm" variant="ghost" onClick={() => setToDelete({ kind: "doc", id: d.id, name: d.original_filename })}><Trash2 />Verwijderen</Button>
                      </div>
                      {d.extraction_error && d.extraction_status !== "completed" && <p className="text-xs text-danger">{d.extraction_error}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Originelen en eigen versies" />
            <CardBody>
              {!versions.data ? <Skeleton className="h-24" /> : own.length === 0 ? <p className="text-sm text-muted">Nog geen versies. Bevestig een geüpload cv of maak er een van je profiel.</p> : (
                <ul className="divide-y divide-border">
                  {own.map((v) => (
                    <li key={v.id} className="flex items-center gap-3 py-3">
                      <div className="min-w-0 flex-1">
                        <Link href={`/cv/versions/${v.id}`} className="font-medium text-text hover:text-accent">{v.title}</Link>
                        <p className="text-xs text-muted">{t(`enums.cvKind.${v.kind}`)} · {t(`enums.template.${v.template}`)} · {relativeTime(v.updated_at)}</p>
                      </div>
                      <Button size="icon" variant="ghost" aria-label="Verwijderen" onClick={() => setToDelete({ kind: "version", id: v.id, name: v.title })}><Trash2 /></Button>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>
      </div>

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen} title="Cv uploaden" description="Na het uploaden kijk je na wat we herkenden.">
        <CvUpload onDone={onUploaded} />
      </Dialog>
      <ConfirmDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)} title="Definitief verwijderen?"
        description={toDelete?.kind === "doc" ? `Het bestand ‘${toDelete.name}’ en de herkende gegevens worden verwijderd. Je profiel en cv-versies blijven bestaan.` : `‘${toDelete?.name}’ wordt verwijderd.`}
        confirmLabel="Verwijderen" loading={remove.isPending} onConfirm={() => toDelete && remove.mutate(toDelete)} />
    </>
  );
}
