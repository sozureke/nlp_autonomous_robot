"use client";

import { useState } from "react";
import { MonitorSmartphone, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { JsonFields } from "@/components/json-fields";
import { cn } from "@/lib/utils";
import type { HealthResponse, StateResponse, JsonValue } from "@/lib/types";

interface RuntimeCardProps {
  health: HealthResponse | null;
  state: StateResponse | null;
}

export function RuntimeCard({ health, state }: RuntimeCardProps) {
  const [open, setOpen] = useState(false);

  const cmdMode = health?.command_mode ?? state?.command_mode;
  const badges: { label: string; ok: boolean }[] = [
    { label: `connected: ${health?.connected ?? false}`, ok: health?.connected ?? false },
    { label: `ready: ${health?.ready ?? false}`, ok: health?.ready ?? false },
    { label: `busy: ${health?.busy ?? false}`, ok: !(health?.busy ?? false) },
    { label: `method: ${health?.method ?? "—"}`, ok: !!health?.method },
    { label: `command_mode: ${cmdMode ?? "—"}`, ok: !!cmdMode },
  ];

  const detailData: Record<string, JsonValue> = {
    runtime_status: state?.runtime_status ?? null,
    last_error: state?.last_error ?? null,
    last_plan_command: state?.last_plan_command ?? null,
    last_command_plan: state?.last_command_plan ?? null,
  };

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <MonitorSmartphone className="size-3.5 text-muted-foreground" />
          Runtime Snapshot
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex flex-wrap gap-1">
          {badges.map((b) => (
            <Badge
              key={b.label}
              variant={b.ok ? "secondary" : "destructive"}
              className="text-[10px] font-mono"
            >
              {b.label}
            </Badge>
          ))}
        </div>

        <Collapsible open={open} onOpenChange={setOpen}>
          <CollapsibleTrigger className="flex w-full items-center gap-1 rounded-md px-1 py-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground">
            <ChevronDown className={cn("size-3 transition-transform", open && "rotate-180")} />
            Runtime details
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-1 rounded-lg border border-border bg-muted/30 p-2.5">
              <JsonFields data={detailData} />
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}
