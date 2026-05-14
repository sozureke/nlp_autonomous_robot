import { ScrollText } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { EventItem } from "@/lib/types";

function formatPayload(data: unknown, maxLen = 100): string {
  if (data === undefined || data === null) return "";
  const text = typeof data === "string" ? data : JSON.stringify(data);
  return text.length > maxLen ? `${text.slice(0, maxLen)}...` : text;
}

interface EventTimelineProps {
  events: EventItem[];
}

export function EventTimeline({ events }: EventTimelineProps) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <ScrollText className="size-3.5 text-muted-foreground" />
          Event Timeline
        </CardTitle>
        <CardDescription>Latest {events.length} events</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="max-h-64 space-y-px overflow-auto">
          {events.length === 0 ? (
            <p className="py-4 text-center text-xs text-muted-foreground">No events yet</p>
          ) : (
            [...events].reverse().map((event, i) => {
              const label = event.type ?? event.name ?? "event";
              const detail = formatPayload(event.payload ?? event);
              return (
                <div
                  key={i}
                  className="flex items-start gap-2.5 rounded-md px-2 py-1.5 hover:bg-muted/40 transition-colors"
                >
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-neutral-600" />
                  <div className="min-w-0 flex-1">
                    <span className="text-xs font-medium">{label}</span>
                    {detail && (
                      <p className="truncate text-[11px] text-muted-foreground">{detail}</p>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
