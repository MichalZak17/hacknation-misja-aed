import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * The "Rejestrując się, zyskujesz dostęp do" tile: a square bordered box, a two-tone line icon (slate strokes with a
 * crimson accent dot), centred copy with the key words in bold. Grid them 3 across on desktop, 2 on tablets, 1 on phones.
 */
export function FeatureTile({
  icon: Icon,
  children,
  className,
}: {
  icon: LucideIcon;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "bg-card flex flex-col items-center gap-4 border px-6 py-8 text-center transition-[border-color] duration-150 hover:border-frame-line",
        className,
      )}
    >
      <span className="relative">
        <Icon aria-hidden strokeWidth={1.5} className="text-hn-slate dark:text-hn-cyan size-10" />
        <span aria-hidden className="bg-hn-crimson absolute -top-0.5 -right-1 size-2" />
      </span>
      <p className="type-body text-muted-foreground max-w-[26ch] [&_strong]:text-foreground [&_strong]:font-semibold">
        {children}
      </p>
    </div>
  );
}
