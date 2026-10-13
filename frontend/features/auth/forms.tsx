"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Building2, CheckCircle2, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Alert, Spinner } from "@/components/ui/feedback";
import { Checkbox, Field, Input } from "@/components/ui/input";
import { homeFor } from "@/hooks/use-auth";
import { api, ApiError, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { User } from "@/types/api";

function AuthCard({ title, description, children, footer }: { title: string; description?: React.ReactNode; children: React.ReactNode; footer?: React.ReactNode }) {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col px-4 py-12 sm:py-16">
      <Card className="p-6 sm:p-8">
        <h1 className="text-2xl font-semibold tracking-tight text-text">{title}</h1>
        {description && <p className="mt-1.5 text-sm text-muted">{description}</p>}
        <div className="mt-6">{children}</div>
      </Card>
      {footer && <p className="mt-6 text-center text-sm text-muted">{footer}</p>}
    </div>
  );
}

/** Only same-site relative paths are followed after login (no open redirects). */
function safeNext(next: string | null): string | null {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : null;
}

const password = z.string().min(10, "Minstens 10 tekens.").max(128);

// ── login ────────────────────────────────────────────────────────────────────

const loginSchema = z.object({ email: z.email("Vul een geldig e-mailadres in."), password: z.string().min(1, "Vul je wachtwoord in.") });

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const [error, setError] = React.useState<string | null>(null);
  const form = useForm<z.infer<typeof loginSchema>>({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      const user = await api.post<User>("/auth/login", values);
      qc.setQueryData(["me"], user);
      router.replace(safeNext(params.get("next")) ?? homeFor(user));
    } catch (e) {
      setError(errorMessage(e));
    }
  });

  return (
    <AuthCard title="Welkom terug" description="Log in om verder te gaan." footer={<>Nog geen account? <Link className="font-medium text-accent hover:underline" href="/register">Maak er gratis een aan</Link></>}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}
        <Field label="E-mailadres" htmlFor="email" error={form.formState.errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!form.formState.errors.email} {...form.register("email")} />
        </Field>
        <Field label="Wachtwoord" htmlFor="password" error={form.formState.errors.password?.message}>
          <Input id="password" type="password" autoComplete="current-password" aria-invalid={!!form.formState.errors.password} {...form.register("password")} />
        </Field>
        <div className="-mt-1 text-right"><Link href="/forgot-password" className="text-sm text-accent hover:underline">Wachtwoord vergeten?</Link></div>
        <Button type="submit" loading={form.formState.isSubmitting}>Inloggen</Button>
      </form>
    </AuthCard>
  );
}

// ── register ─────────────────────────────────────────────────────────────────

const registerSchema = z
  .object({
    account_type: z.enum(["candidate", "employer"]),
    full_name: z.string().trim().min(2, "Vul je naam in."),
    email: z.email("Vul een geldig e-mailadres in."),
    password,
    company_name: z.string().trim().optional(),
    accept_terms: z.boolean().refine((v) => v, "Je moet de voorwaarden aanvaarden."),
  })
  .refine((v) => v.account_type === "candidate" || (v.company_name ?? "").length >= 2, { path: ["company_name"], message: "Vul de naam van je bedrijf in." });

export function RegisterForm() {
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const [error, setError] = React.useState<string | null>(null);
  const form = useForm<z.infer<typeof registerSchema>>({
    resolver: zodResolver(registerSchema),
    defaultValues: { account_type: params.get("type") === "employer" ? "employer" : "candidate", full_name: "", email: "", password: "", company_name: "", accept_terms: false },
  });
  const type = useWatch({ control: form.control, name: "account_type" });

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      const user = await api.post<User>("/auth/register", { ...values, company_name: values.account_type === "employer" ? values.company_name : null });
      qc.setQueryData(["me"], user);
      router.replace(user.role === "employer" ? "/employer" : "/onboarding");
    } catch (e) {
      if (e instanceof ApiError && e.code === "email_taken") form.setError("email", { message: e.message });
      else setError(errorMessage(e));
    }
  });

  const options = [
    { value: "candidate", icon: UserRound, title: "Ik zoek werk", text: "Vacatures, matches en cv's" },
    { value: "employer", icon: Building2, title: "Ik werf aan", text: "Vacatures en kandidaten" },
  ] as const;

  return (
    <AuthCard title="Account aanmaken" description="Gratis, en je kunt je gegevens altijd exporteren of verwijderen."
      footer={<>Al een account? <Link className="font-medium text-accent hover:underline" href="/login">Inloggen</Link></>}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium text-text-2">Ik ben</legend>
          <div className="grid grid-cols-2 gap-2">
            {options.map(({ value, icon: Icon, title, text }) => (
              <label key={value} className={cn("cursor-pointer rounded-lg border p-3 transition-colors", type === value ? "border-accent bg-accent-soft" : "border-border hover:bg-surface-2")}>
                <input type="radio" value={value} className="sr-only" {...form.register("account_type")} />
                <Icon className={cn("mb-1.5 size-5", type === value ? "text-accent" : "text-muted")} />
                <span className="block text-sm font-medium text-text">{title}</span>
                <span className="block text-xs text-muted">{text}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <Field label="Volledige naam" htmlFor="full_name" error={form.formState.errors.full_name?.message}>
          <Input id="full_name" autoComplete="name" aria-invalid={!!form.formState.errors.full_name} {...form.register("full_name")} />
        </Field>
        {type === "employer" && (
          <Field label="Bedrijfsnaam" htmlFor="company_name" error={form.formState.errors.company_name?.message}>
            <Input id="company_name" autoComplete="organization" {...form.register("company_name")} />
          </Field>
        )}
        <Field label="E-mailadres" htmlFor="email" error={form.formState.errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!form.formState.errors.email} {...form.register("email")} />
        </Field>
        <Field label="Wachtwoord" htmlFor="password" error={form.formState.errors.password?.message} hint="Minstens 10 tekens.">
          <Input id="password" type="password" autoComplete="new-password" aria-invalid={!!form.formState.errors.password} {...form.register("password")} />
        </Field>
        <div>
          <Checkbox {...form.register("accept_terms")} label={<>Ik aanvaard de <Link href="/terms" className="text-accent underline" target="_blank">voorwaarden</Link> en de <Link href="/privacy" className="text-accent underline" target="_blank">privacyverklaring</Link>.</>} />
          {form.formState.errors.accept_terms && <p className="mt-1 text-xs text-danger">{form.formState.errors.accept_terms.message}</p>}
        </div>
        <Button type="submit" loading={form.formState.isSubmitting}>Account aanmaken</Button>
      </form>
    </AuthCard>
  );
}

// ── password reset ───────────────────────────────────────────────────────────

export function ForgotPasswordForm() {
  const [sent, setSent] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const form = useForm<{ email: string }>({ resolver: zodResolver(z.object({ email: z.email("Vul een geldig e-mailadres in.") })), defaultValues: { email: "" } });
  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      setSent((await api.post<{ message: string }>("/auth/forgot-password", values)).message);
    } catch (e) {
      setError(errorMessage(e));
    }
  });
  return (
    <AuthCard title="Wachtwoord vergeten" description="We sturen je een link om een nieuw wachtwoord in te stellen." footer={<Link className="text-accent hover:underline" href="/login">Terug naar inloggen</Link>}>
      {sent ? <Alert tone="success">{sent}</Alert> : (
        <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
          {error && <Alert tone="danger">{error}</Alert>}
          <Field label="E-mailadres" htmlFor="email" error={form.formState.errors.email?.message}>
            <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
          </Field>
          <Button type="submit" loading={form.formState.isSubmitting}>Link versturen</Button>
        </form>
      )}
    </AuthCard>
  );
}

const resetSchema = z.object({ password, confirm: z.string() }).refine((v) => v.password === v.confirm, { path: ["confirm"], message: "De wachtwoorden zijn niet gelijk." });

export function ResetPasswordForm() {
  const params = useSearchParams();
  const token = params.get("token");
  const [done, setDone] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const form = useForm<z.infer<typeof resetSchema>>({ resolver: zodResolver(resetSchema), defaultValues: { password: "", confirm: "" } });
  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      await api.post("/auth/reset-password", { token, password: values.password });
      setDone(true);
    } catch (e) {
      setError(errorMessage(e));
    }
  });
  if (!token) return <AuthCard title="Ongeldige link"><Alert tone="danger">Deze link is onvolledig. Vraag een nieuwe aan via <Link href="/forgot-password" className="underline">wachtwoord vergeten</Link>.</Alert></AuthCard>;
  return (
    <AuthCard title="Nieuw wachtwoord instellen">
      {done ? (
        <div className="flex flex-col gap-4">
          <Alert tone="success">Je wachtwoord is gewijzigd. Op andere apparaten ben je uitgelogd.</Alert>
          <Button asChild><Link href="/login">Inloggen</Link></Button>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
          {error && <Alert tone="danger">{error}</Alert>}
          <Field label="Nieuw wachtwoord" htmlFor="password" error={form.formState.errors.password?.message}>
            <Input id="password" type="password" autoComplete="new-password" {...form.register("password")} />
          </Field>
          <Field label="Herhaal het wachtwoord" htmlFor="confirm" error={form.formState.errors.confirm?.message}>
            <Input id="confirm" type="password" autoComplete="new-password" {...form.register("confirm")} />
          </Field>
          <Button type="submit" loading={form.formState.isSubmitting}>Wachtwoord opslaan</Button>
        </form>
      )}
    </AuthCard>
  );
}

export function VerifyEmail() {
  const params = useSearchParams();
  const token = params.get("token");
  const qc = useQueryClient();
  const [result, setState] = React.useState<{ status: "loading" | "ok" | "error"; message?: string }>({ status: "loading" });
  const state = token ? result : { status: "error" as const, message: "Deze link is onvolledig." };
  const started = React.useRef(false);
  React.useEffect(() => {
    if (started.current || !token) return;
    started.current = true;
    api.post<User>("/auth/verify-email", { token })
      .then((user) => { qc.setQueryData(["me"], (old: User | null | undefined) => (old ? user : old)); setState({ status: "ok" }); })
      .catch((e) => setState({ status: "error", message: errorMessage(e) }));
  }, [token, qc]);
  return (
    <AuthCard title="E-mailadres bevestigen">
      {state.status === "loading" && <Spinner label="Bezig met bevestigen…" />}
      {state.status === "ok" && (
        <div className="flex flex-col gap-4">
          <p className="flex items-center gap-2 text-success"><CheckCircle2 className="size-5" /> Je e-mailadres is bevestigd.</p>
          <Button asChild><Link href="/dashboard">Verder</Link></Button>
        </div>
      )}
      {state.status === "error" && <Alert tone="danger">{state.message}</Alert>}
    </AuthCard>
  );
}
