"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Alert } from "@/components/ui/feedback";
import { Field, Input, Textarea } from "@/components/ui/input";
import { cleanProfile, emptyProfile, ProfileContentEditor, profileProblems } from "@/features/profile/profile-editor";
import { api, errorMessage } from "@/lib/api";
import type { ContactDetails, CvDocumentDetail, ProfileContent } from "@/types/api";

/** Shows what was recognized in the CV as editable fields. Nothing is saved to the profile until confirmed. */
export function ExtractionReview({ doc, onConfirmed }: { doc: CvDocumentDetail; onConfirmed: () => void }) {
  const qc = useQueryClient();
  const extracted = doc.extracted;
  const [contact, setContact] = React.useState<ContactDetails>(extracted?.contact ?? {});
  const [headline, setHeadline] = React.useState(extracted?.headline ?? "");
  const [summary, setSummary] = React.useState(extracted?.summary ?? "");
  const [profile, setProfile] = React.useState<ProfileContent>(extracted?.profile ?? emptyProfile);
  const [problems, setProblems] = React.useState<string[]>([]);

  const confirm = useMutation({
    mutationFn: () => api.post(`/cvs/${doc.id}/confirm`, { contact, headline: headline || null, summary: summary || null, profile: cleanProfile(profile) }),
    onSuccess: () => {
      ["profile", "cvs", "cv-versions", "dashboard", "jobs", "me"].forEach((key) => qc.invalidateQueries({ queryKey: [key] }));
      toast.success("Je profiel is bijgewerkt");
      onConfirmed();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const submit = () => {
    const found = profileProblems(profile);
    setProblems(found);
    if (!found.length) confirm.mutate();
  };

  const setC = (key: keyof ContactDetails) => (e: React.ChangeEvent<HTMLInputElement>) => setContact({ ...contact, [key]: e.target.value || null });

  return (
    <div className="flex flex-col gap-5">
      {doc.extraction_method === "rule_based" && (
        <Alert tone="warning" title="Basisextractie zonder AI">
          {doc.extraction_error ?? "Er is geen AI-model ingesteld."} We herkenden alleen contactgegevens, vaardigheden en talen. Vul je werkervaring en opleiding hieronder zelf aan.
        </Alert>
      )}
      {doc.extraction_method === "ai" && (
        <Alert tone="accent" title="Controleer wat we herkenden">Automatische herkenning maakt soms fouten. Pas aan wat niet klopt; pas na bevestiging wordt je profiel bijgewerkt.</Alert>
      )}
      <Card>
        <CardHeader title="Contactgegevens en samenvatting" />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Naam"><Input value={contact.full_name ?? ""} onChange={setC("full_name")} /></Field>
          <Field label="Woonplaats"><Input value={contact.city ?? ""} onChange={setC("city")} /></Field>
          <Field label="Telefoon"><Input value={contact.phone ?? ""} onChange={setC("phone")} /></Field>
          <Field label="LinkedIn"><Input value={contact.linkedin_url ?? ""} onChange={setC("linkedin_url")} /></Field>
          <Field label="Titel / headline" className="sm:col-span-2"><Input value={headline} onChange={(e) => setHeadline(e.target.value)} /></Field>
          <Field label="Samenvatting" className="sm:col-span-2"><Textarea rows={4} value={summary} onChange={(e) => setSummary(e.target.value)} /></Field>
        </CardBody>
      </Card>
      <ProfileContentEditor value={profile} onChange={setProfile} />
      {problems.length > 0 && <Alert tone="danger" title="Nog niet alles is in orde"><ul className="list-disc pl-4">{problems.map((p) => <li key={p}>{p}</li>)}</ul></Alert>}
      <div className="sticky bottom-0 -mx-1 flex justify-end gap-2 border-t border-border bg-bg/90 px-1 py-3 backdrop-blur">
        <Button onClick={submit} loading={confirm.isPending} size="lg">Bevestigen en profiel opslaan</Button>
      </div>
    </div>
  );
}
