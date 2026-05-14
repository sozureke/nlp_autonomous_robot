import { Play, Pause } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { JsonFields } from "@/components/json-fields";
import type { JsonValue } from "@/lib/types";

interface TasksCardProps {
  activeTask: Record<string, JsonValue> | null;
  waitingTask: Record<string, JsonValue> | null;
}

export function TasksCard({ activeTask, waitingTask }: TasksCardProps) {
  return (
    <Card size="sm" className="flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Play className="size-3.5 text-muted-foreground" />
          Tasks
        </CardTitle>
        <CardDescription>Active and waiting tasks</CardDescription>
      </CardHeader>
      <CardContent className="flex-1 space-y-2">
        <div className="rounded-lg border border-border bg-muted/30 p-2.5">
          <div className="mb-1.5 flex items-center gap-1.5">
            <Play className="size-3 text-emerald-500" />
            <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              Active
            </span>
          </div>
          {activeTask ? (
            <JsonFields data={activeTask} />
          ) : (
            <p className="text-xs text-muted-foreground">No active task</p>
          )}
        </div>

        <div className="rounded-lg border border-border bg-muted/30 p-2.5">
          <div className="mb-1.5 flex items-center gap-1.5">
            <Pause className="size-3 text-amber-500" />
            <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              Waiting
            </span>
          </div>
          {waitingTask ? (
            <JsonFields data={waitingTask} />
          ) : (
            <p className="text-xs text-muted-foreground">No waiting task</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
