"use client";

import { ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Checkbox, Field, Input, Select, Textarea } from "@/components/ui/input";
import { TagInput } from "@/components/ui/tag-input";
import { t } from "@/lib/i18n";
import type { Certification, Education, EducationLevel, Experience, LanguageSkill, ProfileContent, Project } from "@/types/api";

export const emptyProfile: ProfileContent = { experiences: [], education: [], skills: [], certifications: [], languages: [], projects: [] };

const YM = /^\d{4}(-(0[1-9]|1[0-2]))?$/;

/** Client-side check before saving; the API validates again. Returns a list of readable problems. */
export function profileProblems(p: ProfileContent): string[] {
  const problems: string[] = [];
  p.experiences.forEach((e, i) => {
    if (!e.title.trim() || !e.employer.trim()) problems.push(`Werkervaring ${i + 1}: functietitel en werkgever zijn verplicht.`);
    for (const [label, v] of [["begindatum", e.start], ["einddatum", e.end]] as const) {
      if (v && !YM.test(v)) problems.push(`Werkervaring ${i + 1}: ${label} als JJJJ-MM (bv. 2021-03).`);
    }
  });
  p.education.forEach((e, i) => {
    if (!e.degree.trim() || !e.institution.trim()) problems.push(`Opleiding ${i + 1}: diploma en onderwijsinstelling zijn verplicht.`);
  });
  p.projects.forEach((pr, i) => { if (!pr.name.trim()) problems.push(`Project ${i + 1}: naam is verplicht.`); });
  p.certifications.forEach((c, i) => { if (!c.name.trim()) problems.push(`Certificaat ${i + 1}: naam is verplicht.`); });
  return problems;
}

function move<T>(list: T[], index: number, delta: number): T[] {
  const next = [...list];
  const target = index + delta;
  if (target < 0 || target >= next.length) return list;
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function ItemShell({ title, onRemove, onUp, onDown, children }: { title: string; onRemove: () => void; onUp?: () => void; onDown?: () => void; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-bg/50 p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="truncate text-sm font-medium text-text">{title}</p>
        <div className="flex items-center gap-1">
          {onUp && <Button type="button" size="icon" variant="ghost" onClick={onUp} aria-label="Omhoog"><ChevronUp /></Button>}
          {onDown && <Button type="button" size="icon" variant="ghost" onClick={onDown} aria-label="Omlaag"><ChevronDown /></Button>}
          <Button type="button" size="icon" variant="ghost" onClick={onRemove} aria-label="Verwijderen"><Trash2 className="text-danger" /></Button>
        </div>
      </div>
      {children}
    </div>
  );
}

function BulletsEditor({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="flex flex-col gap-2">
      {value.map((bullet, i) => (
        <div key={i} className="flex gap-2">
          <Textarea value={bullet} rows={2} className="min-h-0" aria-label={`Opsommingspunt ${i + 1}`} onChange={(e) => onChange(value.map((b, j) => (j === i ? e.target.value : b)))} />
          <Button type="button" size="icon" variant="ghost" onClick={() => onChange(value.filter((_, j) => j !== i))} aria-label="Punt verwijderen"><Trash2 /></Button>
        </div>
      ))}
      <Button type="button" size="sm" variant="ghost" className="self-start" onClick={() => onChange([...value, ""])}><Plus />Punt toevoegen</Button>
    </div>
  );
}

export function ExperienceEditor({ value, onChange }: { value: Experience[]; onChange: (v: Experience[]) => void }) {
  const update = (i: number, patch: Partial<Experience>) => onChange(value.map((e, j) => (j === i ? { ...e, ...patch } : e)));
  return (
    <div className="flex flex-col gap-3">
      {value.map((exp, i) => (
        <ItemShell key={exp.id ?? i} title={exp.title || "Nieuwe functie"} onRemove={() => onChange(value.filter((_, j) => j !== i))}
          onUp={i > 0 ? () => onChange(move(value, i, -1)) : undefined} onDown={i < value.length - 1 ? () => onChange(move(value, i, 1)) : undefined}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Functietitel"><Input value={exp.title} onChange={(e) => update(i, { title: e.target.value })} /></Field>
            <Field label="Werkgever"><Input value={exp.employer} onChange={(e) => update(i, { employer: e.target.value })} /></Field>
            <Field label="Van" hint={exp.start && exp.start.length === 4 ? "Vul ook de maand in (JJJJ-MM) voor een exacte telling" : "JJJJ-MM"}><Input value={exp.start ?? ""} placeholder="2021-03" onChange={(e) => update(i, { start: e.target.value || null })} /></Field>
            <Field label="Tot" hint="JJJJ-MM"><Input value={exp.end ?? ""} placeholder="2023-06" disabled={exp.is_current} onChange={(e) => update(i, { end: e.target.value || null })} /></Field>
            <Field label="Locatie"><Input value={exp.location ?? ""} onChange={(e) => update(i, { location: e.target.value || null })} /></Field>
            <div className="flex flex-wrap items-end gap-x-5 gap-y-2 pb-2">
              <Checkbox checked={exp.is_current} onChange={(e) => update(i, { is_current: e.target.checked, end: e.target.checked ? null : exp.end })} label="Ik werk hier nog" />
              <Checkbox checked={!!exp.is_internship} onChange={(e) => update(i, { is_internship: e.target.checked })} label="Dit was een stage" />
            </div>
          </div>
          <div className="mt-3">
            <p className="mb-1.5 text-sm font-medium text-text-2">Taken en resultaten</p>
            <BulletsEditor value={exp.bullets} onChange={(bullets) => update(i, { bullets })} />
          </div>
        </ItemShell>
      ))}
      <Button type="button" variant="secondary" className="self-start" onClick={() => onChange([...value, { title: "", employer: "", is_current: false, bullets: [""] }])}>
        <Plus />Werkervaring toevoegen
      </Button>
    </div>
  );
}

const EDUCATION_LEVELS: EducationLevel[] = ["secondary", "professional_bachelor", "bachelor", "master", "phd"];

export function EducationEditor({ value, onChange }: { value: Education[]; onChange: (v: Education[]) => void }) {
  const update = (i: number, patch: Partial<Education>) => onChange(value.map((e, j) => (j === i ? { ...e, ...patch } : e)));
  return (
    <div className="flex flex-col gap-3">
      {value.map((edu, i) => (
        <ItemShell key={edu.id ?? i} title={edu.degree || "Nieuwe opleiding"} onRemove={() => onChange(value.filter((_, j) => j !== i))}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Diploma"><Input value={edu.degree} onChange={(e) => update(i, { degree: e.target.value })} /></Field>
            <Field label="Onderwijsinstelling"><Input value={edu.institution} onChange={(e) => update(i, { institution: e.target.value })} /></Field>
            <Field label="Niveau">
              <Select value={edu.level ?? ""} onChange={(e) => update(i, { level: (e.target.value || null) as EducationLevel | null })}>
                <option value="">Onbekend</option>
                {EDUCATION_LEVELS.map((l) => <option key={l} value={l}>{t(`enums.education.${l}`)}</option>)}
              </Select>
            </Field>
            <Field label="Richting"><Input value={edu.field ?? ""} onChange={(e) => update(i, { field: e.target.value || null })} /></Field>
            <Field label="Van" hint="JJJJ of JJJJ-MM"><Input value={edu.start ?? ""} onChange={(e) => update(i, { start: e.target.value || null })} /></Field>
            <Field label="Tot" hint="JJJJ of JJJJ-MM"><Input value={edu.end ?? ""} onChange={(e) => update(i, { end: e.target.value || null })} /></Field>
          </div>
        </ItemShell>
      ))}
      <Button type="button" variant="secondary" className="self-start" onClick={() => onChange([...value, { degree: "", institution: "" }])}><Plus />Opleiding toevoegen</Button>
    </div>
  );
}

const LANGS = ["nl", "fr", "en", "de", "tr", "es", "it", "ar"];
const LEVELS: LanguageSkill["level"][] = ["native", "fluent", "professional", "basic"];

export function LanguagesEditor({ value, onChange }: { value: LanguageSkill[]; onChange: (v: LanguageSkill[]) => void }) {
  return (
    <div className="flex flex-col gap-2">
      {value.map((lang, i) => (
        <div key={i} className="flex gap-2">
          <Select value={lang.code} aria-label="Taal" onChange={(e) => onChange(value.map((l, j) => (j === i ? { ...l, code: e.target.value } : l)))}>
            {LANGS.map((c) => <option key={c} value={c}>{t(`enums.languages.${c}`)}</option>)}
          </Select>
          <Select value={lang.level} aria-label="Niveau" onChange={(e) => onChange(value.map((l, j) => (j === i ? { ...l, level: e.target.value as LanguageSkill["level"] } : l)))}>
            {LEVELS.map((l) => <option key={l} value={l}>{t(`enums.languageLevel.${l}`)}</option>)}
          </Select>
          <Button type="button" size="icon" variant="ghost" onClick={() => onChange(value.filter((_, j) => j !== i))} aria-label="Taal verwijderen"><Trash2 /></Button>
        </div>
      ))}
      <Button type="button" size="sm" variant="ghost" className="self-start"
        onClick={() => onChange([...value, { code: LANGS.find((c) => !value.some((l) => l.code === c)) ?? "nl", level: "professional" }])}>
        <Plus />Taal toevoegen
      </Button>
    </div>
  );
}

export function ProjectsEditor({ value, onChange }: { value: Project[]; onChange: (v: Project[]) => void }) {
  const update = (i: number, patch: Partial<Project>) => onChange(value.map((p, j) => (j === i ? { ...p, ...patch } : p)));
  return (
    <div className="flex flex-col gap-3">
      {value.map((p, i) => (
        <ItemShell key={p.id ?? i} title={p.name || "Nieuw project"} onRemove={() => onChange(value.filter((_, j) => j !== i))}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Naam"><Input value={p.name} onChange={(e) => update(i, { name: e.target.value })} /></Field>
            <Field label="Link"><Input value={p.url ?? ""} onChange={(e) => update(i, { url: e.target.value || null })} /></Field>
            <Field label="Beschrijving" className="sm:col-span-2"><Textarea rows={2} value={p.description ?? ""} onChange={(e) => update(i, { description: e.target.value || null })} /></Field>
            <Field label="Technologieën" className="sm:col-span-2"><TagInput value={p.technologies} onChange={(technologies) => update(i, { technologies })} /></Field>
          </div>
        </ItemShell>
      ))}
      <Button type="button" variant="secondary" className="self-start" onClick={() => onChange([...value, { name: "", technologies: [] }])}><Plus />Project toevoegen</Button>
    </div>
  );
}

export function CertificationsEditor({ value, onChange }: { value: Certification[]; onChange: (v: Certification[]) => void }) {
  const update = (i: number, patch: Partial<Certification>) => onChange(value.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  return (
    <div className="flex flex-col gap-2">
      {value.map((c, i) => (
        <div key={c.id ?? i} className="grid grid-cols-[1fr_1fr_6rem_auto] gap-2">
          <Input placeholder="Naam" aria-label="Naam" value={c.name} onChange={(e) => update(i, { name: e.target.value })} />
          <Input placeholder="Uitgever" aria-label="Uitgever" value={c.issuer ?? ""} onChange={(e) => update(i, { issuer: e.target.value || null })} />
          <Input placeholder="Jaar" aria-label="Jaar" inputMode="numeric" value={c.year ?? ""} onChange={(e) => update(i, { year: e.target.value ? Number(e.target.value) || null : null })} />
          <Button type="button" size="icon" variant="ghost" onClick={() => onChange(value.filter((_, j) => j !== i))} aria-label="Certificaat verwijderen"><Trash2 /></Button>
        </div>
      ))}
      <Button type="button" size="sm" variant="ghost" className="self-start" onClick={() => onChange([...value, { name: "" }])}><Plus />Certificaat toevoegen</Button>
    </div>
  );
}

/** Full editor for the structured profile. */
export function ProfileContentEditor({ value, onChange }: { value: ProfileContent; onChange: (v: ProfileContent) => void }) {
  const set = <K extends keyof ProfileContent>(key: K) => (v: ProfileContent[K]) => onChange({ ...value, [key]: v });
  return (
    <div className="flex flex-col gap-5">
      <Card><CardHeader title="Werkervaring" description="Meest recent eerst. Eén taak of resultaat per punt." /><CardBody><ExperienceEditor value={value.experiences} onChange={set("experiences")} /></CardBody></Card>
      <Card><CardHeader title="Vaardigheden" description="Tools, technologieën en competenties. Druk op Enter na elke vaardigheid." /><CardBody><TagInput value={value.skills} onChange={set("skills")} placeholder="bv. Python, Excel, klantencontact" /></CardBody></Card>
      <Card><CardHeader title="Opleiding" /><CardBody><EducationEditor value={value.education} onChange={set("education")} /></CardBody></Card>
      <Card><CardHeader title="Talen" /><CardBody><LanguagesEditor value={value.languages} onChange={set("languages")} /></CardBody></Card>
      <Card><CardHeader title="Projecten" description="Optioneel" /><CardBody><ProjectsEditor value={value.projects} onChange={set("projects")} /></CardBody></Card>
      <Card><CardHeader title="Certificaten" description="Optioneel" /><CardBody><CertificationsEditor value={value.certifications} onChange={set("certifications")} /></CardBody></Card>
    </div>
  );
}

/** Removes empty rows before saving. */
export function cleanProfile(p: ProfileContent): ProfileContent {
  return {
    ...p,
    experiences: p.experiences.map((e) => ({ ...e, bullets: e.bullets.map((b) => b.trim()).filter(Boolean), start: e.start || null, end: e.is_current ? null : e.end || null })),
    projects: p.projects.filter((x) => x.name.trim()),
    certifications: p.certifications.filter((x) => x.name.trim()),
  };
}
