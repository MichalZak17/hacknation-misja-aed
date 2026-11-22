import { cn } from "@/lib/utils";

/**
 * The HACK / NATION wordmark, set in Bebas Neue: first line slate (near-white at night), second line crimson.
 * Size it with font-size on className (it inherits): `text-[9rem]`, or `type-display` for the fluid hero size.
 */
export function Wordmark({ className, inline = false }: { className?: string; inline?: boolean }) {
  return (
    <span
      role="img"
      aria-label="HackNation"
      className={cn(
        "font-display leading-[0.82] tracking-[0.005em] uppercase",
        inline ? "inline-flex gap-[0.18em]" : "inline-flex flex-col",
        className,
      )}
    >
      <span aria-hidden className="text-hn-heading">
        Hack
      </span>
      <span aria-hidden className="text-hn-crimson">
        Nation
      </span>
    </span>
  );
}

/** The square HN monogram (the favicon). */
export function Monogram({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" role="img" aria-label="HackNation" className={cn("size-8 shrink-0", className)}>
      <rect width="64" height="64" className="fill-hn-crimson" />
      <path
        fill="#fff"
        d="M10 14h7v14h8V14h7v36h-7V35h-8v15h-7zM36 14h7l7 19V14h6v36h-6l-8-20v20h-6z"
      />
    </svg>
  );
}
