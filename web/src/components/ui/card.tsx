import * as React from "react";
import { cn } from "@/lib/utils";

function Card({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-700/70 bg-slate-900/80 p-4 shadow-[0_14px_30px_rgba(0,0,0,0.35)] backdrop-blur",
        className
      )}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: React.ComponentProps<"h3">) {
  return <h3 className={cn("text-xs font-semibold uppercase tracking-wider text-slate-400", className)} {...props} />;
}

function CardDescription({ className, ...props }: React.ComponentProps<"p">) {
  return <p className={cn("mt-1 text-xs text-slate-500", className)} {...props} />;
}

export { Card, CardTitle, CardDescription };
