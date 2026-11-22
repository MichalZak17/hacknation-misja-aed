import { cn } from "@/lib/utils";

/**
 * Line-drawn tower, standing in for the site's grayscale architecture photos (which belong to the organisers).
 * Slate lines on a pale panel by day, cyan lines on ink at night — the site's "dimension switch" in one figure.
 * Variants change the building, not the style.
 */
export function Blueprint({
  variant = "tower",
  className,
}: {
  variant?: "tower" | "block" | "arc";
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 200 260"
      aria-hidden
      className={cn(
        "bg-canvas text-hn-slate/70 dark:text-hn-cyan/80 block h-auto w-full",
        className,
      )}
      fill="none"
      stroke="currentColor"
      strokeWidth="1"
    >
      {variant === "tower" ? <Tower /> : variant === "block" ? <Block /> : <Arc />}
    </svg>
  );
}

/** Round to 0.1 so server and client print identical path strings (no hydration mismatch). */
const r = (n: number) => Math.round(n * 10) / 10;

function Tower() {
  const floors = Array.from({ length: 22 }, (_, i) => 30 + i * 10);
  return (
    <g>
      <path d="M60 260 L78 22 L128 8 L150 260" strokeWidth="1.4" />
      <path d="M78 22 L104 260" opacity="0.6" />
      {floors.map((y) => {
        const t = (y - 8) / 252;
        const lx = 78 - 18 * t;
        const rx = 128 + 22 * t;
        const mx = 78 + 26 * t;
        return <path key={y} d={`M${r(lx)} ${y} L${r(mx)} ${y + 2} L${r(rx)} ${y - 6}`} opacity="0.55" />;
      })}
      {[90, 104, 116].map((x, i) => (
        <path key={x} d={`M${x + i * 2} 14 L${x + 14 + i * 8} 260`} opacity="0.35" />
      ))}
      <path d="M0 250 H200" opacity="0.4" />
    </g>
  );
}

function Block() {
  const cols = Array.from({ length: 9 }, (_, i) => 30 + i * 17);
  const rows = Array.from({ length: 12 }, (_, i) => 70 + i * 15);
  return (
    <g>
      <path d="M20 250 V60 L100 40 L180 60 V250" strokeWidth="1.4" />
      <path d="M20 60 L100 76 L180 60" opacity="0.6" />
      <path d="M100 76 V250" opacity="0.6" />
      {rows.map((y) => (
        <path key={y} d={`M20 ${y} L100 ${y + 14} L180 ${y}`} opacity="0.45" />
      ))}
      {cols.map((x) => (
        <path key={x} d={`M${x} ${r(80 - Math.abs(100 - x) * 0.2)} V250`} opacity="0.25" />
      ))}
    </g>
  );
}

function Arc() {
  const ribs = Array.from({ length: 14 }, (_, i) => 18 + i * 12.5);
  return (
    <g>
      <path d="M10 250 V120 Q100 40 190 120 V250" strokeWidth="1.4" />
      <path d="M10 150 Q100 80 190 150" opacity="0.6" />
      {ribs.map((x) => (
        <path key={x} d={`M${x} 250 V${r(150 - Math.sin(((x - 10) / 180) * Math.PI) * 50)}`} opacity="0.4" />
      ))}
      <path d="M10 200 H190 M10 225 H190" opacity="0.4" />
    </g>
  );
}
