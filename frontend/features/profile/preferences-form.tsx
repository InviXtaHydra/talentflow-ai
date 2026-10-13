"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Alert, Skeleton } from "@/components/ui/feedback";
import { Checkbox, Field, Input, Select } from "@/components/ui/input";
import { TagInput } from "@/components/ui/tag-input";
import { api, errorMessage } from "@/lib/api";
import { t } from "@/lib/i18n";
import type { EmploymentType, Preferences, RemotePreference, SalaryPeriod } from "@/types/api";
import { useDraft } from "@/hooks/use-draft";

const EMPLOYMENT: EmploymentType[] = ["full_time", "part_time", "contract", "freelance", "internship", "temporary"];
const REMOTE: RemotePreference[] = ["any", "onsite", "hybrid", "remote"];
const CITIES = ["Antwerpen", "Brussel", "Gent", "Leuven", "Mechelen", "Hasselt", "Genk", "Brugge", "Kortrijk", "Liège", "Namur", "Charleroi", "Mons", "Wavre"];
const INDUSTRIES = ["IT & software", "Financiële diensten", "Logistiek", "Zorg", "Retail", "Energie", "Overheid", "Onderwijs", "Industrie", "Bouw"];

export function PreferencesForm({ onSaved, submitLabel = "Voorkeuren opslaan" }: { onSaved?: () => void; submitLabel?: string }) {
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["preferences"], queryFn: () => api.get<Preferences>("/candidates/me/preferences") });
  const [prefs, setPrefs] = useDraft(query.data, query.data?.updated_at ?? (query.data ? "loaded" : undefined), (p: Preferences) => p);

  const save = useMutation({
    mutationFn: (body: Preferences) => api.put<Preferences>("/candidates/me/preferences", body),
    onSuccess: (data) => {
      qc.setQueryData(["preferences"], data);
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Voorkeuren opgeslagen");
      onSaved?.();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (query.error) return <Alert tone="danger">{errorMessage(query.error)}</Alert>;
  if (!prefs) return <Skeleton className="h-64" />;
  const set = <K extends keyof Preferences>(key: K, value: Preferences[K]) => setPrefs({ ...prefs, [key]: value });

  return (
    <form className="flex flex-col gap-5" onSubmit={(e) => { e.preventDefault(); save.mutate(prefs); }}>
      <p className="text-sm text-muted">Alles is optioneel. Je voorkeuren tellen voor 10% mee in de matchscore en worden apart getoond.</p>
      <Field label="Gewenste functies" hint="bv. Data Engineer, Boekhouder">
        <TagInput value={prefs.desired_titles} onChange={(v) => set("desired_titles", v)} max={10} />
      </Field>
      <div className="grid gap-5 sm:grid-cols-[1fr_12rem]">
        <Field label="Voorkeurslocaties"><TagInput value={prefs.preferred_locations} onChange={(v) => set("preferred_locations", v)} suggestions={CITIES} max={10} /></Field>
        <Field label="Max. pendelafstand (km)">
          <Input type="number" min={0} max={500} value={prefs.max_commute_km ?? ""} onChange={(e) => set("max_commute_km", e.target.value ? Number(e.target.value) : null)} />
        </Field>
      </div>
      <Field label="Thuiswerk">
        <Select value={prefs.remote_preference} onChange={(e) => set("remote_preference", e.target.value as RemotePreference)}>
          {REMOTE.map((r) => <option key={r} value={r}>{t(`enums.remote.${r}`)}</option>)}
        </Select>
      </Field>
      <fieldset>
        <legend className="mb-2 text-sm font-medium text-text-2">Contracttype</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {EMPLOYMENT.map((type) => (
            <Checkbox key={type} label={t(`enums.employmentType.${type}`)} checked={prefs.employment_types.includes(type)}
              onChange={(e) => set("employment_types", e.target.checked ? [...prefs.employment_types, type] : prefs.employment_types.filter((x) => x !== type))} />
          ))}
        </div>
      </fieldset>
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Minimumloon (bruto)" hint="Leeg laten als je dit niet wilt delen.">
          <Input type="number" min={0} value={prefs.salary_min ?? ""} onChange={(e) => set("salary_min", e.target.value ? Number(e.target.value) : null)} />
        </Field>
        <Field label="Per">
          <Select value={prefs.salary_period} onChange={(e) => set("salary_period", e.target.value as SalaryPeriod)}>
            {(["month", "year", "hour"] as SalaryPeriod[]).map((p) => <option key={p} value={p}>{t(`enums.salaryPeriod.${p}`).replace("per ", "")}</option>)}
          </Select>
        </Field>
      </div>
      <Field label="Sectoren"><TagInput value={prefs.industries} onChange={(v) => set("industries", v)} suggestions={INDUSTRIES} max={10} /></Field>
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Beschikbaar vanaf"><Input type="date" value={prefs.available_from ?? ""} onChange={(e) => set("available_from", e.target.value || null)} /></Field>
        <Field label="Opmerking over beschikbaarheid"><Input value={prefs.availability_note ?? ""} maxLength={200} onChange={(e) => set("availability_note", e.target.value || null)} /></Field>
      </div>
      <div><Button type="submit" loading={save.isPending}>{submitLabel}</Button></div>
    </form>
  );
}
