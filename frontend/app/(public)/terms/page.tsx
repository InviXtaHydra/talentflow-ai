import type { Metadata } from "next";

import { brand } from "@/lib/config";

export const metadata: Metadata = { title: "Voorwaarden" };

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-semibold tracking-tight text-text">Gebruiksvoorwaarden</h1>
      <p className="mt-3 text-muted">Ontwerpversie: laat deze tekst juridisch nakijken voor een publieke lancering.</p>
      <div className="mt-8 space-y-5 text-text-2">
        <p>{brand.name} helpt werkzoekenden vacatures te vinden en cv&apos;s af te stemmen, en helpt werkgevers vacatures te publiceren en sollicitaties te beheren.</p>
        <p>Je bent verantwoordelijk voor de juistheid van de informatie in je profiel en je cv&apos;s. Controleer elk door AI voorgesteld cv voordat je het gebruikt: het platform verhindert verzonnen feiten zo goed mogelijk, maar automatische controle is nooit perfect.</p>
        <p>Werkgevers publiceren enkel echte vacatures waarvoor ze bevoegd zijn, en gebruiken kandidaatgegevens uitsluitend voor de betreffende aanwerving.</p>
        <p>Matchscores zijn een hulpmiddel en geen beoordeling van een persoon. Aanwervingsbeslissingen worden door mensen genomen.</p>
        <p>Voorbeeldvacatures en -bedrijven met het label &quot;Demo&quot; zijn fictief en dienen alleen om het platform te tonen.</p>
      </div>
    </div>
  );
}
