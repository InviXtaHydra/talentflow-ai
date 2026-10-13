import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-sm font-medium text-accent">404</p>
      <h1 className="text-2xl font-semibold text-text">Deze pagina bestaat niet</h1>
      <p className="max-w-sm text-muted">De link is misschien verouderd, of de vacature werd verwijderd.</p>
      <Button asChild><Link href="/">Naar de startpagina</Link></Button>
    </div>
  );
}
