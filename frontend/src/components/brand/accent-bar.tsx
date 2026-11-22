import { cn } from "@/lib/utils";

const TONES = {
  crimson: "bg-hn-crimson",
  slate: "bg-hn-slate dark:bg-hn-cyan",
  cyan: "bg-hn-cyan",
} as const;

/**
 * A solid accent bar, the site's signature block. Under headings it is a thin rule (h-1); around hero imagery it is a
 * chunky block (h-6 to h-10) overlapping the photo's frame. Decorative only, so it is hidden from assistive tech.
 * `from` sets the edge it grows out of when `animate` is on.
 */
export function AccentBar({
  tone = "crimson",
  from = "left",
  animate = false,
  className,
  style,
}: {
  tone?: keyof typeof TONES;
  from?: "left" | "right";
  animate?: boolean;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <span
      aria-hidden
      style={style}
      className={cn(
        "block h-1",
        TONES[tone],
        animate && "animate-bar-in",
        from === "left" ? "origin-left" : "origin-right",
        className,
      )}
    />
  );
}
