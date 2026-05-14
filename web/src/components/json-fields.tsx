import type { JsonValue } from "@/lib/types";

function formatValue(val: JsonValue): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "boolean") return val ? "Yes" : "No";
  if (typeof val === "number") return String(val);
  if (typeof val === "string") return val || "—";
  if (Array.isArray(val)) return val.map((v) => formatValue(v)).join(", ");
  return JSON.stringify(val);
}

function formatKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/^./, (c) => c.toUpperCase());
}

interface JsonFieldsProps {
  data: Record<string, JsonValue> | null | undefined;
  maxFields?: number;
}

export function JsonFields({ data, maxFields = 12 }: JsonFieldsProps) {
  if (!data || Object.keys(data).length === 0) {
    return <p className="text-xs text-muted-foreground">—</p>;
  }

  const entries = Object.entries(data).slice(0, maxFields);

  return (
    <dl className="grid gap-1.5">
      {entries.map(([key, val]) => {
        const isComplex = val !== null && typeof val === "object" && !Array.isArray(val);

        if (isComplex) {
          return (
            <div key={key}>
              <dt className="text-[11px] font-medium text-muted-foreground">{formatKey(key)}</dt>
              <dd className="mt-0.5 rounded-md bg-muted/50 p-2">
                <JsonFields data={val as Record<string, JsonValue>} maxFields={8} />
              </dd>
            </div>
          );
        }

        return (
          <div key={key} className="flex items-baseline justify-between gap-3">
            <dt className="shrink-0 text-[11px] text-muted-foreground">{formatKey(key)}</dt>
            <dd className="truncate text-right text-xs font-medium text-foreground">
              {formatValue(val)}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

interface PlanStepFieldsProps {
  step: Record<string, JsonValue>;
  index: number;
}

export function PlanStepFields({ step, index }: PlanStepFieldsProps) {
  const action = (step.action ?? step.type ?? step.name ?? step.func ?? null) as string | null;
  const target = (step.target ?? step.object ?? step.device ?? null) as string | null;
  const params = (step.params ?? step.args ?? step.kwargs ?? null) as Record<string, JsonValue> | null;
  const rest = Object.fromEntries(
    Object.entries(step).filter(
      ([k]) => !["action", "type", "name", "func", "target", "object", "device", "params", "args", "kwargs"].includes(k),
    ),
  );

  return (
    <div className="flex gap-2.5 rounded-lg border border-border bg-muted/30 p-2.5">
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-muted text-[10px] font-bold text-muted-foreground">
        {index + 1}
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        {action && (
          <p className="text-xs font-medium text-foreground">{action}</p>
        )}
        {target && (
          <p className="text-[11px] text-muted-foreground">Target: {target}</p>
        )}
        {params && Object.keys(params).length > 0 && (
          <div className="rounded-md bg-muted/50 p-1.5">
            <JsonFields data={params} maxFields={6} />
          </div>
        )}
        {Object.keys(rest).length > 0 && !action && (
          <JsonFields data={rest} maxFields={6} />
        )}
      </div>
    </div>
  );
}
