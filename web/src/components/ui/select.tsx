import * as React from "react";
import { cn } from "@/lib/utils";

const Select = React.forwardRef<HTMLSelectElement, React.ComponentProps<"select">>(
  ({ className, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(
          "h-10 rounded-md border border-slate-700 bg-slate-950/80 px-3 text-sm text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40",
          className
        )}
        {...props}
      />
    );
  }
);
Select.displayName = "Select";

export { Select };
