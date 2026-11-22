import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "cn";
import { Slot } from "radix-ui";

const markerVariants = cva(
  "group/marker text-subtle-foreground relative flex min-h-4 w-full items-center gap-2 text-left text-xs [&_svg:not([class*='size-'])]:size-3.5 [a]:rounded-xs [a]:underline [a]:underline-offset-3 [a]:outline-none [a]:transition-colors [a]:duration-150 [a]:ease-standard [a]:hover:text-foreground [a]:focus-visible:outline-2 [a]:focus-visible:outline-offset-2 [a]:focus-visible:outline-ring",
  {
    variants: {
      variant: {
        default: "",
        separator:
          "before:bg-border after:bg-border before:mr-1 before:h-px before:min-w-0 before:flex-1 after:ml-1 after:h-px after:min-w-0 after:flex-1",
        border: "border-border border-b pb-2",
      },
    },
  },
);

function Marker({
  className,
  variant = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"div"> &
  VariantProps<typeof markerVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : "div";

  return (
    <Comp
      data-slot="marker"
      data-variant={variant}
      className={cn(markerVariants({ variant, className }))}
      {...props}
    />
  );
}

function MarkerIcon({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="marker-icon"
      aria-hidden="true"
      className={cn(
        "flex size-3.5 shrink-0 items-center justify-center [&_svg:not([class*='size-'])]:size-3.5",
        className,
      )}
      {...props}
    />
  );
}

function MarkerContent({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="marker-content"
      className={cn(
        "min-w-0 wrap-break-word group-data-[variant=separator]/marker:flex-none group-data-[variant=separator]/marker:text-center *:[a]:text-link *:[a]:rounded-xs *:[a]:underline-offset-3 *:[a]:outline-none *:[a]:hover:text-link-hover *:[a]:hover:underline *:[a]:focus-visible:outline-2 *:[a]:focus-visible:outline-offset-2 *:[a]:focus-visible:outline-ring",
        className,
      )}
      {...props}
    />
  );
}

export { Marker, MarkerIcon, MarkerContent, markerVariants };
