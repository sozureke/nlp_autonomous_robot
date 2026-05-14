import { useEffect, useState } from "react";
import { Radar, TriangleAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { JsonValue } from "@/lib/types";

function asNum(v: JsonValue | undefined): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function asBool(v: JsonValue | undefined): boolean {
  return v === true || v === 1 || v === "true";
}

interface SensorsCardProps {
  world: Record<string, JsonValue> | null;
  connected: boolean;
  lastUpdatedAt: number | null;
}

function formatSensorAge(lastUpdatedAt: number | null): string {
  if (lastUpdatedAt == null) return "no updates yet";
  const ms = Math.max(0, Date.now() - lastUpdatedAt);
  if (ms < 1000) return `${ms} ms ago`;
  const s = ms / 1000;
  return `${s.toFixed(1)} s ago`;
}

export function SensorsCard({ world, connected, lastUpdatedAt }: SensorsCardProps) {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => tick((n) => n + 1), 250);
    return () => window.clearInterval(id);
  }, []);

  const sensors = world?.sensors as Record<string, JsonValue> | null | undefined;
  const derived = world?.derived as Record<string, JsonValue> | null | undefined;

  const distanceFront = asNum(sensors?.distance_front);
  const obstacleLeft = asBool(sensors?.obstacle_left);
  const obstacleRight = asBool(sensors?.obstacle_right);
  const obstacle =
    derived?.obstacle !== undefined
      ? asBool(derived.obstacle)
      : obstacleLeft || obstacleRight;

  const maxDist = 2.0;
  const distPct =
    distanceFront !== null
      ? Math.min(100, (distanceFront / maxDist) * 100)
      : null;

  const distColor =
    distanceFront === null
      ? "text-foreground"
      : distanceFront < 0.3
        ? "text-destructive"
        : distanceFront < 0.6
          ? "text-amber-400"
          : "text-foreground";

  const barColor =
    distanceFront === null
      ? "bg-muted-foreground"
      : distanceFront < 0.3
        ? "bg-destructive"
        : distanceFront < 0.6
          ? "bg-amber-500"
          : "bg-emerald-500";

  return (
    <Card size="sm">
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Radar
            className={cn(
              "size-3.5",
              connected && obstacle
                ? "animate-pulse text-destructive"
                : "text-muted-foreground",
            )}
          />
          Sensors
        </CardTitle>
        <span className="text-[10px] font-mono text-muted-foreground">
          Updated {formatSensorAge(lastUpdatedAt)}
        </span>
      </CardHeader>

      <CardContent className="space-y-3">
        {!connected || !world ? (
          <p className="text-xs text-muted-foreground">
            {connected ? "No sensor data" : "Connect the robot to see sensors."}
          </p>
        ) : (
          <>
            {/* Distance front */}
            <div className="space-y-1.5">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
                Distance front
              </p>
              <div className="flex items-end gap-2">
                <span
                  className={cn(
                    "text-2xl font-mono font-bold tabular-nums leading-none",
                    distColor,
                  )}
                >
                  {distanceFront !== null ? distanceFront.toFixed(2) : "—"}
                </span>
                <span className="mb-0.5 text-[11px] text-muted-foreground">m</span>
              </div>
              {distPct !== null && (
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn("h-full rounded-full transition-all duration-300", barColor)}
                    style={{ width: `${distPct.toFixed(0)}%` }}
                  />
                </div>
              )}
            </div>

            {/* Obstacle status — single indicator */}
            <div
              className={cn(
                "flex items-center gap-2 rounded-lg border px-3 py-2 transition-colors",
                obstacle
                  ? "border-destructive/50 bg-destructive/10"
                  : "border-border bg-muted/20",
              )}
            >
              <TriangleAlert
                className={cn(
                  "size-3.5 shrink-0",
                  obstacle ? "text-destructive" : "text-muted-foreground",
                )}
              />
              <span
                className={cn(
                  "text-xs font-medium",
                  obstacle ? "text-destructive" : "text-muted-foreground",
                )}
              >
                {obstacle ? "Obstacle detected" : "Path clear"}
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
