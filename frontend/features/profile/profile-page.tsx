"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { PageSkeleton } from "@/components/page-suspense";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Alert } from "@/components/ui/feedback";
import { Field, Input, Textarea } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, errorMessage } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import type { CandidateProfile, ProfileContent } from "@/types/api";

import { PreferencesForm } from "./preferences-form";
import { cleanProfile, ProfileContentEditor, profileProblems } from "./profile-editor";
import { useDraft } from "@/hooks/use-draft";

type Basics = Pick<CandidateProfile, "headline" | "summary" | "phone" | "city" | "linkedin_url" | "website_url">;

export function ProfilePage() {
  const qc = useQueryClient();
  const profile = useQuery({ queryKey: ["profile"], queryFn: () => api.get<CandidateProfile>("/candidates/me") });
  const [draft, setDraft] = useDraft(profile.data, profile.data?.updated_at, (p: CandidateProfile) => ({
    basics: { headline: p.headline, summary: p.summary, phone: p.phone, city: p.city, linkedin_url: p.linkedin_url, website_url: p.website_url } as Basics,
    content: p.content,
  }));
  const basics = draft?.basics ?? null;
  const content = draft?.content ?? null;
  const setBasics = (b: Basics) => setDraft((d) => ({ ...d, basics: b }));
  const setContent = (c: ProfileContent) => setDraft((d) => ({ ...d, content: c }));
  const [problems, setProblems] = React.useState<string[]>([]);

  const save = useMutation({
    mutationFn: () => api.patch<CandidateProfile>("/candidates/me", { ...basics, content: cleanProfile(content!) }),
    onSuccess: (data) => {
      qc.setQueryData(["profile"], data);
      ["jobs", "dashboard", "match"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      toast.success("Profiel opgeslagen. Je matches worden herberekend.");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (profile.error) return <QueryError error={profile.error} onRetry={() => profile.refetch()} />;
  if (!basics || !content || !profile.data) return <PageSkeleton />;
  const dirty = JSON.stringify(content) !== JSON.stringify(profile.data.content) || Object.entries(basics).some(([k, v]) => v !== profile.data[k as keyof Basics]);
  const set = (k: keyof Basics) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setBasics({ ...basics, [k]: e.target.value || null });

  return (
    <>
      <PageHeader title="Mijn profiel" description={`Je profiel is de bron voor je matches en voor elk cv dat we afstemmen. Laatst bijgewerkt ${relativeTime(profile.data.updated_at)}.`}
        actions={<Button disabled={!dirty} loading={save.isPending} onClick={() => { const p = profileProblems(content); setProblems(p); if (!p.length) save.mutate(); }}><Save />{dirty ? "Wijzigingen opslaan" : "Opgeslagen"}</Button>} />
      <Tabs defaultValue="profile">
        <TabsList className="mb-5"><TabsTrigger value="profile">Profiel</TabsTrigger><TabsTrigger value="preferences">Voorkeuren</TabsTrigger></TabsList>
        <TabsContent value="profile" className="flex flex-col gap-5">
          {problems.length > 0 && <Alert tone="danger"><ul className="list-disc pl-4">{problems.map((p) => <li key={p}>{p}</li>)}</ul></Alert>}
          <Card>
            <CardHeader title="Over jou" />
            <CardBody className="grid gap-4 sm:grid-cols-2">
              <Field label="Naam" hint="Wijzig je naam via Instellingen."><Input value={profile.data.full_name} disabled /></Field>
              <Field label="E-mail"><Input value={profile.data.email} disabled /></Field>
              <Field label="Titel / headline"><Input value={basics.headline ?? ""} onChange={set("headline")} /></Field>
              <Field label="Woonplaats"><Input value={basics.city ?? ""} onChange={set("city")} /></Field>
              <Field label="Telefoon"><Input value={basics.phone ?? ""} onChange={set("phone")} /></Field>
              <Field label="LinkedIn"><Input value={basics.linkedin_url ?? ""} onChange={set("linkedin_url")} /></Field>
              <Field label="Website"><Input value={basics.website_url ?? ""} onChange={set("website_url")} /></Field>
              <Field label="Samenvatting" className="sm:col-span-2"><Textarea rows={4} value={basics.summary ?? ""} onChange={set("summary")} /></Field>
            </CardBody>
          </Card>
          <ProfileContentEditor value={content} onChange={setContent} />
        </TabsContent>
        <TabsContent value="preferences"><Card><CardBody><PreferencesForm /></CardBody></Card></TabsContent>
      </Tabs>
    </>
  );
}
