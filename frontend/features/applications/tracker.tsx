"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Briefcase, ExternalLink, History, Trash2 } from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Dialog } from "@/components/ui/dialog";
import { Badge, EmptyState, Skeleton } from "@/components/ui/feedback";
import { Field, Select, Textarea } from "@/components/ui/input";
import { CompanyLogo } from "@/features/jobs/company-logo";
import { api, errorMessage } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Application, ApplicationStatus } from "@/types/api";

const COLUMNS: ApplicationStatus[] = ["saved", "ready_to_apply", "applied", "in_review", "interview", "offer", "rejected", "withdrawn"];
export const statusTone: Record<ApplicationStatus, "neutral" | "accent" | "success" | "warning" | "danger"> = {
  saved: "neutral", ready_to_apply: "neutral", applied: "accent", in_review: "accent", interview: "warning", offer: "success", rejected: "danger", withdrawn: "neutral",
};

function ApplicationDialog({ app, onClose }: { app: Application; onClose: () => void }) {
  const qc = useQueryClient();
  const [status, setStatus] = React.useState<ApplicationStatus>(app.status);
  const [notes, setNotes] = React.useState(app.notes ?? "");
  const [confirmDelete, setConfirmDelete] = React.useState(false);
  const platform = app.channel === "platform";
  const update = useMutation({
    mutationFn: () => api.patch(`/applications/${app.id}`, { notes, ...(status !== app.status ? { status } : {}) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["applications"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); toast.success("Bijgewerkt"); onClose(); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const remove = useMutation({
    mutationFn: () => api.delete(`/applications/${app.id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["applications"] }); toast.success("Verwijderd uit je overzicht"); onClose(); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const options: ApplicationStatus[] = platform ? (app.status === "withdrawn" ? ["withdrawn"] : [app.status, "withdrawn"]) : COLUMNS;
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()} title={app.job.title} description={`${app.job.company.name} · ${platform ? "via het platform" : "extern bijgehouden"}`}
      footer={<>
        <Button variant="ghost" className="mr-auto" onClick={() => setConfirmDelete(true)}><Trash2 />Verwijderen</Button>
        <Button variant="secondary" onClick={onClose}>Annuleren</Button>
        <Button loading={update.isPending} onClick={() => update.mutate()}>Opslaan</Button>
      </>}>
      <div className="flex flex-col gap-4">
        <Field label="Status" hint={platform ? "De werkgever werkt de status bij. Jij kunt je sollicitatie intrekken." : undefined}>
          <Select value={status} onChange={(e) => setStatus(e.target.value as ApplicationStatus)}>
            {[...new Set(options)].map((s) => <option key={s} value={s}>{t(`enums.applicationStatus.${s}`)}</option>)}
          </Select>
        </Field>
        <Field label="Persoonlijke notities" hint="Alleen zichtbaar voor jou."><Textarea rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        {app.cv_version_title && <p className="text-sm text-text-2">Meegestuurd cv: {app.cv_version_title}</p>}
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-sm font-medium text-text-2"><History className="size-4" />Geschiedenis</p>
          <ol className="flex flex-col gap-1.5 border-l border-border pl-4 text-sm">
            {app.history.map((h, i) => (
              <li key={i}><span className="font-medium text-text">{t(`enums.applicationStatus.${h.to_status}`)}</span> <span className="text-muted">· {formatDateTime(h.created_at)}{h.changed_by_role === "employer" && " · door de werkgever"}</span>{h.note && <p className="text-muted">{h.note}</p>}</li>
            ))}
          </ol>
        </div>
      </div>
      <ConfirmDialog open={confirmDelete} onOpenChange={setConfirmDelete} title="Uit je overzicht verwijderen?" description="Je notities en de geschiedenis worden verwijderd."
        confirmLabel="Verwijderen" loading={remove.isPending} onConfirm={() => remove.mutate()} />
    </Dialog>
  );
}

export function ApplicationTracker() {
  const apps = useQuery({ queryKey: ["applications"], queryFn: () => api.get<Application[]>("/applications/me") });
  const [open, setOpen] = React.useState<Application | null>(null);
  const [filter, setFilter] = React.useState<"active" | "all">("active");
  const list = (apps.data ?? []).filter((a) => filter === "all" || !["rejected", "withdrawn"].includes(a.status));
  return (
    <>
      <PageHeader title="Sollicitaties" description="Volg je sollicitaties via het platform én de sollicitaties die je elders deed."
        actions={<Select value={filter} onChange={(e) => setFilter(e.target.value as "active" | "all")} aria-label="Filter" className="w-auto"><option value="active">Lopend</option><option value="all">Alle</option></Select>} />
      {apps.error ? <QueryError error={apps.error} onRetry={() => apps.refetch()} /> : !apps.data ? <Skeleton className="h-48" /> : apps.data.length === 0 ? (
        <EmptyState icon={Briefcase} title="Nog geen sollicitaties" description="Solliciteer via een vacature of voeg een vacature toe aan je overzicht om ze hier te volgen."
          action={<Button asChild variant="secondary"><Link href="/jobs">Vacatures zoeken</Link></Button>} />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-card">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-border text-left text-muted">
              <tr><th className="px-4 py-3 font-medium">Vacature</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Kanaal</th><th className="px-4 py-3 font-medium">Gesolliciteerd</th><th className="px-4 py-3 font-medium">Laatste update</th><th className="px-4 py-3"><span className="sr-only">Acties</span></th></tr>
            </thead>
            <tbody>
              {list.map((a) => (
                <tr key={a.id} className="border-b border-border last:border-0 hover:bg-surface-2/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <CompanyLogo company={a.job.company} size={32} />
                      <div className="min-w-0"><Link href={`/jobs/${a.job.id}`} className="font-medium text-text hover:text-accent">{a.job.title}</Link><p className="text-xs text-muted">{a.job.company.name}</p></div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><Badge tone={statusTone[a.status]}>{t(`enums.applicationStatus.${a.status}`)}</Badge></td>
                  <td className="px-4 py-3 text-text-2">{a.channel === "platform" ? "Platform" : <span className="inline-flex items-center gap-1">Extern <ExternalLink className="size-3" /></span>}</td>
                  <td className="px-4 py-3 text-text-2">{a.applied_at ? formatDate(a.applied_at) : "—"}</td>
                  <td className="px-4 py-3 text-text-2">{formatDate(a.updated_at)}</td>
                  <td className="px-4 py-3 text-right"><Button size="sm" variant="secondary" onClick={() => setOpen(a)}>Details</Button></td>
                </tr>
              ))}
              {list.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-muted">Geen lopende sollicitaties.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {open && <ApplicationDialog app={open} onClose={() => setOpen(null)} />}
    </>
  );
}
