"use client";

import { useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";

import { cn } from "@/lib/utils";

export interface SegmentedOption<T extends string> {
  value: T;
  label: React.ReactNode;
}

/**
 * Single-choice switcher with a sliding indicator (e.g. Day / Week / Month). Behaves as a radio group:
 * arrow keys move the selection, Tab leaves the control.
 */
export function SegmentedControl<T extends string>({
  options,
  value,
  onValueChange,
  label,
  className,
}: {
  options: SegmentedOption<T>[];
  value: T;
  onValueChange: (value: T) => void;
  /** Accessible name for the group. */
  label: string;
  className?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const [box, setBox] = useState<{ x: number; w: number } | null>(null);
  const index = Math.max(
    0,
    options.findIndex((o) => o.value === value),
  );

  useLayoutEffect(() => {
    const measure = () => {
      const el = refs.current[index];
      if (el) setBox({ x: el.offsetLeft, w: el.offsetWidth });
    };
    measure();
    // Re-measure when the control changes size, including when it is first shown after mounting hidden
    const observer = new ResizeObserver(measure);
    if (refs.current[index]?.parentElement) observer.observe(refs.current[index]!.parentElement!);
    return () => observer.disconnect();
  }, [index, options.length]);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const step =
      event.key === "ArrowRight" || event.key === "ArrowDown"
        ? 1
        : event.key === "ArrowLeft" || event.key === "ArrowUp"
          ? -1
          : 0;
    if (!step) return;
    event.preventDefault();
    const next = (index + step + options.length) % options.length;
    onValueChange(options[next].value);
    refs.current[next]?.focus();
  }

  return (
    <div
      data-slot="segmented-control"
      role="radiogroup"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={cn("bg-muted relative inline-flex h-9 items-center rounded-lg p-0.5", className)}
    >
      {box ? (
        <span
          aria-hidden
          className="bg-background ease-spring absolute inset-y-0.5 left-0 rounded-md shadow-sm transition-[translate,width] duration-450"
          style={{ translate: `${box.x}px 0`, width: box.w }}
        />
      ) : null}
      {options.map((option, i) => {
        const active = i === index;
        return (
          <button
            key={option.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onValueChange(option.value)}
            className={cn(
              "focus-visible:outline-ring relative z-10 inline-flex h-7 items-center gap-1.5 rounded-md px-3 text-sm font-medium whitespace-nowrap transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-1 [&_svg]:size-4",
              active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
