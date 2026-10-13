import type { Metadata } from "next";
import Link from "next/link";

import { brand } from "@/lib/config";

export const metadata: Metadata = { title: "Privacyverklaring" };

const sections: [string, string[]][] = [
  ["Welke gegevens we verwerken", [
    "Accountgegevens: naam, e-mailadres, wachtwoord (alleen als onomkeerbare hash) en je rol.",
    "Je professionele profiel en voorkeuren, zoals je die zelf invult of bevestigt.",
    "Cv-bestanden die je uploadt, de tekst die eruit gehaald wordt en de cv-versies die je maakt.",
    "Sollicitaties, bewaarde vacatures, meldingen en gesprekken met de carrière-assistent.",
    "Technische gegevens voor beveiliging: sessies en een gehashte versie van je IP-adres in het auditlogboek.",
  ]],
  ["Waarvoor we ze gebruiken", [
    "Om je vacatures te tonen die bij je passen, met een uitlegbare matchscore.",
    "Om op jouw vraag een cv af te stemmen op een vacature en als bestand aan te maken.",
    "Om je sollicitatie aan een werkgever te bezorgen, alleen als jij solliciteert en toestemming geeft om je cv te delen.",
    "Om het platform te beveiligen en misbruik te voorkomen.",
  ]],
  ["AI-verwerking", [
    "Standaard draait het taalmodel lokaal (Ollama) op de server van het platform: je cv wordt dan niet naar een externe AI-dienst gestuurd.",
    "Als de beheerder een externe AI-dienst inschakelt, wordt dat hier vermeld samen met de verwerker en zijn voorwaarden.",
    "Matchscores worden berekend met een transparante methode. Gevoelige kenmerken zoals leeftijd, geslacht, afkomst, religie, handicap of foto's worden nooit gebruikt.",
    "AI neemt geen beslissingen over aanwerving: werkgevers zien kwalificaties, en mensen beslissen.",
  ]],
  ["Delen met werkgevers", [
    "Werkgevers zien je gegevens enkel wanneer je via het platform solliciteert. Je kiest zelf welk cv je meestuurt.",
    "Externe sollicitaties die je bijhoudt, blijven privé.",
  ]],
  ["Bewaring", [
    "We bewaren je gegevens zolang je account bestaat. Operationele logboeken worden na een beperkte termijn verwijderd.",
    "De beheerder kan instellen dat accounts na een lange periode van inactiviteit automatisch verwijderd worden.",
  ]],
  ["Jouw rechten", [
    "Inzage en overdraagbaarheid: download al je gegevens als JSON-bestand via Privacy & gegevens.",
    "Verbetering: pas je profiel en cv's op elk moment aan.",
    "Verwijdering: verwijder afzonderlijke cv's of je volledige account, inclusief bestanden.",
  ]],
];

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-3xl font-semibold tracking-tight text-text">Privacyverklaring</h1>
      <p className="mt-3 text-muted">
        Deze verklaring beschrijft hoe {brand.name} met je persoonsgegevens omgaat. Ze is technisch correct voor deze software, maar moet vóór een
        publieke lancering juridisch nagekeken en aangevuld worden met de gegevens van de verwerkingsverantwoordelijke.
      </p>
      {sections.map(([title, items]) => (
        <section key={title} className="mt-8">
          <h2 className="text-lg font-semibold text-text">{title}</h2>
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-text-2">{items.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      ))}
      <p className="mt-10 text-sm text-muted">Beheer je gegevens via <Link href="/privacy/data" className="text-accent underline">Privacy &amp; gegevens</Link> (na inloggen).</p>
    </div>
  );
}
