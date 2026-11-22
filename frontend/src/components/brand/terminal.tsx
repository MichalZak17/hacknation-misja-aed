import { cn } from "@/lib/utils";

export type TerminalLine =
  | { kind: "cmd"; text: string }
  | { kind: "out"; text: string }
  | { kind: "accent"; text: string };

/**
 * The ink terminal window from the "O HackNation" section: a title bar, mono lines, a blinking caret on the last
 * prompt. Always dark (hn-terminal) in both dimensions. Lines type in one after another unless `still` is set;
 * reduced motion shows them at once (global rule in globals.css).
 */
export function Terminal({
  title = "hack_",
  lines,
  still = false,
  className,
  children,
}: {
  title?: string;
  lines: TerminalLine[];
  still?: boolean;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "bg-hn-terminal text-hn-terminal-foreground border-hn-terminal-line relative overflow-hidden border font-mono text-[0.8125rem] leading-6",
        className,
      )}
    >
      <div className="flex items-center justify-between border-hn-terminal-line border-b px-4 py-2">
        <span className="text-hn-cyan">{title}</span>
        <span aria-hidden className="flex gap-1.5">
          <span className="block size-2 bg-hn-terminal-dot" />
          <span className="block size-2 bg-hn-terminal-dot" />
          <span className="bg-hn-crimson block size-2" />
        </span>
      </div>
      <div className="space-y-0.5 px-4 py-3">
        {lines.map((line, i) => (
          <div
            key={i}
            className={cn(
              "w-fit max-w-full whitespace-pre-wrap",
              !still && "animate-type",
              line.kind === "accent" && "text-hn-cyan",
              line.kind === "out" && "text-hn-terminal-muted",
            )}
            style={
              still
                ? undefined
                : ({ "--chars": Math.max(line.text.length, 1), animationDelay: `${i * 0.9}s` } as React.CSSProperties)
            }
          >
            {line.kind === "cmd" ? <span className="text-hn-crimson">$ </span> : null}
            {line.text}
          </div>
        ))}
        <div aria-hidden>
          <span className="text-hn-crimson">$ </span>
          <span className="animate-caret bg-hn-cyan inline-block h-4 w-2 translate-y-0.5" />
        </div>
        {children}
      </div>
    </div>
  );
}
