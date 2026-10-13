"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Briefcase, FileText, ImageUp, Plus, Trash2, UserPlus, Users } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import * as React from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { PageSkeleton } from "@/components/page-suspense";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Alert, Badge, EmptyState, Skeleton } from "@/components/ui/feedback";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { statusTone } from "@/features/applications/tracker";
import { CompanyLogo } from "@/features/jobs/company-logo";
import { useMe } from "@/hooks/use-auth";
import { api, errorMessage } from "@/lib/api";
import { formatDate, formatDateTime, period } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Applicant, ApplicationStatus, Company, JobSummary, Member } from "@/types/api";
import { useDraft } from "@/hooks/use-draft";

interface EmployerDashboard {
  companies: number;
  jobs: { total: number; draft: number; published: number; closed: number };
  applications: { total: number } & Partial<Record<ApplicationStatus, number>>;
  per_job: { job_id: string; title: string; count: number }[];
  timeline: { date: string; count: number }[];
  recent: { id: string; job_title: string; candidate_name: string; status: ApplicationStatus; applied_at: string | null }[];
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return <Card><CardBody><p className="text-sm text-muted">{label}</p><p className="mt-1 text-2xl font-semibold tabular-nums text-text">{value}</p></CardBody></Card>;
}

export function EmployerDashboardPage() {
  const me = useMe();
  const d = useQuery({ queryKey: ["employer-dashboard"], queryFn: () => api.get<EmployerDashboard>("/employer/dashboard") });
  if (d.error) return <QueryError error={d.error} onRetry={() => d.refetch()} />;
  const company = me.data?.companies[0];
  return (
    <>
      <PageHeader title={company ? company.name : "Werkgeversoverzicht"} description="Je vacatures en kandidaten in één oogopslag."
        actions={<Button asChild><Link href="/employer/jobs/new"><Plus />Nieuwe vacature</Link></Button>} />
      {me.data && me.data.companies.length === 0 && <Alert tone="accent" className="mb-6" action={<Button asChild size="sm"><Link href="/employer/company">Bedrijf aanmaken</Link></Button>}>Maak eerst een bedrijfsprofiel aan.</Alert>}
      {!d.data ? <Skeleton className="h-64" /> : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat label="Gepubliceerde vacatures" value={d.data.jobs.published} />
            <Stat label="Concepten" value={d.data.jobs.draft} />
            <Stat label="Sollicitaties" value={d.data.applications.total} />
            <Stat label="In gesprek" value={d.data.applications.interview ?? 0} />
          </div>
          <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <Card>
              <CardHeader title="Sollicitaties per dag" description="Laatste 30 dagen" />
              <CardBody className="h-64">
                {d.data.applications.total === 0 ? <p className="text-sm text-muted">Nog geen sollicitaties ontvangen.</p> : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={d.data.timeline} margin={{ left: -20, right: 8 }}>
                      <CartesianGrid vertical={false} stroke="var(--border)" />
                      <XAxis dataKey="date" tickFormatter={(v: string) => v.slice(8, 10)} tick={{ fontSize: 11, fill: "var(--muted)" }} axisLine={false} tickLine={false} interval={4} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "var(--muted)" }} axisLine={false} tickLine={false} />
                      <Tooltip cursor={{ fill: "var(--surface-2)" }} contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                        labelFormatter={(v) => formatDate(String(v))} formatter={(v) => [v, "Sollicitaties"]} />
                      <Bar dataKey="count" fill="var(--accent)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Recente sollicitaties" action={<Link href="/employer/applications" className="text-sm text-accent hover:underline">Alle</Link>} />
              <CardBody>
                {d.data.recent.length === 0 ? <p className="text-sm text-muted">Nog niets ontvangen.</p> : (
                  <ul className="flex flex-col gap-3">
                    {d.data.recent.map((r) => (
                      <li key={r.id} className="flex items-center justify-between gap-2 text-sm">
                        <div className="min-w-0"><Link href={`/employer/applications/${r.id}`} className="font-medium text-text hover:text-accent">{r.candidate_name}</Link><p className="truncate text-xs text-muted">{r.job_title}</p></div>
                        <Badge tone={statusTone[r.status]}>{t(`enums.applicationStatus.${r.status}`)}</Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </CardBody>
            </Card>
          </div>
          {d.data.per_job.length > 0 && (
            <Card>
              <CardHeader title="Sollicitaties per vacature" />
              <CardBody><ul className="flex flex-col gap-2 text-sm">{d.data.per_job.map((p) => (
                <li key={p.job_id} className="flex items-center gap-3"><span className="w-56 truncate text-text-2">{p.title}</span>
                  <div className="h-2 flex-1 rounded-full bg-surface-2"><div className="h-full rounded-full bg-accent" style={{ width: `${(p.count / Math.max(...d.data!.per_job.map((x) => x.count))) * 100}%` }} /></div>
                  <span className="w-8 text-right tabular-nums text-text">{p.count}</span></li>
              ))}</ul></CardBody>
            </Card>
          )}
        </div>
      )}
    </>
  );
}

export function EmployerJobsPage() {
  const me = useMe();
  const companyId = me.data?.companies[0]?.id;
  const jobs = useQuery({ queryKey: ["employer-jobs", companyId], queryFn: () => api.get<JobSummary[]>(`/companies/${companyId}/jobs`), enabled: !!companyId });
  return (
    <>
      <PageHeader title="Vacatures" actions={<Button asChild><Link href="/employer/jobs/new"><Plus />Nieuwe vacature</Link></Button>} />
      {me.data && !companyId ? <Alert tone="accent">Maak eerst een <Link href="/employer/company" className="underline">bedrijfsprofiel</Link> aan.</Alert> :
        jobs.error ? <QueryError error={jobs.error} /> : !jobs.data ? <Skeleton className="h-40" /> : jobs.data.length === 0 ? (
          <EmptyState icon={Briefcase} title="Nog geen vacatures" action={<Button asChild><Link href="/employer/jobs/new">Eerste vacature maken</Link></Button>} />
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-card">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="border-b border-border text-left text-muted"><tr><th className="px-4 py-3 font-medium">Titel</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Gepubliceerd</th><th className="px-4 py-3 font-medium">Plaats</th><th className="px-4 py-3"><span className="sr-only">Acties</span></th></tr></thead>
              <tbody>
                {jobs.data.map((j) => (
                  <tr key={j.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3"><Link href={`/jobs/${j.id}`} className="font-medium text-text hover:text-accent">{j.title}</Link></td>
                    <td className="px-4 py-3"><Badge tone={j.status === "published" ? "success" : j.status === "draft" ? "neutral" : "danger"}>{t(`enums.jobStatus.${j.status}`)}</Badge></td>
                    <td className="px-4 py-3 text-text-2">{j.published_at ? formatDate(j.published_at) : "—"}</td>
                    <td className="px-4 py-3 text-text-2">{j.city ?? "—"}</td>
                    <td className="px-4 py-3 text-right"><div className="flex justify-end gap-1">
                      <Button asChild size="sm" variant="ghost"><Link href={`/employer/applications?job=${j.id}`}><Users />Kandidaten</Link></Button>
                      <Button asChild size="sm" variant="secondary"><Link href={`/employer/jobs/${j.id}/edit`}>Bewerken</Link></Button>
                    </div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </>
  );
}

const EMPLOYER_STATUSES: ApplicationStatus[] = ["in_review", "interview", "offer", "rejected"];

export function ApplicantsPage() {
  const params = useSearchParams();
  const [status, setStatus] = React.useState("");
  const jobId = params.get("job");
  const list = useQuery({ queryKey: ["applicants", jobId, status], queryFn: () => api.get<Applicant[]>(`/employer/applications?${new URLSearchParams({ ...(jobId ? { job_id: jobId } : {}), ...(status ? { status } : {}) })}`) });
  return (
    <>
      <PageHeader title="Kandidaten" description="Sollicitaties via het platform. Kandidaten worden niet automatisch gerangschikt: jij beoordeelt."
        actions={<Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-auto" aria-label="Status"><option value="">Alle statussen</option>{(["applied", ...EMPLOYER_STATUSES, "withdrawn"] as ApplicationStatus[]).map((s) => <option key={s} value={s}>{t(`enums.applicationStatus.${s}`)}</option>)}</Select>} />
      {jobId && <p className="-mt-3 mb-4 text-sm text-muted">Gefilterd op één vacature · <Link href="/employer/applications" className="text-accent hover:underline">alle tonen</Link></p>}
      {list.error ? <QueryError error={list.error} /> : !list.data ? <Skeleton className="h-40" /> : list.data.length === 0 ? <EmptyState icon={Users} title="Geen sollicitaties" /> : (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-card">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="border-b border-border text-left text-muted"><tr><th className="px-4 py-3 font-medium">Kandidaat</th><th className="px-4 py-3 font-medium">Vacature</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Ontvangen</th><th className="px-4 py-3"><span className="sr-only">Openen</span></th></tr></thead>
            <tbody>
              {list.data.map((a) => (
                <tr key={a.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3"><p className="font-medium text-text">{a.candidate_name}</p><p className="text-xs text-muted">{a.candidate_headline ?? a.candidate_city ?? ""}</p></td>
                  <td className="px-4 py-3 text-text-2">{a.job_title}</td>
                  <td className="px-4 py-3"><Badge tone={statusTone[a.status]}>{t(`enums.applicationStatus.${a.status}`)}</Badge></td>
                  <td className="px-4 py-3 text-text-2">{a.applied_at ? formatDate(a.applied_at) : "—"}</td>
                  <td className="px-4 py-3 text-right"><Button asChild size="sm" variant="secondary"><Link href={`/employer/applications/${a.id}`}>Bekijken</Link></Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export function ApplicantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const a = useQuery({ queryKey: ["applicant", id], queryFn: () => api.get<Applicant>(`/employer/applications/${id}`) });
  const [status, setStatus] = React.useState<ApplicationStatus | "">("");
  const [note, setNote] = React.useState("");
  const update = useMutation({
    mutationFn: () => api.patch<Applicant>(`/employer/applications/${id}`, { status, note: note || null }),
    onSuccess: (data) => { qc.setQueryData(["applicant", id], data); qc.invalidateQueries({ queryKey: ["applicants"] }); setNote(""); setStatus(""); toast.success("Status bijgewerkt; de kandidaat krijgt een melding."); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  if (a.error) return <QueryError error={a.error} />;
  if (!a.data) return <PageSkeleton />;
  const d = a.data;
  const cv = d.cv;
  return (
    <div className="flex flex-col gap-6">
      <Link href="/employer/applications" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-text"><ArrowLeft className="size-4" />Kandidaten</Link>
      <PageHeader title={d.candidate_name} description={`${d.job_title} · ontvangen ${d.applied_at ? formatDateTime(d.applied_at) : ""}`}
        actions={<><Badge tone={statusTone[d.status]} className="px-3 py-1 text-sm">{t(`enums.applicationStatus.${d.status}`)}</Badge>
          {d.has_cv && <Button asChild variant="secondary"><a href={`/api/v1/employer/applications/${d.id}/cv`} target="_blank" rel="noreferrer"><FileText />Cv (PDF)</a></Button>}</>} />
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="flex flex-col gap-6">
          {d.cover_letter && <Card><CardHeader title="Motivatie" /><CardBody><p className="whitespace-pre-line text-sm text-text-2">{d.cover_letter}</p></CardBody></Card>}
          {cv && (
            <Card>
              <CardHeader title="Gedeeld cv" description="Gedeeld door de kandidaat bij het solliciteren." />
              <CardBody className="flex flex-col gap-4 text-sm">
                {cv.headline && <p className="font-medium text-text">{cv.headline}</p>}
                {cv.summary && <p className="text-text-2">{cv.summary}</p>}
                {cv.experiences.map((e, i) => (
                  <div key={i}><p className="font-medium text-text">{e.title} — {e.employer}</p><p className="text-xs text-muted">{period(e.start, e.end, e.is_current)}</p>
                    <ul className="mt-1 list-disc pl-5 text-text-2">{e.bullets.map((b, k) => <li key={k}>{b.text}</li>)}</ul></div>
                ))}
                {cv.skills.length > 0 && <p className="text-text-2"><span className="font-medium text-text">Vaardigheden:</span> {cv.skills.join(", ")}</p>}
                {cv.education.length > 0 && <p className="text-text-2"><span className="font-medium text-text">Opleiding:</span> {cv.education.map((e) => `${e.degree} (${e.institution})`).join("; ")}</p>}
              </CardBody>
            </Card>
          )}
        </div>
        <aside className="flex flex-col gap-6">
          <Card>
            <CardHeader title="Contact" />
            <CardBody className="text-sm text-text-2"><p><a href={`mailto:${d.candidate_email}`} className="text-accent hover:underline">{d.candidate_email}</a></p>{d.candidate_city && <p>{d.candidate_city}</p>}</CardBody>
          </Card>
          <Card>
            <CardHeader title="Vaardigheden t.o.v. de vacature" description="Feitelijke overlap, geen rangschikking." />
            <CardBody className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-1.5">{d.matching_skills.map((s) => <Badge key={s} tone="success">{s}</Badge>)}{d.matching_skills.length === 0 && <span className="text-sm text-muted">—</span>}</div>
              {d.missing_required_skills.length > 0 && <div><p className="mb-1 text-xs text-muted">Niet gevonden:</p><div className="flex flex-wrap gap-1.5">{d.missing_required_skills.map((s) => <Badge key={s} tone="warning">{s}</Badge>)}</div></div>}
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Status wijzigen" />
            <CardBody className="flex flex-col gap-3">
              {d.status === "withdrawn" ? <p className="text-sm text-muted">De kandidaat heeft deze sollicitatie ingetrokken.</p> : (
                <>
                  <Select value={status} onChange={(e) => setStatus(e.target.value as ApplicationStatus)} aria-label="Nieuwe status">
                    <option value="">Kies een status</option>{EMPLOYER_STATUSES.map((s) => <option key={s} value={s}>{t(`enums.applicationStatus.${s}`)}</option>)}
                  </Select>
                  <Textarea rows={2} value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} placeholder="Notitie (zichtbaar voor de kandidaat)" aria-label="Notitie" />
                  <Button disabled={!status} loading={update.isPending} onClick={() => update.mutate()}>Bijwerken</Button>
                </>
              )}
              <ol className="mt-2 flex flex-col gap-1.5 border-l border-border pl-4 text-xs text-muted">
                {d.history.map((h, i) => <li key={i}><span className="font-medium text-text-2">{t(`enums.applicationStatus.${h.to_status}`)}</span> · {formatDateTime(h.created_at)}{h.note && ` · ${h.note}`}</li>)}
              </ol>
            </CardBody>
          </Card>
        </aside>
      </div>
    </div>
  );
}

export function CompanySettingsPage() {
  const me = useMe();
  const qc = useQueryClient();
  const companyId = me.data?.companies[0]?.id;
  const company = useQuery({ queryKey: ["company", companyId], queryFn: () => api.get<Company>(`/companies/${companyId}`), enabled: !!companyId });
  const members = useQuery({ queryKey: ["members", companyId], queryFn: () => api.get<Member[]>(`/companies/${companyId}/members`), enabled: !!companyId });
  const emptyCompany = { name: "", description: "", website_url: "", industry: "", city: "", size: "" };
  const [draft, setForm] = useDraft<Company | null, typeof emptyCompany>(companyId ? company.data : null, companyId ? company.data?.name + (company.data?.description ?? "") : "new",
    (c) => (c ? { name: c.name, description: c.description ?? "", website_url: c.website_url ?? "", industry: c.industry ?? "", city: c.city ?? "", size: c.size ?? "" } : emptyCompany));
  const form = draft ?? emptyCompany;
  const [invite, setInvite] = React.useState("");
  const body = () => Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v.trim() || null]));
  const save = useMutation({
    mutationFn: () => (companyId ? api.patch<Company>(`/companies/${companyId}`, body()) : api.post<Company>("/companies", body())),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["company"] }); qc.invalidateQueries({ queryKey: ["me"] }); toast.success("Bedrijfsprofiel opgeslagen"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const logo = useMutation({
    mutationFn: (file: File) => { const f = new FormData(); f.append("file", file); return api.post<Company>(`/companies/${companyId}/logo`, f); },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["company", companyId] }); toast.success("Logo bijgewerkt"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const addMember = useMutation({
    mutationFn: () => api.post(`/companies/${companyId}/members`, { email: invite, role: "recruiter" }),
    onSuccess: () => { setInvite(""); qc.invalidateQueries({ queryKey: ["members", companyId] }); toast.success("Collega toegevoegd"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const removeMember = useMutation({
    mutationFn: (userId: string) => api.delete(`/companies/${companyId}/members/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members", companyId] }),
    onError: (e) => toast.error(errorMessage(e)),
  });
  if (companyId && !company.data) return <PageSkeleton />;
  const isOwner = me.data?.companies[0]?.role === "owner";
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });
  return (
    <>
      <PageHeader title="Bedrijfsprofiel" description="Zo zien kandidaten je bedrijf." />
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <Card>
          <CardBody className="grid gap-4 sm:grid-cols-2">
            <Field label="Naam" className="sm:col-span-2"><Input value={form.name} onChange={set("name")} /></Field>
            <Field label="Beschrijving" className="sm:col-span-2"><Textarea rows={5} value={form.description} onChange={set("description")} /></Field>
            <Field label="Sector"><Input value={form.industry} onChange={set("industry")} /></Field>
            <Field label="Plaats"><Input value={form.city} onChange={set("city")} /></Field>
            <Field label="Website"><Input value={form.website_url} placeholder="https://" onChange={set("website_url")} /></Field>
            <Field label="Grootte"><Select value={form.size} onChange={set("size")}><option value="">—</option>{["1-10", "11-50", "51-200", "201-1000", "1000+"].map((s) => <option key={s} value={s}>{s} medewerkers</option>)}</Select></Field>
            <div className="sm:col-span-2"><Button disabled={form.name.trim().length < 2} loading={save.isPending} onClick={() => save.mutate()}>{companyId ? "Opslaan" : "Bedrijf aanmaken"}</Button></div>
          </CardBody>
        </Card>
        {companyId && company.data && (
          <aside className="flex flex-col gap-6">
            <Card>
              <CardHeader title="Logo" />
              <CardBody className="flex items-center gap-4">
                <CompanyLogo company={company.data} size={64} />
                <label className="cursor-pointer text-sm font-medium text-accent hover:underline">
                  <ImageUp className="mr-1 inline size-4" />{logo.isPending ? "Uploaden…" : "Logo uploaden"}
                  <input type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" onChange={(e) => { const f = e.target.files?.[0]; if (f) logo.mutate(f); e.target.value = ""; }} />
                </label>
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Collega's" />
              <CardBody className="flex flex-col gap-3">
                <ul className="flex flex-col gap-2 text-sm">
                  {members.data?.map((m) => (
                    <li key={m.user_id} className="flex items-center justify-between gap-2">
                      <div className="min-w-0"><p className="truncate font-medium text-text">{m.full_name}</p><p className="truncate text-xs text-muted">{m.email} · {m.role === "owner" ? "eigenaar" : "recruiter"}</p></div>
                      {isOwner && m.user_id !== me.data?.id && <Button size="icon" variant="ghost" aria-label="Verwijderen" onClick={() => removeMember.mutate(m.user_id)}><Trash2 /></Button>}
                    </li>
                  ))}
                </ul>
                {isOwner && (
                  <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); addMember.mutate(); }}>
                    <Input type="email" value={invite} onChange={(e) => setInvite(e.target.value)} placeholder="collega@bedrijf.be" aria-label="E-mailadres collega" />
                    <Button type="submit" size="icon" className="size-10" loading={addMember.isPending} disabled={!invite} aria-label="Toevoegen"><UserPlus /></Button>
                  </form>
                )}
                <p className="text-xs text-muted">Collega&apos;s hebben eerst een eigen werkgeversaccount nodig.</p>
              </CardBody>
            </Card>
          </aside>
        )}
      </div>
    </>
  );
}
