import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Providers } from "@/components/providers";
import { themeScript } from "@/hooks/use-theme";
import { brand } from "@/lib/config";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: brand.name, template: `%s · ${brand.name}` },
  description: "Vind vacatures die echt bij je passen, begrijp waarom, en maak per vacature een sterk, eerlijk cv.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="nl-BE" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} min-h-dvh antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
