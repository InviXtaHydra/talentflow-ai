import { BrowseShell } from "@/components/layout/browse-shell";

export default function BrowseLayout({ children }: { children: React.ReactNode }) {
  return <BrowseShell>{children}</BrowseShell>;
}
