"use client";

import { Button } from "@/components/ui/button";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex min-h-[60dvh] flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-2xl font-semibold text-text">Er ging iets mis</h1>
      <p className="max-w-sm text-muted">Probeer het opnieuw. Blijft het probleem bestaan, kom dan later terug.</p>
      <Button onClick={reset}>Opnieuw proberen</Button>
    </div>
  );
}
