"use client";

import * as React from "react";
import { cn } from "cn";

/** Name of the scroll container: the table's own label or caption, else a generic one. */
function regionLabel(table: HTMLTableElement) {
  const labelledBy = table.getAttribute("aria-labelledby");
  const fromId = labelledBy ? document.getElementById(labelledBy)?.textContent : null;
  return (
    table.getAttribute("aria-label") || fromId || table.caption?.textContent?.trim() || "Tabela, przewiń w poziomie"
  );
}

function Table({ className, ...props }: React.ComponentProps<"table">) {
  const ref = React.useRef<HTMLDivElement>(null);
  // WCAG 2.1.1: when the table is wider than its container (phones), the scroll container must be reachable by
  // keyboard, so it becomes a focusable, named region. Only then: a table that fits adds no extra tab stop.
  const [scrollable, setScrollable] = React.useState<string | null>(null);
  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => {
      const table = el.querySelector("table");
      setScrollable(table && el.scrollWidth > el.clientWidth + 1 ? regionLabel(table) : null);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    const table = el.querySelector("table");
    if (table) observer.observe(table);
    return () => observer.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      data-slot="table-container"
      className="relative w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      {...(scrollable ? { tabIndex: 0, role: "region", "aria-label": scrollable } : {})}
    >
      <table data-slot="table" className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  );
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return <thead data-slot="table-header" className={cn("[&_tr]:border-b", className)} {...props} />;
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return <tbody data-slot="table-body" className={cn("[&_tr:last-child]:border-0", className)} {...props} />;
}

function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn("bg-muted/50 border-t font-medium [&>tr]:last:border-b-0", className)}
      {...props}
    />
  );
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        "hover:bg-muted/50 has-aria-expanded:bg-muted/50 data-[state=selected]:bg-muted border-b transition-colors",
        className,
      )}
      {...props}
    />
  );
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap [&:has([role=checkbox])]:pr-0",
        className,
      )}
      {...props}
    />
  );
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn("p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0", className)}
      {...props}
    />
  );
}

function TableCaption({ className, ...props }: React.ComponentProps<"caption">) {
  return (
    <caption
      data-slot="table-caption"
      className={cn("text-muted-foreground mt-4 text-sm", className)}
      {...props}
    />
  );
}

export { Table, TableHeader, TableBody, TableFooter, TableHead, TableRow, TableCell, TableCaption };
