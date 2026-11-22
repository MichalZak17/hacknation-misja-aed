import { Bebas_Neue, JetBrains_Mono, Montserrat, Roboto_Condensed } from "next/font/google";

/**
 * The hacknation.pl families, self-hosted by next/font (all SIL Open Font License):
 * Bebas Neue (display, caps only), Montserrat (running text), JetBrains Mono (labels, code),
 * Roboto Condensed Light (the unit beside a big figure). latin-ext covers Polish diacritics.
 */
export const bebas = Bebas_Neue({
  variable: "--font-bebas",
  subsets: ["latin", "latin-ext"],
  weight: "400",
  display: "swap",
});
export const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});
export const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500"],
  display: "swap",
});
export const robotoCondensed = Roboto_Condensed({
  variable: "--font-roboto-condensed",
  subsets: ["latin", "latin-ext"],
  weight: "300",
  preload: false,
  display: "swap",
});

export const fontVariables = `${bebas.variable} ${montserrat.variable} ${jetbrains.variable} ${robotoCondensed.variable}`;
