import { cn } from "@/lib/utils";

/**
 * A headline figure: Bebas number in crimson, a light condensed unit beside it ("+370 000 PLN").
 * Use one per section at most; it is the loudest thing on the screen.
 */
export function Stat({
  value,
  unit,
  label,
  tone = "crimson",
  className,
}: {
  value: string;
  unit?: string;
  label?: string;
  tone?: "crimson" | "heading";
  className?: string;
}) {
  return (
    <div className={cn("min-w-0", className)}>
      {label ? <div className="type-h3 text-hn-heading mb-1">{label}</div> : null}
      <div className="flex flex-wrap items-baseline gap-x-3">
        <span className={cn("type-figure-lg", tone === "crimson" ? "text-hn-crimson" : "text-hn-heading")}>
          {value}
        </span>
        {unit ? <span className="type-unit text-hn-heading">{unit}</span> : null}
      </div>
    </div>
  );
}
