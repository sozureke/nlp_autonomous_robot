import { ListChecks } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PlanStepFields } from "@/components/json-fields";
import type { PlanResponse } from "@/lib/types";

interface PlanPreviewProps {
  plan: PlanResponse | null;
}

export function PlanPreview({ plan }: PlanPreviewProps) {
  const steps = plan?.plan ?? [];
  const source =
    plan?.source != null && String(plan.source).trim()
      ? String(plan.source)
      : plan?.planning?.source != null
        ? String(plan.planning.source)
        : null;
  const planMsg =
    plan?.message != null && String(plan.message).trim()
      ? String(plan.message)
      : plan?.planning?.message != null
        ? String(plan.planning.message)
        : null;
  const planMode = plan?.mode != null && String(plan.mode).trim() ? String(plan.mode) : null;

  return (
    <Card size="sm" className="flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <ListChecks className="size-3.5 text-muted-foreground" />
          Plan Preview
        </CardTitle>
        <CardDescription>
          <span className="inline-flex flex-wrap items-center gap-1.5">
            {plan?.manual_assist_mode != null && (
              <Badge variant="secondary" className="text-[10px]">
                {plan.manual_assist_mode ? "Manual Assist" : "Task Mode"}
              </Badge>
            )}
            {planMode && (
              <Badge variant="outline" className="text-[10px] font-mono">
                {planMode}
              </Badge>
            )}
            {source && (
              <Badge variant="outline" className="text-[10px] font-mono">
                {source}
              </Badge>
            )}
            <Badge variant="outline" className="text-[10px]">
              {steps.length} step{steps.length !== 1 ? "s" : ""}
            </Badge>
          </span>
          {planMsg && (
            <p className="mt-1 text-[11px] text-muted-foreground/80">{planMsg}</p>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1">
        <div className="max-h-64 space-y-1.5 overflow-auto">
          {steps.length === 0 ? (
            <p className="py-4 text-center text-xs text-muted-foreground">
              No plan yet — use Preview to generate
            </p>
          ) : (
            steps.map((step, i) => <PlanStepFields key={i} step={step} index={i} />)
          )}
        </div>
      </CardContent>
    </Card>
  );
}
