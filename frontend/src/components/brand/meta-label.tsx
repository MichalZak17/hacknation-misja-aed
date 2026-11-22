import { cn } from "@/lib/utils";

/**
 * Mono caps label for facts people scan: dates and places ("21–22.11.2026 / BYDGOSZCZ"), the organiser above a logo
 * ("> Ministerstwo Cyfryzacji"), a slide's section number. Crimson by default; `muted` for secondary ones.
 */
export function MetaLabel({
  children,
  prompt = false,
  tone = "crimson",
  className,
}: {
  children: React.ReactNode;
  /** prefix with the terminal ">" */
  prompt?: boolean;
  tone?: "crimson" | "muted";
  className?: string;
}) {
  return (
    <span
      className={cn(
        "type-label inline-block",
        tone === "crimson" ? "text-crimson-text" : "text-subtle-foreground",
        className,
      )}
    >
      {prompt ? <span aria-hidden>&gt; </span> : null}
      {children}
    </span>
  );
}
