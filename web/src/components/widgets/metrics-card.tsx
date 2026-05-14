"use client";

import { useState } from "react";
import { BarChart3, RefreshCw, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { labelCommandMode, type MetricsResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

interface MetricsCardProps {
  metrics: MetricsResponse | null;
  onReset: () => Promise<void>;
}

function pct(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

export function MetricsCard({ metrics, onReset }: MetricsCardProps) {
  const [resetting, setResetting] = useState(false);

  async function handleReset() {
    setResetting(true);
    try {
      await onReset();
    } finally {
      setResetting(false);
    }
  }

  const modes = metrics?.by_mode ? Object.entries(metrics.by_mode) : [];

  return (
    <Card size="sm">
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle className="flex items-center gap-2 text-sm">
          <BarChart3 className="size-3.5 text-muted-foreground" />
          Experiment Metrics
        </CardTitle>
        <div className="flex items-center gap-2">
          {metrics && (
            <span className="text-[11px] text-muted-foreground">
              {metrics.total_commands} cmd{metrics.total_commands !== 1 ? "s" : ""}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            disabled={resetting}
            onClick={() => void handleReset()}
          >
            {resetting ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <RefreshCw className="size-3.5" />
            )}
            Reset
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {modes.length === 0 ? (
          <p className="py-2 text-center text-xs text-muted-foreground">
            No metrics recorded yet
          </p>
        ) : (
          <>
            {/* By-mode comparison table */}
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    {["Mode", "Cmds", "Completion", "Safety viol.", "Avg time"].map((h) => (
                      <th
                        key={h}
                        className={cn(
                          "px-3 py-2 text-[10px] font-medium uppercase tracking-widest text-muted-foreground",
                          h === "Mode" ? "text-left" : "text-right",
                        )}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {modes.map(([mode, stats]) => (
                    <tr
                      key={mode}
                      className="border-b border-border last:border-0 transition-colors hover:bg-muted/20"
                    >
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center rounded-md border border-border px-1.5 py-0.5 font-mono text-[10px]">
                          {labelCommandMode(mode)}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums text-muted-foreground">
                        {stats.completed}/{stats.total}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <span
                          className={cn(
                            "font-mono font-medium tabular-nums",
                            stats.completion_rate >= 0.8
                              ? "text-emerald-400"
                              : stats.completion_rate >= 0.5
                                ? "text-amber-400"
                                : "text-destructive",
                          )}
                        >
                          {pct(stats.completion_rate)}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <span
                          className={cn(
                            "font-mono tabular-nums",
                            stats.safety_violations > 0
                              ? "text-destructive"
                              : "text-muted-foreground",
                          )}
                        >
                          {stats.safety_violations}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums text-muted-foreground">
                        {stats.avg_time_sec.toFixed(1)}s
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Summary row */}
            {metrics?.summary && (
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  {
                    label: "Completion",
                    value: pct(metrics.summary.completion_rate),
                    bad: metrics.summary.completion_rate < 0.8,
                  },
                  {
                    label: "Avg time",
                    value: `${metrics.summary.avg_time_sec.toFixed(1)}s`,
                    bad: false,
                  },
                  {
                    label: "Safety viol.",
                    value: String(metrics.summary.total_safety_violations),
                    bad: metrics.summary.total_safety_violations > 0,
                  },
                  {
                    label: "Obstacle stops",
                    value: String(metrics.summary.total_obstacle_interruptions),
                    bad: false,
                  },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="rounded-lg border border-border bg-muted/20 p-2 text-center"
                  >
                    <p className="text-[10px] text-muted-foreground">{item.label}</p>
                    <p
                      className={cn(
                        "font-mono text-sm font-bold tabular-nums",
                        item.bad ? "text-destructive" : "text-foreground",
                      )}
                    >
                      {item.value}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
