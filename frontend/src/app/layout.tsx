import type { Metadata, Viewport } from "next";

import { fontVariables } from "@/app/fonts";
import { Providers } from "@/components/theme-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Misja AED · dane", template: "%s · Misja AED" },
  description: "Zbieranie i łączenie danych o defibrylatorach AED z wielu źródeł do zbioru na dane.gov.pl.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f5f5f7" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1f28" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pl" className={`${fontVariables} h-full antialiased`} suppressHydrationWarning>
      <body className="bg-background text-foreground min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
