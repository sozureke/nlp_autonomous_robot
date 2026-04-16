"use client";

import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";

export function Toaster() {
  const { toasts, remove } = useToast();

  return (
    <div className="fixed right-4 top-4 z-50 grid w-[min(360px,calc(100vw-2rem))] gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "rounded-xl border bg-slate-950/95 p-3 shadow-xl backdrop-blur",
            toast.variant === "error" && "border-rose-500/50",
            toast.variant === "success" && "border-emerald-500/50",
            toast.variant === "info" && "border-blue-500/50"
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-slate-100">{toast.title}</p>
              {toast.description ? <p className="mt-0.5 text-xs text-slate-400">{toast.description}</p> : null}
            </div>
            <button
              className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-100"
              onClick={() => remove(toast.id)}
              aria-label="Close notification"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
