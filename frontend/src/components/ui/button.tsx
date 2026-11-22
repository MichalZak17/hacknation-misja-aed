import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "cn";
import { Slot } from "radix-ui";

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-none border border-transparent bg-clip-padding font-sans text-sm font-semibold leading-none whitespace-nowrap outline-none select-none transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-40 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary-hover active:bg-primary-pressed",
        /* The brand call to action ("Zarejestruj się"): crimson in both dimensions. One per page, never beside destructive. */
        cta: "bg-hn-crimson text-white hover:bg-hn-crimson-hover active:bg-hn-crimson-pressed focus-visible:outline-hn-crimson",
        outline:
          "border-input bg-background text-foreground hover:bg-secondary-hover aria-expanded:bg-secondary-hover",
        filter:
          "border-input bg-background text-foreground border-dashed hover:bg-secondary-hover aria-expanded:bg-secondary-hover data-[active=true]:border-solid",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary-hover aria-expanded:bg-secondary-hover",
        ghost: "text-foreground hover:bg-accent active:bg-pressed aria-expanded:bg-accent",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90 focus-visible:outline-destructive",
        link: "text-link hover:text-link-hover h-auto! px-0! font-sans text-sm font-semibold underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 gap-1.5 px-4 has-data-[icon=inline-end]:pr-2.5 has-data-[icon=inline-start]:pl-2.5",
        xs: "h-6 gap-1 px-2 text-xs in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 px-3 text-[0.8125rem] in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-11 gap-2 px-5 text-base has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3",
        icon: "size-9",
        "icon-xs":
          "size-6 in-data-[slot=button-group]:rounded-lg [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8 in-data-[slot=button-group]:rounded-lg",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  framed = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    /** The hacknation.pl hero look: a hairline outline offset up and to the right behind the button. */
    framed?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : "button";

  const button = (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className: framed ? undefined : className }))}
      {...props}
    />
  );
  if (!framed) return button;
  return (
    <span data-slot="button-frame" className={cn("relative isolate inline-flex", className)}>
      <span
        aria-hidden
        className="border-frame-line pointer-events-none absolute inset-0 -z-10 translate-x-[6px] -translate-y-[6px] border"
      />
      {button}
    </span>
  );
}

export { Button, buttonVariants };
