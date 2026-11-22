import { cn } from "@/lib/utils";

/**
 * Faint code fragments sprinkled around hero imagery (`buffer_size = 1024`). Pure texture: aria-hidden, never
 * real information, never more than three per screen.
 */
export function CodeDeco({ children, className }: { children: string; className?: string }) {
  return (
    <pre
      aria-hidden
      className={cn(
        "text-subtle-foreground pointer-events-none font-mono text-[0.625rem] leading-[1.35] select-none",
        className,
      )}
    >
      {children}
    </pre>
  );
}
