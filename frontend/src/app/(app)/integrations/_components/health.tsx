import { Badge } from "@/components/ui/badge";
import type { RunBrief } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { plural, runName, type Tone } from "@/lib/integrations";
import { cn } from "@/lib/utils";

const BADGE: Record<Tone, "positive" | "info" | "caution" | "destructive" | "secondary"> = {
  positive: "positive",
  info: "info",
  caution: "caution",
  negative: "destructive",
  neutral: "secondary",
};

export function HealthBadge({ tone, label }: { tone: Tone; label: string }) {
  return <Badge variant={BADGE[tone]}>{label}</Badge>;
}

/** Solid fill for runs that wrote data; an outline for checks without saving. */
const TICK: Record<string, { solid: string; outline: string }> = {
  success: { solid: "bg-positive", outline: "ring-positive" },
  failed: { solid: "bg-destructive", outline: "ring-destructive" },
  queued: { solid: "bg-info/50", outline: "ring-info" },
  running: { solid: "bg-info", outline: "ring-info" },
};

const STATUS_WORD: Record<string, string> = {
  success: "udane",
  failed: "nieudane",
  queued: "w kolejce",
  running: "w toku",
};

function summary(runs: RunBrief[]) {
  if (runs.length === 0) return "Jeszcze nie uruchamiane.";
  const failed = runs.filter((r) => r.status === "failed").length;
  const head = `Ostatnie ${runs.length} ${plural(runs.length, "uruchomienie", "uruchomienia", "uruchomień")}`;
  return failed ? `${head}, w tym ${failed} ${plural(failed, "nieudane", "nieudane", "nieudanych")}.` : `${head}, wszystkie udane.`;
}

/**
 * The source's recent runs as a row of ticks, oldest on the left: green wrote data, red failed, an outline was a check
 * without saving, cyan is queued or running. Empty slots keep every strip the same width so the list lines up.
 */
export function RunStrip({ runs, slots = 12, className }: { runs: RunBrief[]; slots?: number; className?: string }) {
  const shown = runs.slice(0, slots).reverse();
  const empty = Math.max(0, slots - shown.length);
  return (
    <div className={cn("flex items-center", className)}>
      <span className="sr-only">{summary(shown)}</span>
      <ol aria-hidden className="flex h-5 items-stretch gap-[3px]">
        {Array.from({ length: empty }, (_, n) => (
          <li key={`e${n}`} className="w-[7px] self-center border-b border-border" />
        ))}
        {shown.map((r) => {
          const style = TICK[r.status] ?? TICK.queued;
          return (
            <li
              key={r.id}
              title={`${runName(r)}: ${STATUS_WORD[r.status] ?? r.status}, ${formatDateTime(r.created_at)}${r.error ? `\n${r.error}` : ""}`}
              className={cn(
                "w-[7px]",
                r.dry_run ? cn("bg-transparent ring-1 ring-inset", style.outline) : style.solid,
              )}
            />
          );
        })}
      </ol>
    </div>
  );
}
