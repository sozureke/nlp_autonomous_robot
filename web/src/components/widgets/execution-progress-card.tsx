"use client";

import { Activity, CheckCircle2, AlertTriangle, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { JsonValue } from "@/lib/types";

function asNum(v: JsonValue | undefined): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function asStr(v: JsonValue | undefined): string | null {
  return typeof v === "string" && v.trim() ? v.trim() : null;
}

interface ExecutionProgressCardProps {
  activeTask: Record<string, JsonValue> | null;
  waitingTask: Record<string, JsonValue> | null;
  busy: boolean;
}

const STATUS_META: Record<string, { color: string; pulse: boolean }> = {
  running: { color: "text-blue-400", pulse: true },
  executing: { color: "text-blue-400", pulse: true },
  completed: { color: "text-emerald-400", pulse: false },
  interrupted: { color: "text-amber-400", pulse: false },
  idle: { color: "text-muted-foreground", pulse: false },
};

export function ExecutionProgressCard({
  activeTask,
  waitingTask,
  busy,
}: ExecutionProgressCardProps) {
  const rawCommand = asStr(activeTask?.raw_command);
  const status = asStr(activeTask?.status) ?? (busy ? "executing" : null);
  const currentStepIndex = asNum(activeTask?.current_step_index);
  const stepsTotal = asNum(activeTask?.steps_total);
  const stepElapsed = asNum(activeTask?.step_elapsed_sec);
  const stepDuration = asNum(activeTask?.step_duration_sec);
  const currentStep = activeTask?.current_step as Record<string, JsonValue> | null | undefined;
  const action = asStr(currentStep?.action);
  const speed = asNum(currentStep?.speed);
  const duration = asNum(currentStep?.duration);
  const lastInterruption = asStr(activeTask?.last_interruption);

  const progress =
    stepDuration !== null && stepDuration > 0 && stepElapsed !== null
      ? Math.min(1, stepElapsed / stepDuration)
      : null;

  const meta = STATUS_META[status ?? ""] ?? { color: "text-muted-foreground", pulse: false };

  const StatusIcon =
    status === "completed"
      ? CheckCircle2
      : status === "interrupted"
        ? AlertTriangle
        : status === "running" || status === "executing"
          ? Activity
          : Clock;

  const badgeVariant =
    status === "interrupted" ? "destructive" : "secondary";

  return (
    <Card size="sm">
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle className="flex items-center gap-2 text-sm">
          <StatusIcon
            className={cn("size-3.5", meta.color, meta.pulse && "animate-pulse")}
          />
          Execution
        </CardTitle>
        {status && (
          <Badge variant={badgeVariant} className="text-[10px] font-mono capitalize">
            {status}
          </Badge>
        )}
      </CardHeader>

      <CardContent className="space-y-3">
        {activeTask ? (
          <>
            {rawCommand && (
              <p className="truncate text-xs font-medium text-foreground">
                &ldquo;{rawCommand}&rdquo;
              </p>
            )}

            {currentStepIndex !== null && stepsTotal !== null && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2 text-[11px]">
                  <span className="text-muted-foreground">
                    Step{" "}
                    <span className="font-medium text-foreground">
                      {currentStepIndex + 1}
                    </span>{" "}
                    of {stepsTotal}
                    {action && (
                      <>
                        {" "}·{" "}
                        <span className="font-medium text-foreground">{action}</span>
                      </>
                    )}
                    {speed !== null && (
                      <span className="text-muted-foreground"> · speed {speed}</span>
                    )}
                    {duration !== null && (
                      <span className="text-muted-foreground"> · {duration}s</span>
                    )}
                  </span>
                  {stepElapsed !== null && (
                    <span className="shrink-0 font-mono tabular-nums text-muted-foreground">
                      {stepElapsed.toFixed(1)}s
                      {stepDuration !== null ? ` / ${stepDuration.toFixed(1)}s` : ""}
                    </span>
                  )}
                </div>

                {/* Determinate progress bar */}
                {progress !== null && (
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-500",
                        status === "interrupted" ? "bg-amber-500" : "bg-primary",
                      )}
                      style={{ width: `${(progress * 100).toFixed(1)}%` }}
                    />
                  </div>
                )}

                {/* Indeterminate — no duration known */}
                {progress === null &&
                  (status === "running" || status === "executing") && (
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div className="h-full w-full animate-pulse rounded-full bg-primary/50" />
                    </div>
                  )}
              </div>
            )}

            {lastInterruption && (
              <p className="flex items-center gap-1 text-[11px] text-amber-400">
                <AlertTriangle className="size-3 shrink-0" />
                {lastInterruption}
              </p>
            )}
          </>
        ) : (
          <p className="text-xs text-muted-foreground">No active task</p>
        )}

        {waitingTask && (
          <div className="rounded-md border border-border bg-muted/20 px-2.5 py-2">
            <p className="mb-0.5 text-[10px] uppercase tracking-widest text-muted-foreground">
              Queued
            </p>
            <p className="truncate text-xs text-foreground">
              {asStr(waitingTask.raw_command) ??
                asStr(waitingTask.command) ??
                "Waiting task"}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
