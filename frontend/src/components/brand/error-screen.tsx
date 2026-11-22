"use client";

import { RotateCw, Undo2 } from "lucide-react";

import { AccentBar } from "@/components/brand/accent-bar";
import { Blueprint } from "@/components/brand/blueprint";
import { Framed } from "@/components/brand/framed";
import { MetaLabel } from "@/components/brand/meta-label";
import { Terminal, type TerminalLine } from "@/components/brand/terminal";
import { Button } from "@/components/ui/button";

/**
 * Full-page error in the hero's language: a giant Bebas code (slate + crimson), a framed blueprint, accent bars and a
 * terminal line saying what failed. Used by app/not-found.tsx and app/error.tsx.
 */
export function ErrorScreen({
  code,
  title,
  body,
  lines,
  actions,
  meta,
}: {
  code: string;
  title: string;
  body: string;
  lines: TerminalLine[];
  actions: React.ReactNode;
  meta?: React.ReactNode;
}) {
  return (
    <main className="bg-background relative grid min-h-svh place-items-center overflow-hidden px-4 py-16">
      <div className="grid w-full max-w-[1000px] items-center gap-12 md:grid-cols-[1.1fr_1fr]">
        <div className="relative min-w-0">
          <MetaLabel>Błąd / {code}</MetaLabel>
          <div aria-hidden className="font-display mt-2 text-[clamp(7rem,24vw,13rem)] leading-[0.8]">
            <span className="text-hn-heading">{code.slice(0, 1)}</span>
            <span className="text-hn-crimson">{code.slice(1)}</span>
          </div>
          <AccentBar animate className="mt-4 h-2 w-[70%]" />
          <h1 className="type-h1 text-hn-heading mt-6">{title}</h1>
          <p className="type-lead text-muted-foreground mt-2 max-w-[44ch]">{body}</p>
          <div className="mt-8 flex flex-wrap gap-5">{actions}</div>
          {meta ? <div className="mt-6">{meta}</div> : null}
        </div>
        <div className="relative hidden md:block">
          <Framed offset={14} className="mx-auto w-[78%]">
            <Blueprint variant="tower" className="border" />
          </Framed>
          <AccentBar tone="crimson" from="right" animate className="absolute top-[18%] -right-4 h-7 w-[46%]" />
          <Terminal title="hack_" lines={lines} className="absolute -bottom-8 -left-6 w-[86%] shadow-lg" />
        </div>
      </div>
    </main>
  );
}

export function ReloadButton({ label, onClick }: { label: string; onClick?: () => void }) {
  return (
    <Button size="lg" framed onClick={onClick ?? (() => window.location.reload())}>
      <RotateCw /> {label}
    </Button>
  );
}

export function BackButton({ label }: { label: string }) {
  return (
    <Button size="lg" variant="outline" onClick={() => window.history.back()}>
      <Undo2 /> {label}
    </Button>
  );
}
