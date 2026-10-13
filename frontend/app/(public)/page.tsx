import { ArrowRight, Building2, CheckCircle2, FileCheck2, Lock, Scale, Search, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { brand } from "@/lib/config";

const steps = [
  { icon: FileCheck2, title: "Upload je cv", text: "We lezen je cv uit. Jij controleert en verbetert wat we herkenden, niets wordt zomaar overgenomen." },
  { icon: Search, title: "Zie wat echt past", text: "Elke vacature krijgt een uitlegbare matchscore: welke vaardigheden je hebt, wat ontbreekt en waarom." },
  { icon: Sparkles, title: "Een cv per vacature", text: "Met één klik een cv dat jouw echte ervaring zo relevant mogelijk presenteert. Als PDF of Word." },
];

const principles = [
  { icon: Scale, title: "Uitlegbare matching", text: "Scores komen uit een transparante berekening, niet uit een taalmodel dat een percentage verzint. Je ziet per onderdeel hoe het tot stand komt." },
  { icon: ShieldCheck, title: "Geen verzonnen feiten", text: "De optimalisatie mag herformuleren en ordenen, maar geen cijfers, diploma's of ervaring toevoegen. Wat niet te staven is, leggen we aan jou voor." },
  { icon: Lock, title: "Jouw gegevens, jouw keuze", text: "Je cv wordt privé bewaard. Werkgevers zien het pas als jij solliciteert en toestemming geeft. Exporteren of alles verwijderen kan altijd." },
];

export default function LandingPage() {
  return (
    <>
      <section className="border-b border-border bg-surface">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.1fr_1fr] lg:py-24">
          <div>
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-border bg-surface-2 px-3 py-1 text-xs font-medium text-text-2">
              Voor werkzoekenden en werkgevers in België
            </p>
            <h1 className="text-4xl font-semibold leading-[1.1] tracking-tight text-text sm:text-5xl">
              Vind werk dat bij je past, en een cv dat dat laat zien.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
              {brand.name} vergelijkt je profiel eerlijk met vacatures in het Nederlands en het Frans, toont waar je sterk staat en wat ontbreekt,
              en helpt je per vacature een sterk cv te maken op basis van je echte ervaring.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg"><Link href="/register">Maak gratis een account <ArrowRight /></Link></Button>
              <Button asChild size="lg" variant="secondary"><Link href="/jobs">Bekijk vacatures</Link></Button>
            </div>
            <p className="mt-6 flex items-center gap-2 text-sm text-muted">
              <Building2 className="size-4" /> Werkgever? <Link href="/register?type=employer" className="font-medium text-accent hover:underline">Publiceer je vacatures</Link>
            </p>
          </div>

          <div aria-hidden className="relative">
            <div className="rounded-2xl border border-border bg-bg p-5 shadow-pop">
              <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted">Voorbeeld</p>
              <div className="rounded-xl border border-border bg-surface p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-text">Data Engineer</p>
                    <p className="text-sm text-muted">Gent · Hybride · Voltijds</p>
                  </div>
                  <div className="flex size-14 items-center justify-center rounded-full border-[5px] border-success/80 text-sm font-semibold text-success">86%</div>
                </div>
                <div className="mt-4 flex flex-col gap-2.5">
                  {[["Vaardigheden", 90], ["Relevante ervaring", 100], ["Functie en taken", 74], ["Jouw voorkeuren", 83]].map(([label, value]) => (
                    <div key={label as string}>
                      <div className="flex justify-between text-xs text-text-2"><span>{label}</span><span>{value}%</span></div>
                      <div className="mt-1 h-1.5 rounded-full bg-surface-2"><div className="h-full rounded-full bg-accent" style={{ width: `${value}%` }} /></div>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex flex-wrap gap-1.5 text-xs">
                  {["Python", "SQL", "PostgreSQL"].map((s) => <span key={s} className="rounded-md bg-success-soft px-2 py-0.5 font-medium text-success">{s}</span>)}
                  <span className="rounded-md bg-warning-soft px-2 py-0.5 font-medium text-warning">mist: Airflow</span>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2 rounded-xl border border-border bg-surface p-3 text-sm text-text-2">
                <CheckCircle2 className="size-4 shrink-0 text-success" /> Cv afgestemd: 3 punten herschreven, 0 verzonnen feiten
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <h2 className="text-2xl font-semibold tracking-tight text-text">Zo werkt het</h2>
        <ol className="mt-8 grid gap-6 md:grid-cols-3">
          {steps.map(({ icon: Icon, title, text }, i) => (
            <li key={title} className="rounded-xl border border-border bg-surface p-6 shadow-card">
              <div className="mb-4 flex items-center gap-3">
                <span className="flex size-9 items-center justify-center rounded-lg bg-accent-soft text-accent"><Icon className="size-5" /></span>
                <span className="text-sm font-medium text-muted">Stap {i + 1}</span>
              </div>
              <h3 className="font-semibold text-text">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="border-y border-border bg-surface">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="text-2xl font-semibold tracking-tight text-text">Slim, maar eerlijk</h2>
          <p className="mt-2 max-w-2xl text-muted">AI helpt je sneller vooruit, maar beslist niet in jouw plaats en verzint niets over jou.</p>
          <div className="mt-8 grid gap-8 md:grid-cols-3">
            {principles.map(({ icon: Icon, title, text }) => (
              <div key={title}>
                <Icon className="size-6 text-accent" />
                <h3 className="mt-3 font-semibold text-text">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 text-center sm:px-6">
        <h2 className="text-2xl font-semibold tracking-tight text-text">Klaar om te beginnen?</h2>
        <p className="mx-auto mt-2 max-w-xl text-muted">Een account is gratis. Zonder cv kun je ook meteen je profiel invullen.</p>
        <Button asChild size="lg" className="mt-6"><Link href="/register">Account aanmaken <ArrowRight /></Link></Button>
      </section>
    </>
  );
}
