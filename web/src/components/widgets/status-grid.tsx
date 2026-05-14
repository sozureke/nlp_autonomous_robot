import { Wifi, WifiOff, Activity, Cpu, Settings } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { labelCommandMode, type HealthResponse, type StateResponse } from "@/lib/types";

interface StatusGridProps {
  health: HealthResponse | null;
  state: StateResponse | null;
}

function runtimeLabel(health: HealthResponse | null): string {
  if (health == null) return "—";
  if (health.ready === true) return "Ready";
  if (health.ready === false) return "Not Ready";
  return "Unknown";
}

export function StatusGrid({ health, state }: StatusGridProps) {
  const connected = health?.connected ?? state?.connected ?? false;
  const runtimeValue = runtimeLabel(health);
  const readyPositive = health?.ready === true;

  const items = [
    {
      label: "Connection",
      value: connected ? "Online" : "Offline",
      icon: connected ? Wifi : WifiOff,
      active: connected,
    },
    {
      label: "Runtime",
      value: runtimeValue,
      icon: Activity,
      active: readyPositive,
    },
    {
      label: "Execution",
      value: health?.busy ? "Busy" : "Idle",
      icon: Cpu,
      active: !(health?.busy ?? false),
      pulse: health?.busy ?? false,
    },
    {
      label: "Command mode",
      value: labelCommandMode(health?.command_mode ?? state?.command_mode ?? undefined),
      icon: Settings,
      active: !!(health?.command_mode ?? state?.command_mode),
    },
  ];

  return (
    <section className="grid grid-cols-2 gap-2 xl:grid-cols-4">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <Card key={item.label} size="sm" className="py-2.5">
            <CardContent className="flex items-center gap-3">
              <Icon className="size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0">
                <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
                  {item.label}
                </p>
                <div className="flex items-center gap-1.5">
                  <span
                    className={cn(
                      "size-1.5 rounded-full",
                      item.active ? "bg-emerald-500" : "bg-neutral-600",
                      "pulse" in item && item.pulse && "animate-pulse",
                    )}
                  />
                  <p className="truncate text-sm font-medium">{item.value}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </section>
  );
}
