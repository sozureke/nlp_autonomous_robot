"use client";

import { useEffect, useState } from "react";
import { Loader2, Radio, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";

function formatAgo(ts: number | null): string {
  if (ts == null) return "—";
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  return new Date(ts).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

interface SyncStatusProps {
  polling: boolean;
  lastSyncedAt: number | null;
  apiReachable: boolean;
}

export function SyncStatus({ polling, lastSyncedAt, apiReachable }: SyncStatusProps) {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => tick((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  if (!apiReachable) {
    return (
      <Badge variant="destructive" className="gap-1.5 font-normal">
        <WifiOff className="size-3" />
        API unreachable
      </Badge>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] text-muted-foreground">
      <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted/40 px-2 py-0.5">
        {polling ? (
          <Loader2 className="size-3 animate-spin text-foreground" aria-label="Syncing" />
        ) : (
          <Radio className="size-3 text-emerald-500" aria-hidden />
        )}
        <span>{polling ? "Syncing…" : "Live"}</span>
      </span>
      <span className="font-mono tabular-nums text-muted-foreground">
        Updated {formatAgo(lastSyncedAt)}
      </span>
    </div>
  );
}
