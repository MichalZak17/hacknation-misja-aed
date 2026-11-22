import { cn } from "cn";
import { Loader2Icon } from "lucide-react";

function Spinner({ className, ...props }: React.ComponentProps<"svg">) {
  return (
    <Loader2Icon
      data-slot="spinner"
      role="status"
      aria-label="Loading"
      className={cn(
        // Muted on its own; inside a button or badge it takes the control's own ink.
        "text-muted-foreground in-data-[slot=badge]:text-current in-data-[slot=button]:text-current size-4 animate-spin",
        className,
      )}
      {...props}
    />
  );
}

export { Spinner };
