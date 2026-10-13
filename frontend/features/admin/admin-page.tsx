"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Badge, Skeleton } from "@/components/ui/feedback";
import { Input, Select } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, errorMessage, query } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Page } from "@/types/api";

interface Stats {
  users: Record<string, number>; companies: number; jobs: Record<string, number>; cv_documents: number; cv_versions: number; applications: number;
  active_sessions: number; tasks: { queued: number; running: number; failed_30d: number };
  ai_usage_30d: { operation: string; calls: number; avg_ms: number; succeeded: number }[];
}
interface AdminUser { id: string; email: string; full_name: string; role: string; is_active: boolean; is_demo: boolean; email_verified: boolean; created_at: string; last_active_at: string | null }
interface AdminJob { id: string; title: string; company_name: string; status: string; source: string; is_demo: boolean; published_at: string | null }
interface Audit { id: string; action: string; target_type: string | null; created_at: string; details: Record<string, unknown> }

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="rounded-lg bg-surface-2 px-4 py-3"><p className="text-xs text-muted">{label}</p><p className="mt-0.5 text-xl font-semibold tabular-nums text-text">{value}</p></div>;
}

const OPS: Record<string, string> = { cv_extraction: "Cv-extractie", cv_analysis: "Cv-analyse", cv_optimization: "Cv-optimalisatie", assistant: "Assistent" };

export function AdminPage() {
  const qc = useQueryClient();
  const stats = useQuery({ queryKey: ["admin-stats"], queryFn: () => api.get<Stats>("/admin/stats") });
  const [userQ, setUserQ] = React.useState("");
  const [role, setRole] = React.useState("");
  const users = useQuery({ queryKey: ["admin-users", userQ, role], queryFn: () => api.get<Page<AdminUser>>(`/admin/users${query({ q: userQ, role })}`) });
  const jobs = useQuery({ queryKey: ["admin-jobs"], queryFn: () => api.get<Page<AdminJob>>("/admin/jobs") });
  const audit = useQuery({ queryKey: ["admin-audit"], queryFn: () => api.get<Audit[]>("/admin/audit-logs") });
  const [closeJob, setCloseJob] = React.useState<AdminJob | null>(null);
  const toggle = useMutation({
    mutationFn: (u: AdminUser) => api.patch(`/admin/users/${u.id}`, { is_active: !u.is_active }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-users"] }); toast.success("Bijgewerkt"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const close = useMutation({
    mutationFn: (id: string) => api.post(`/admin/jobs/${id}/close`),
    onSuccess: () => { setCloseJob(null); qc.invalidateQueries({ queryKey: ["admin-jobs"] }); toast.success("Vacature gesloten"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const s = stats.data;
  return (
    <>
      <PageHeader title="Beheer" description="Platformstatistieken, gebruikers, vacatures en het auditlogboek." />
      {stats.error ? <QueryError error={stats.error} /> : !s ? <Skeleton className="h-32" /> : (
        <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
          <Stat label="Kandidaten" value={s.users.candidate ?? 0} />
          <Stat label="Werkgevers" value={s.users.employer ?? 0} />
          <Stat label="Open vacatures" value={s.jobs.published} />
          <Stat label="Sollicitaties" value={s.applications} />
          <Stat label="Cv-versies" value={s.cv_versions} />
          <Stat label="Taken in wachtrij" value={`${s.tasks.queued} / ${s.tasks.running} actief`} />
        </div>
      )}
      <Tabs defaultValue="users">
        <TabsList className="mb-4"><TabsTrigger value="users">Gebruikers</TabsTrigger><TabsTrigger value="jobs">Vacatures</TabsTrigger><TabsTrigger value="ai">AI-gebruik</TabsTrigger><TabsTrigger value="audit">Auditlog</TabsTrigger></TabsList>
        <TabsContent value="users">
          <Card>
            <CardBody className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-2">
                <Input value={userQ} onChange={(e) => setUserQ(e.target.value)} placeholder="Zoek op naam of e-mail" className="max-w-xs" aria-label="Zoek gebruikers" />
                <Select value={role} onChange={(e) => setRole(e.target.value)} className="w-auto" aria-label="Rol"><option value="">Alle rollen</option>{["candidate", "employer", "admin"].map((r) => <option key={r} value={r}>{t(`enums.role.${r}`)}</option>)}</Select>
              </div>
              {!users.data ? <Skeleton className="h-32" /> : (
                <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-sm">
                  <thead className="text-left text-muted"><tr><th className="py-2 font-medium">Naam</th><th className="py-2 font-medium">Rol</th><th className="py-2 font-medium">Aangemaakt</th><th className="py-2 font-medium">Laatst actief</th><th className="py-2"><span className="sr-only">Acties</span></th></tr></thead>
                  <tbody>{users.data.items.map((u) => (
                    <tr key={u.id} className="border-t border-border">
                      <td className="py-2.5"><p className="font-medium text-text">{u.full_name} {u.is_demo && <Badge>Demo</Badge>}</p><p className="text-xs text-muted">{u.email}{!u.email_verified && " · niet bevestigd"}</p></td>
                      <td className="py-2.5">{t(`enums.role.${u.role}`)}</td>
                      <td className="py-2.5 text-text-2">{formatDate(u.created_at)}</td>
                      <td className="py-2.5 text-text-2">{u.last_active_at ? formatDate(u.last_active_at) : "—"}</td>
                      <td className="py-2.5 text-right"><Button size="sm" variant={u.is_active ? "ghost" : "secondary"} loading={toggle.isPending && toggle.variables?.id === u.id} onClick={() => toggle.mutate(u)}>{u.is_active ? "Blokkeren" : "Activeren"}</Button></td>
                    </tr>
                  ))}</tbody>
                </table></div>
              )}
            </CardBody>
          </Card>
        </TabsContent>
        <TabsContent value="jobs">
          <Card><CardBody>
            {!jobs.data ? <Skeleton className="h-32" /> : (
              <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-sm">
                <thead className="text-left text-muted"><tr><th className="py-2 font-medium">Vacature</th><th className="py-2 font-medium">Status</th><th className="py-2 font-medium">Bron</th><th className="py-2 font-medium">Gepubliceerd</th><th className="py-2"><span className="sr-only">Acties</span></th></tr></thead>
                <tbody>{jobs.data.items.map((j) => (
                  <tr key={j.id} className="border-t border-border">
                    <td className="py-2.5"><p className="font-medium text-text">{j.title}</p><p className="text-xs text-muted">{j.company_name}</p></td>
                    <td className="py-2.5">{t(`enums.jobStatus.${j.status}`)}</td>
                    <td className="py-2.5">{j.is_demo ? <Badge>Demo</Badge> : j.source}</td>
                    <td className="py-2.5 text-text-2">{j.published_at ? formatDate(j.published_at) : "—"}</td>
                    <td className="py-2.5 text-right">{j.status === "published" && <Button size="sm" variant="ghost" onClick={() => setCloseJob(j)}>Sluiten</Button>}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
          </CardBody></Card>
        </TabsContent>
        <TabsContent value="ai">
          <Card><CardHeader title="AI-aanroepen" description="Laatste 30 dagen. Prompts en antwoorden worden niet bewaard." /><CardBody>
            {!s ? <Skeleton className="h-24" /> : s.ai_usage_30d.length === 0 ? <p className="text-sm text-muted">Nog geen AI-aanroepen.</p> : (
              <table className="w-full text-sm"><thead className="text-left text-muted"><tr><th className="py-2 font-medium">Bewerking</th><th className="py-2 font-medium">Aanroepen</th><th className="py-2 font-medium">Geslaagd</th><th className="py-2 font-medium">Gem. duur</th></tr></thead>
                <tbody>{s.ai_usage_30d.map((r) => <tr key={r.operation} className="border-t border-border"><td className="py-2">{OPS[r.operation] ?? r.operation}</td><td className="py-2 tabular-nums">{r.calls}</td><td className="py-2 tabular-nums">{r.succeeded}</td><td className="py-2 tabular-nums">{(r.avg_ms / 1000).toFixed(1)} s</td></tr>)}</tbody></table>
            )}
          </CardBody></Card>
        </TabsContent>
        <TabsContent value="audit">
          <Card><CardBody>
            {audit.error ? <QueryError error={audit.error} /> : !audit.data ? <Skeleton className="h-32" /> : (
              <ul className="divide-y divide-border text-sm">{audit.data.map((a) => (
                <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2"><span className="font-mono text-xs text-text">{a.action}</span><span className="text-xs text-muted">{a.target_type} · {formatDateTime(a.created_at)}</span></li>
              ))}</ul>
            )}
          </CardBody></Card>
        </TabsContent>
      </Tabs>
      <ConfirmDialog open={!!closeJob} onOpenChange={(o) => !o && setCloseJob(null)} title="Vacature sluiten?" description={`‘${closeJob?.title}’ is daarna niet meer zichtbaar in de zoekresultaten.`}
        confirmLabel="Sluiten" loading={close.isPending} onConfirm={() => closeJob && close.mutate(closeJob.id)} />
    </>
  );
}
