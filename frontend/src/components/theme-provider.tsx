"use client";

import { ThemeProvider } from "next-themes";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

/**
 * next-themes renders an inline <script> that sets the theme class before paint. On the client mark it as a data
 * block so React doesn't warn that it won't execute.
 */
const themeScriptProps = typeof window === "undefined" ? undefined : { type: "application/json" };

/** Theme, tooltip and toast providers. Day dimension (light) by default, like hacknation.pl. */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="light"
      enableSystem
      disableTransitionOnChange
      scriptProps={themeScriptProps}
    >
      <TooltipProvider delayDuration={300}>
        {children}
        <Toaster richColors position="top-center" />
      </TooltipProvider>
    </ThemeProvider>
  );
}
