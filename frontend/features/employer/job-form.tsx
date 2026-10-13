"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { PageSkeleton } from "@/components/page-suspense";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Alert } from "@/components/ui/feedback";
import { Checkbox, Field, Input, Select, Textarea } from "@/components/ui/input";
import { TagInput } from "@/components/ui/tag-input";
import { useMe } from "@/hooks/use-auth";
import { api, ApiError, errorMessage } from "@/lib/api";
import { t } from "@/lib/i18n";
import type { EducationLevel, EmploymentType, ExperienceLevel, JobDetail, RemotePolicy, SalaryPeriod } from "@/types/api";
import { useDraft } from "@/hooks/use-draft";

interface FormState {
  title: string; description: string; responsibilities: string[]; qualifications: string[];
  skills: { name: string; is_required: boolean }[];
  min_years_experience: string; experience_level: ExperienceLevel | ""; education_level: EducationLevel | ""; required_languages: string[];
  city: string; remote_policy: RemotePolicy; employment_type: EmploymentType; salary_min: string; salary_max: string; salary_period: SalaryPeriod | "";
  industry: string; language: "nl" | "fr" | "en"; application_deadline: string; application_url: string;
}

const empty: FormState = {
  title: "", description: "", responsibilities: [""], qualifications: [""], skills: [{ name: "", is_required: true }], min_years_experience: "",
  experience_level: "", education_level: "", required_languages: ["nl"], city: "", remote_policy: "hybrid", employment_type: "full_time",
  salary_min: "", salary_max: "", salary_period: "month", industry: "", language: "nl", application_deadline: "", application_url: "",
};

function fromJob(j: JobDetail): FormState {
  return {
    title: j.title, description: j.description, responsibilities: j.responsibilities.length ? j.responsibilities : [""],
    qualifications: j.qualifications.length ? j.qualifications : [""], skills: j.skills.length ? j.skills : [{ name: "", is_required: true }],
    min_years_experience: j.min_years_experience?.toString() ?? "", experience_level: j.experience_level ?? "", education_level: j.education_level ?? "",
    required_languages: j.required_languages, city: j.city ?? "", remote_policy: j.remote_policy, employment_type: j.employment_type,
    salary_min: j.salary_min?.toString() ?? "", salary_max: j.salary_max?.toString() ?? "", salary_period: j.salary_period ?? "month",
    industry: j.industry ?? "", language: (j.language as FormState["language"]) ?? "nl", application_deadline: j.application_deadline ?? "", application_url: j.application_url ?? "",
  };
}

function toBody(f: FormState) {
  const num = (v: string) => (v.trim() === "" ? null : Number(v));
  const hasSalary = f.salary_min.trim() !== "" || f.salary_max.trim() !== "";
  return {
    title: f.title, description: f.description,
    responsibilities: f.responsibilities.map((x) => x.trim()).filter(Boolean), qualifications: f.qualifications.map((x) => x.trim()).filter(Boolean),
    skills: f.skills.filter((s) => s.name.trim()), min_years_experience: num(f.min_years_experience),
    experience_level: f.experience_level || null, education_level: f.education_level || null, required_languages: f.required_languages,
    city: f.city || null, remote_policy: f.remote_policy, employment_type: f.employment_type,
    salary_min: num(f.salary_min), salary_max: num(f.salary_max), salary_period: hasSalary ? f.salary_period || null : null, salary_currency: "EUR",
    industry: f.industry || null, language: f.language, application_deadline: f.application_deadline || null, application_url: f.application_url || null,
  };
}

function ListEditor({ value, onChange, label }: { value: string[]; onChange: (v: string[]) => void; label: string }) {
  return (
    <div className="flex flex-col gap-2">
      {value.map((item, i) => (
        <div key={i} className="flex gap-2">
          <Input value={item} aria-label={`${label} ${i + 1}`} onChange={(e) => onChange(value.map((x, j) => (j === i ? e.target.value : x)))} />
          <Button type="button" size="icon" variant="ghost" aria-label="Verwijderen" onClick={() => onChange(value.filter((_, j) => j !== i))}><Trash2 /></Button>
        </div>
      ))}
      <Button type="button" size="sm" variant="ghost" className="self-start" onClick={() => onChange([...value, ""])}><Plus />Toevoegen</Button>
    </div>
  );
}

export function JobForm({ mode }: { mode: "new" | "edit" }) {
  const params = useParams<{ id?: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const me = useMe();
  const existing = useQuery({ queryKey: ["job", params.id], queryFn: () => api.get<JobDetail>(`/jobs/${params.id}`), enabled: mode === "edit" });
  const [form, setForm] = useDraft<JobDetail | null, FormState>(mode === "new" ? null : existing.data, mode === "new" ? "new" : existing.data?.updated_at,
    (job) => (job ? fromJob(job) : empty));
  const [errors, setErrors] = React.useState<string[]>([]);
  const companyId = me.data?.companies[0]?.id;

  const save = useMutation({
    mutationFn: (status: "draft" | "published" | "closed" | undefined) => {
      const body = { ...toBody(form!), ...(status ? { status } : {}) };
      return mode === "new" ? api.post<JobDetail>(`/companies/${companyId}/jobs`, body) : api.patch<JobDetail>(`/jobs/${params.id}`, body);
    },
    onSuccess: (job) => {
      qc.invalidateQueries({ queryKey: ["employer-jobs"] });
      qc.setQueryData(["job", job.id], job);
      toast.success(job.status === "published" ? "Vacature gepubliceerd" : job.status === "closed" ? "Vacature gesloten" : "Opgeslagen als concept");
      router.push("/employer/jobs");
    },
    onError: (e) => {
      if (e instanceof ApiError && Array.isArray(e.details)) setErrors((e.details as { field: string; message: string }[]).map((d) => `${d.field}: ${d.message}`));
      else setErrors([errorMessage(e)]);
    },
  });

  if (existing.error) return <QueryError error={existing.error} />;
  if (!form) return <PageSkeleton />;
  if (mode === "new" && me.data && !companyId) return <Alert tone="warning">Maak eerst een <Link href="/employer/company" className="underline">bedrijfsprofiel</Link> aan.</Alert>;
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setForm((f) => ({ ...f, [k]: v }));
  const submit = (status?: "draft" | "published" | "closed") => {
    const problems: string[] = [];
    if (form.title.trim().length < 3) problems.push("Geef de vacature een titel.");
    if (form.description.trim().length < 20) problems.push("De beschrijving moet minstens 20 tekens bevatten.");
    if (form.salary_min && form.salary_max && Number(form.salary_min) > Number(form.salary_max)) problems.push("Het minimumloon is hoger dan het maximum.");
    if (form.application_url && !/^https?:\/\//.test(form.application_url)) problems.push("De sollicitatielink moet met https:// beginnen.");
    setErrors(problems);
    if (!problems.length) save.mutate(status);
  };
  const status = existing.data?.status;

  return (
    <div className="flex flex-col gap-6">
      <Link href="/employer/jobs" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-text"><ArrowLeft className="size-4" />Vacatures</Link>
      <PageHeader title={mode === "new" ? "Nieuwe vacature" : "Vacature bewerken"} description="Duidelijke vaardigheden en vereisten zorgen voor betere, eerlijkere matches." />
      {errors.length > 0 && <Alert tone="danger" title="Controleer het formulier"><ul className="list-disc pl-4">{errors.map((e) => <li key={e}>{e}</li>)}</ul></Alert>}
      {!me.data?.email_verified && <Alert tone="warning">Bevestig eerst je e-mailadres om vacatures te publiceren. Opslaan als concept kan wel.</Alert>}

      <Card>
        <CardHeader title="Functie" />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Functietitel" className="sm:col-span-2"><Input value={form.title} onChange={(e) => set("title", e.target.value)} /></Field>
          <Field label="Beschrijving" className="sm:col-span-2"><Textarea rows={6} value={form.description} onChange={(e) => set("description", e.target.value)} /></Field>
          <Field label="Taken" className="sm:col-span-2"><ListEditor label="Taak" value={form.responsibilities} onChange={(v) => set("responsibilities", v)} /></Field>
          <Field label="Profiel / vereisten" className="sm:col-span-2"><ListEditor label="Vereiste" value={form.qualifications} onChange={(v) => set("qualifications", v)} /></Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Vaardigheden en vereisten" description="Verplichte vaardigheden wegen dubbel in de match. Taal- en opleidingseisen worden als harde eis getoond." />
        <CardBody className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            {form.skills.map((s, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input value={s.name} placeholder="bv. Python" aria-label={`Vaardigheid ${i + 1}`} onChange={(e) => set("skills", form.skills.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
                <Checkbox className="shrink-0" label="Verplicht" checked={s.is_required} onChange={(e) => set("skills", form.skills.map((x, j) => (j === i ? { ...x, is_required: e.target.checked } : x)))} />
                <Button type="button" size="icon" variant="ghost" aria-label="Verwijderen" onClick={() => set("skills", form.skills.filter((_, j) => j !== i))}><Trash2 /></Button>
              </div>
            ))}
            <Button type="button" size="sm" variant="ghost" className="self-start" onClick={() => set("skills", [...form.skills, { name: "", is_required: false }])}><Plus />Vaardigheid toevoegen</Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Min. jaren ervaring"><Input type="number" min={0} max={40} value={form.min_years_experience} onChange={(e) => set("min_years_experience", e.target.value)} /></Field>
            <Field label="Niveau"><Select value={form.experience_level} onChange={(e) => set("experience_level", e.target.value as ExperienceLevel | "")}><option value="">—</option>{(["junior", "medior", "senior", "lead"] as ExperienceLevel[]).map((l) => <option key={l} value={l}>{t(`enums.experienceLevel.${l}`)}</option>)}</Select></Field>
            <Field label="Opleiding"><Select value={form.education_level} onChange={(e) => set("education_level", e.target.value as EducationLevel | "")}><option value="">Geen vereiste</option>{(["secondary", "professional_bachelor", "bachelor", "master", "phd"] as EducationLevel[]).map((l) => <option key={l} value={l}>{t(`enums.education.${l}`)}</option>)}</Select></Field>
          </div>
          <Field label="Vereiste talen" hint="Taalcodes, bv. nl, fr, en"><TagInput value={form.required_languages} onChange={(v) => set("required_languages", v.map((x) => x.toLowerCase()))} max={6} /></Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Voorwaarden" />
        <CardBody className="grid gap-4 sm:grid-cols-3">
          <Field label="Plaats"><Input value={form.city} onChange={(e) => set("city", e.target.value)} /></Field>
          <Field label="Thuiswerk"><Select value={form.remote_policy} onChange={(e) => set("remote_policy", e.target.value as RemotePolicy)}>{(["onsite", "hybrid", "remote"] as RemotePolicy[]).map((r) => <option key={r} value={r}>{t(`enums.remote.${r}`)}</option>)}</Select></Field>
          <Field label="Contract"><Select value={form.employment_type} onChange={(e) => set("employment_type", e.target.value as EmploymentType)}>{(["full_time", "part_time", "contract", "freelance", "internship", "temporary"] as EmploymentType[]).map((x) => <option key={x} value={x}>{t(`enums.employmentType.${x}`)}</option>)}</Select></Field>
          <Field label="Loon van (€ bruto)"><Input type="number" min={0} value={form.salary_min} onChange={(e) => set("salary_min", e.target.value)} /></Field>
          <Field label="Loon tot (€ bruto)"><Input type="number" min={0} value={form.salary_max} onChange={(e) => set("salary_max", e.target.value)} /></Field>
          <Field label="Per"><Select value={form.salary_period} onChange={(e) => set("salary_period", e.target.value as SalaryPeriod)}>{(["month", "year", "hour"] as SalaryPeriod[]).map((p) => <option key={p} value={p}>{t(`enums.salaryPeriod.${p}`)}</option>)}</Select></Field>
          <Field label="Sector"><Input value={form.industry} onChange={(e) => set("industry", e.target.value)} /></Field>
          <Field label="Taal van de vacature"><Select value={form.language} onChange={(e) => set("language", e.target.value as FormState["language"])}>{(["nl", "fr", "en"] as const).map((l) => <option key={l} value={l}>{t(`enums.languages.${l}`)}</option>)}</Select></Field>
          <Field label="Solliciteren tot"><Input type="date" value={form.application_deadline} onChange={(e) => set("application_deadline", e.target.value)} /></Field>
          <Field label="Externe sollicitatielink" hint="Optioneel. Kandidaten kunnen ook via het platform solliciteren." className="sm:col-span-3"><Input value={form.application_url} placeholder="https://" onChange={(e) => set("application_url", e.target.value)} /></Field>
        </CardBody>
      </Card>

      <div className="sticky bottom-0 flex flex-wrap justify-end gap-2 border-t border-border bg-bg/90 py-3 backdrop-blur">
        {status === "published" && <Button variant="ghost" loading={save.isPending && save.variables === "closed"} onClick={() => submit("closed")}>Vacature sluiten</Button>}
        {status !== "published" && <Button variant="secondary" loading={save.isPending && save.variables === "draft"} onClick={() => submit("draft")}>Opslaan als concept</Button>}
        {status === "published" ? (
          <Button loading={save.isPending && save.variables === undefined} onClick={() => submit(undefined)}>Wijzigingen opslaan</Button>
        ) : (
          <Button loading={save.isPending && save.variables === "published"} disabled={!me.data?.email_verified} onClick={() => submit("published")}>Publiceren</Button>
        )}
      </div>
    </div>
  );
}

export function NewJobPage() { return <JobForm mode="new" />; }
export function EditJobPage() { return <JobForm mode="edit" />; }
