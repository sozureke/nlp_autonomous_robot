import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-slate-700 bg-slate-900 text-slate-200",
        success: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
        warning: "border-amber-500/50 bg-amber-500/10 text-amber-300",
        destructive: "border-rose-500/50 bg-rose-500/10 text-rose-300",
        info: "border-blue-500/50 bg-blue-500/10 text-blue-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
