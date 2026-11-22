import { cn } from "@/lib/utils";

/**
 * Puts a hairline outline behind its child, offset up and to the right, like the photos and buttons on hacknation.pl.
 * For buttons use `<Button framed>`; this is for images, tiles and figures.
 */
export function Framed({
  children,
  offset = 10,
  direction = "up-right",
  className,
}: {
  children: React.ReactNode;
  /** px between the child and the outline */
  offset?: number;
  direction?: "up-right" | "down-left" | "down-right" | "up-left";
  className?: string;
}) {
  const x = direction.endsWith("right") ? offset : -offset;
  const y = direction.startsWith("up") ? -offset : offset;
  return (
    <div className={cn("relative isolate", className)}>
      <span
        aria-hidden
        className="border-frame-line pointer-events-none absolute inset-0 -z-10 border"
        style={{ transform: `translate(${x}px, ${y}px)` }}
      />
      {children}
    </div>
  );
}
