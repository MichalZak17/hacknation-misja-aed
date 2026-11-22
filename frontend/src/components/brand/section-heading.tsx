import { AccentBar } from "@/components/brand/accent-bar";
import { cn } from "@/lib/utils";

/**
 * The site's section title: Bebas caps in slate, a crimson rule underneath that runs past the words.
 * `align="right"` hangs the rule off the right edge instead (the site alternates them down a page).
 */
export function SectionHeading({
  children,
  id,
  as: Tag = "h2",
  align = "left",
  className,
}: {
  children: React.ReactNode;
  id?: string;
  as?: "h1" | "h2" | "h3";
  align?: "left" | "right";
  className?: string;
}) {
  return (
    <div className={cn("relative", className)}>
      <Tag id={id} className="type-h1 text-hn-heading">
        {children}
      </Tag>
      <AccentBar
        animate
        from={align}
        className={cn("mt-2 w-[min(28rem,70%)]", align === "right" && "ml-auto")}
      />
    </div>
  );
}
