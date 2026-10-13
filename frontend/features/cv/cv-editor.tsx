"use client";

import { ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Checkbox, Field, Input, Textarea } from "@/components/ui/input";
import { TagInput } from "@/components/ui/tag-input";
import { CertificationsEditor, LanguagesEditor } from "@/features/profile/profile-editor";
import type { CvContent, CvExperience } from "@/types/api";

function move<T>(list: T[], i: number, d: number): T[] {
  const j = i + d;
  if (j < 0 || j >= list.length) return list;
  const next = [...list];
  [next[i], next[j]] = [next[j], next[i]];
  return next;
}

/** Structured editor for a CV version. Everything the export renders is editable here. */
export function CvContentEditor({ value, onChange, readOnly }: { value: CvContent; onChange: (v: CvContent) => void; readOnly?: boolean }) {
  const set = <K extends keyof CvContent>(key: K, v: CvContent[K]) => onChange({ ...value, [key]: v });
  const setExp = (i: number, patch: Partial<CvExperience>) => set("experiences", value.experiences.map((e, j) => (j === i ? { ...e, ...patch } : e)));
  return (
    <fieldset disabled={readOnly} className="flex min-w-0 flex-col gap-5">
      <Card>
        <CardHeader title="Kop en contact" description="Contactgegevens komen uit je profiel; pas ze hier enkel aan voor dit cv." />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Naam"><Input value={value.contact.full_name ?? ""} onChange={(e) => set("contact", { ...value.contact, full_name: e.target.value })} /></Field>
          <Field label="Titel"><Input value={value.headline ?? ""} onChange={(e) => set("headline", e.target.value || null)} /></Field>
          <Field label="E-mail"><Input value={value.contact.email ?? ""} onChange={(e) => set("contact", { ...value.contact, email: e.target.value || null })} /></Field>
          <Field label="Telefoon"><Input value={value.contact.phone ?? ""} onChange={(e) => set("contact", { ...value.contact, phone: e.target.value || null })} /></Field>
          <Field label="Woonplaats"><Input value={value.contact.city ?? ""} onChange={(e) => set("contact", { ...value.contact, city: e.target.value || null })} /></Field>
          <Field label="LinkedIn"><Input value={value.contact.linkedin_url ?? ""} onChange={(e) => set("contact", { ...value.contact, linkedin_url: e.target.value || null })} /></Field>
          <Field label="Samenvatting" className="sm:col-span-2"><Textarea rows={5} value={value.summary ?? ""} onChange={(e) => set("summary", e.target.value || null)} /></Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Werkervaring" />
        <CardBody className="flex flex-col gap-3">
          {value.experiences.map((exp, i) => (
            <div key={exp.source_id ?? i} className="rounded-lg border border-border bg-bg/50 p-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="truncate text-sm font-medium text-text">{exp.title} — {exp.employer}</p>
                {!readOnly && (
                  <div className="flex gap-1">
                    <Button type="button" size="icon" variant="ghost" aria-label="Omhoog" onClick={() => set("experiences", move(value.experiences, i, -1))}><ChevronUp /></Button>
                    <Button type="button" size="icon" variant="ghost" aria-label="Omlaag" onClick={() => set("experiences", move(value.experiences, i, 1))}><ChevronDown /></Button>
                    <Button type="button" size="icon" variant="ghost" aria-label="Functie verwijderen" onClick={() => set("experiences", value.experiences.filter((_, j) => j !== i))}><Trash2 className="text-danger" /></Button>
                  </div>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Functietitel"><Input value={exp.title} onChange={(e) => setExp(i, { title: e.target.value })} /></Field>
                <Field label="Werkgever"><Input value={exp.employer} onChange={(e) => setExp(i, { employer: e.target.value })} /></Field>
                <Field label="Van" hint="JJJJ-MM"><Input value={exp.start ?? ""} onChange={(e) => setExp(i, { start: e.target.value || null })} /></Field>
                <Field label="Tot" hint="JJJJ-MM"><Input value={exp.end ?? ""} disabled={exp.is_current} onChange={(e) => setExp(i, { end: e.target.value || null })} /></Field>
              </div>
              <Checkbox className="mt-2" checked={exp.is_current} onChange={(e) => setExp(i, { is_current: e.target.checked, end: e.target.checked ? null : exp.end })} label="Huidige functie" />
              <div className="mt-3 flex flex-col gap-2">
                {exp.bullets.map((b, k) => (
                  <div key={k} className="flex gap-2">
                    <Textarea rows={2} className="min-h-0" value={b.text} aria-label={`Punt ${k + 1}`}
                      onChange={(e) => setExp(i, { bullets: exp.bullets.map((x, m) => (m === k ? { ...x, text: e.target.value } : x)) })} />
                    {!readOnly && <Button type="button" size="icon" variant="ghost" aria-label="Punt verwijderen" onClick={() => setExp(i, { bullets: exp.bullets.filter((_, m) => m !== k) })}><Trash2 /></Button>}
                  </div>
                ))}
                {!readOnly && <Button type="button" size="sm" variant="ghost" className="self-start" onClick={() => setExp(i, { bullets: [...exp.bullets, { text: "", source_refs: [] }] })}><Plus />Punt toevoegen</Button>}
              </div>
            </div>
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Vaardigheden" description="De volgorde hier is de volgorde op je cv." />
        <CardBody><TagInput value={value.skills} onChange={(v) => set("skills", v)} /></CardBody>
      </Card>

      {value.projects.length > 0 && (
        <Card>
          <CardHeader title="Projecten" />
          <CardBody className="flex flex-col gap-3">
            {value.projects.map((p, i) => (
              <Field key={p.source_id ?? i} label={p.name}>
                <Textarea rows={2} value={p.description ?? ""} onChange={(e) => set("projects", value.projects.map((x, j) => (j === i ? { ...x, description: e.target.value || null } : x)))} />
              </Field>
            ))}
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader title="Opleiding" />
        <CardBody className="flex flex-col gap-3">
          {value.education.map((edu, i) => (
            <div key={edu.source_id ?? i} className="grid gap-3 sm:grid-cols-2">
              <Field label="Diploma"><Input value={edu.degree} onChange={(e) => set("education", value.education.map((x, j) => (j === i ? { ...x, degree: e.target.value } : x)))} /></Field>
              <Field label="Instelling"><Input value={edu.institution} onChange={(e) => set("education", value.education.map((x, j) => (j === i ? { ...x, institution: e.target.value } : x)))} /></Field>
            </div>
          ))}
          {value.education.length === 0 && <p className="text-sm text-muted">Geen opleiding in dit cv. Voeg ze toe in je profiel.</p>}
        </CardBody>
      </Card>

      <Card><CardHeader title="Talen" /><CardBody><LanguagesEditor value={value.languages} onChange={(v) => set("languages", v)} /></CardBody></Card>
      <Card><CardHeader title="Certificaten" /><CardBody><CertificationsEditor value={value.certifications} onChange={(v) => set("certifications", v)} /></CardBody></Card>
    </fieldset>
  );
}
