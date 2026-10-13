"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, Download, Laptop, ShieldAlert, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Alert, Badge, EmptyState, Skeleton } from "@/components/ui/feedback";
import { Checkbox, Field, Input } from "@/components/ui/input";
import { useMe, usePublicConfig } from "@/hooks/use-auth";
import { api, downloadBlob, errorMessage } from "@/lib/api";
import { formatDateTime, relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Notification, Session, User } from "@/types/api";
import { useDraft } from "@/hooks/use-draft";

export function NotificationsPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const list = useQuery({ queryKey: ["notifications"], queryFn: () => api.get<Notification[]>("/notifications") });
  const read = useMutation({
    mutationFn: (id?: string) => api.post(`/notifications/read${id ? `?notification_id=${id}` : ""}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["notifications"] }); qc.invalidateQueries({ queryKey: ["unread"] }); },
  });
  const unread = list.data?.some((n) => !n.read_at);
  return (
    <>
      <PageHeader title="Meldingen" actions={unread && <Button variant="secondary" onClick={() => read.mutate(undefined)} loading={read.isPending && !read.variables}><CheckCheck />Alles als gelezen markeren</Button>} />
      {list.error ? <QueryError error={list.error} /> : !list.data ? <Skeleton className="h-40" /> : list.data.length === 0 ? <EmptyState icon={Bell} title="Geen meldingen" description="Je krijgt hier een melding als een cv klaar is of een sollicitatie verandert." /> : (
        <Card>
          <ul className="divide-y divide-border">
            {list.data.map((n) => (
              <li key={n.id}>
                <button className={cn("flex w-full items-start gap-3 px-5 py-4 text-left hover:bg-surface-2/60", !n.read_at && "bg-accent-soft/30")}
                  onClick={() => { if (!n.read_at) read.mutate(n.id); if (n.link) router.push(n.link); }}>
                  <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", n.read_at ? "bg-transparent" : "bg-accent")} aria-label={n.read_at ? undefined : "Ongelezen"} />
                  <span className="min-w-0 flex-1"><span className="block font-medium text-text">{n.title}</span>{n.body && <span className="block text-sm text-muted">{n.body}</span>}</span>
                  <span className="shrink-0 text-xs text-muted">{relativeTime(n.created_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}

export function SettingsPage() {
  const qc = useQueryClient();
  const me = useMe();
  const [draftName, setName] = useDraft(me.data ?? undefined, me.data?.full_name, (u) => u.full_name);
  const name = draftName ?? "";
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: () => api.get<Session[]>("/auth/sessions") });
  const saveName = useMutation({ mutationFn: () => api.patch<User>("/account", { full_name: name }), onSuccess: (u) => { qc.setQueryData(["me"], u); toast.success("Opgeslagen"); }, onError: (e) => toast.error(errorMessage(e)) });
  const revoke = useMutation({ mutationFn: (id: string) => api.delete(`/auth/sessions/${id}`), onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions"] }), onError: (e) => toast.error(errorMessage(e)) });
  const [pw, setPw] = React.useState({ current: "", next: "" });
  const changePw = useMutation({
    mutationFn: () => api.post<{ message: string }>("/auth/change-password", { current_password: pw.current, new_password: pw.next }),
    onSuccess: (r) => { toast.success(r.message); setPw({ current: "", next: "" }); qc.invalidateQueries({ queryKey: ["sessions"] }); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <>
      <PageHeader title="Instellingen" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Account" />
          <CardBody className="flex flex-col gap-4">
            <Field label="Naam"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
            <Field label="E-mailadres" hint={me.data?.email_verified ? "Bevestigd" : "Nog niet bevestigd"}><Input value={me.data?.email ?? ""} disabled /></Field>
            <Button className="self-start" disabled={!name.trim() || name === me.data?.full_name} loading={saveName.isPending} onClick={() => saveName.mutate()}>Opslaan</Button>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Wachtwoord wijzigen" description="Andere apparaten worden daarna uitgelogd." />
          <CardBody>
            <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); changePw.mutate(); }}>
              <Field label="Huidig wachtwoord"><Input type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} /></Field>
              <Field label="Nieuw wachtwoord" hint="Minstens 10 tekens."><Input type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} /></Field>
              <Button type="submit" className="self-start" disabled={!pw.current || pw.next.length < 10} loading={changePw.isPending}>Wachtwoord wijzigen</Button>
            </form>
          </CardBody>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader title="Actieve sessies" description="Apparaten waarop je bent ingelogd." />
          <CardBody>
            {!sessions.data ? <Skeleton className="h-16" /> : (
              <ul className="divide-y divide-border">
                {sessions.data.map((s) => (
                  <li key={s.id} className="flex items-center gap-3 py-3 text-sm">
                    <Laptop className="size-4 text-muted" />
                    <div className="min-w-0 flex-1"><p className="truncate text-text">{s.user_agent ?? "Onbekend apparaat"}</p><p className="text-xs text-muted">Laatst actief {relativeTime(s.last_seen_at)} · sinds {formatDateTime(s.created_at)}</p></div>
                    {s.current ? <Badge tone="accent">Dit apparaat</Badge> : <Button size="sm" variant="ghost" loading={revoke.isPending && revoke.variables === s.id} onClick={() => revoke.mutate(s.id)}>Uitloggen</Button>}
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </>
  );
}

export function PrivacyDataPage() {
  const qc = useQueryClient();
  const me = useMe();
  const config = usePublicConfig();
  const [exporting, setExporting] = React.useState(false);
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [password, setPassword] = React.useState("");
  const [understood, setUnderstood] = React.useState(false);
  const consent = useMutation({
    mutationFn: (value: boolean) => api.patch<User>("/account", { ai_processing_consent: value }),
    onSuccess: (u) => qc.setQueryData(["me"], u),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const remove = useMutation({
    mutationFn: () => api.post("/account/delete", { password }),
    onSuccess: () => { qc.clear(); window.location.assign(new URL("/", window.location.origin).toString()); },
  });
  async function exportData() {
    setExporting(true);
    try {
      const response = await fetch("/api/v1/account/export", { credentials: "same-origin" });
      if (!response.ok) throw new Error("Exporteren mislukt.");
      downloadBlob(await response.blob(), "talentflow-gegevens.json");
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setExporting(false);
    }
  }
  return (
    <>
      <PageHeader title="Privacy en gegevens" description={<>Wat we bewaren en wat je ermee kunt doen. Lees ook de <Link href="/privacy" className="text-accent underline">privacyverklaring</Link>.</>} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="AI-verwerking" />
          <CardBody className="flex flex-col gap-3 text-sm text-text-2">
            <p>{config.data?.ai_is_local ? "Het AI-model draait lokaal op de server van het platform. Je cv wordt niet naar een externe AI-dienst gestuurd." : config.data?.ai_configured ? `Het platform gebruikt een externe AI-dienst (${config.data.ai_provider}). Je cv-inhoud wordt daarheen gestuurd wanneer je een AI-functie gebruikt.` : "Er is momenteel geen AI-model ingesteld."}</p>
            <Checkbox checked={!!me.data?.ai_processing_consent} disabled={consent.isPending} onChange={(e) => consent.mutate(e.target.checked)}
              label="Ik ga akkoord dat mijn cv en profiel door het AI-model verwerkt worden voor analyse, optimalisatie en de assistent." />
            <p className="text-xs text-muted">AI-functies voer je altijd zelf uit; zonder actie gebeurt er niets met je cv.</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Je gegevens downloaden" />
          <CardBody className="flex flex-col gap-3 text-sm text-text-2">
            <p>Download alles wat we over je bewaren als JSON-bestand: account, profiel, cv&apos;s, sollicitaties, meldingen en gesprekken.</p>
            <Button className="self-start" variant="secondary" loading={exporting} onClick={exportData}><Download />Gegevens downloaden</Button>
          </CardBody>
        </Card>
        <Card className="border-danger/30 lg:col-span-2">
          <CardHeader title="Account verwijderen" />
          <CardBody className="flex flex-col gap-3 text-sm text-text-2">
            <p>Je account, profiel, cv-bestanden, cv-versies, sollicitaties en meldingen worden definitief verwijderd. Dit kan niet ongedaan gemaakt worden.</p>
            <Button className="self-start" variant="danger" onClick={() => setDeleteOpen(true)}><Trash2 />Account verwijderen</Button>
          </CardBody>
        </Card>
      </div>
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen} title="Account definitief verwijderen" description="Bevestig met je wachtwoord."
        footer={<><Button variant="secondary" onClick={() => setDeleteOpen(false)}>Annuleren</Button><Button variant="danger" disabled={!password || !understood} loading={remove.isPending} onClick={() => remove.mutate()}><ShieldAlert />Definitief verwijderen</Button></>}>
        <div className="flex flex-col gap-4">
          {remove.error && <Alert tone="danger">{errorMessage(remove.error)}</Alert>}
          <Field label="Wachtwoord"><Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
          <Checkbox checked={understood} onChange={(e) => setUnderstood(e.target.checked)} label="Ik begrijp dat al mijn gegevens definitief verwijderd worden." />
        </div>
      </Dialog>
    </>
  );
}
