"use client";

import { cn } from "@/lib/utils";

interface GlobalActivityBarProps {
  active: boolean;
}

/** Thin top bar while a user action is in progress (connect / plan / execute). */
export function GlobalActivityBar({ active }: GlobalActivityBarProps) {
  return (
    <div
      className={cn(
        "pointer-events-none fixed inset-x-0 top-0 z-[100] h-[3px] overflow-hidden bg-transparent transition-opacity duration-200",
        active ? "opacity-100" : "opacity-0",
      )}
      aria-hidden
    >
      <div
        className={cn(
          "global-activity-shimmer h-full w-[42%] rounded-full",
          "bg-gradient-to-r from-transparent via-foreground/75 to-transparent",
        )}
      />
    </div>
  );
}
