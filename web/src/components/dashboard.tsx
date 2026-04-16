"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import {
  connectRobot,
  disconnectRobot,
  executeCommand,
  fetchEvents,
  fetchHealth,
  fetchState,
  getApiBaseUrl,
  previewPlan,
} from "@/lib/api";
import type { EventItem, HealthResponse, PlanResponse, StateResponse } from "@/lib/types";

function stringify(data: unknown) {
  return JSON.stringify(data, null, 2);
}

function shortText(data: unknown, maxLength = 180) {
  const text = typeof data === "string" ? data : JSON.stringify(data);
  if (!text) return "-";
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

export function Dashboard() {
  const { push } = useToast();
  const [method, setMethod] = useState<"real" | "sim">("real");
  const [serialPort, setSerialPort] = useState("");
  const [command, setCommand] = useState("");

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [state, setState] = useState<StateResponse | null>(null);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventOffset, setEventOffset] = useState(0);
  const [connectHint, setConnectHint] = useState("");
  const [assistHint, setAssistHint] = useState("Commands are sent in task mode unless a waiting task exists.");

  async function refresh() {
    const [nextHealth, nextState, nextEvents] = await Promise.all([
      fetchHealth(),
      fetchState(),
      fetchEvents(eventOffset),
    ]);

    setHealth(nextHealth);
    setState(nextState);

    if (nextEvents.events.length > 0) {
      setEventOffset(nextEvents.next_offset);
      setEvents((prev) => [...prev, ...nextEvents.events].slice(-200));
    }
  }

  useEffect(() => {
    void refresh().catch((error) => {
      push({ title: "Live update failed", description: String(error), variant: "error" });
    });
    const interval = window.setInterval(() => {
      void refresh().catch(() => null);
    }, 1000);
    return () => window.clearInterval(interval);
  }, [eventOffset, push]);

  const statCards = useMemo(
    () => [
      { label: "Connection", value: health?.connected ? "Online" : "Offline" },
      { label: "Runtime", value: health?.ready ? "Ready" : "Not Ready" },
      { label: "Execution", value: health?.busy ? "Busy" : "Idle" },
      { label: "Mode", value: health?.method ?? "-" },
    ],
    [health]
  );

  return (
    <main className="mx-auto grid w-full max-w-6xl gap-3 px-4 pb-36 pt-6">
      <Card className="text-center">
        <Badge className="mx-auto mb-3">Neural-style Robot Console</Badge>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-100">AI Robot Control Panel</h1>
        <p className="mt-2 text-sm text-slate-400">FastAPI: {getApiBaseUrl()}</p>
      </Card>

      <Card>
        <CardTitle>Connection</CardTitle>
        <CardDescription>Connect robot hardware or simulation runtime.</CardDescription>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Select value={method} onChange={(event) => setMethod(event.target.value as "real" | "sim")}>
            <option value="real">Real Robot</option>
            <option value="sim">Simulation</option>
          </Select>
          <Input
            value={serialPort}
            onChange={(event) => setSerialPort(event.target.value)}
            placeholder="Serial port (optional, e.g. /dev/ttyUSB0)"
            className="min-w-[220px] flex-1"
          />
          <Button
            onClick={async () => {
              try {
                const response = await connectRobot(method, serialPort.trim() || null);
                setEventOffset(0);
                setEvents([]);
                setConnectHint(response.connected ? `Connected via ${response.method}` : `Connect failed: ${response.error}`);
                push({
                  title: response.connected ? "Connected" : "Connection failed",
                  description: response.connected ? `Mode: ${response.method}` : response.error,
                  variant: response.connected ? "success" : "error",
                });
              } catch (error) {
                const message = String(error);
                setConnectHint(message);
                push({ title: "Connection failed", description: message, variant: "error" });
              }
            }}
          >
            Connect
          </Button>
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                await disconnectRobot();
                setEventOffset(0);
                setEvents([]);
                setConnectHint("Disconnected");
                push({ title: "Disconnected", variant: "info" });
              } catch (error) {
                push({ title: "Disconnect failed", description: String(error), variant: "error" });
              }
            }}
          >
            Disconnect
          </Button>
        </div>
        {connectHint ? <p className="mt-2 text-xs text-slate-400">{connectHint}</p> : null}
      </Card>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {statCards.map((item) => (
          <Card key={item.label}>
            <p className="text-xs text-slate-400">{item.label}</p>
            <p className="mt-1 text-xl font-semibold text-slate-100">{item.value}</p>
          </Card>
        ))}
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <Card>
          <CardTitle>Plan Preview</CardTitle>
          <CardDescription>Command interpretation and action steps.</CardDescription>
          <div className="mt-3 flex gap-2">
            <Badge variant={plan?.manual_assist_mode ? "warning" : "success"}>
              {plan?.manual_assist_mode ? "Manual Assist Mode" : "Task Mode"}
            </Badge>
            <Badge variant="info">{plan?.plan.length ?? 0} step(s)</Badge>
          </div>
          <ul className="mt-3 grid max-h-72 gap-2 overflow-auto">
            {(plan?.plan ?? []).length === 0 ? (
              <li className="rounded-lg border border-slate-700 bg-slate-950/50 p-2 text-xs text-slate-500">No plan yet.</li>
            ) : (
              plan?.plan.map((step, index) => (
                <li key={index} className="rounded-lg border border-slate-700 bg-slate-950/50 p-2 text-xs text-slate-200">
                  <p className="font-medium text-slate-300">Step {index + 1}</p>
                  <p className="mt-1">{shortText(step)}</p>
                </li>
              ))
            )}
          </ul>
        </Card>

        <Card>
          <CardTitle>Tasks</CardTitle>
          <CardDescription>Compact active/waiting task widgets.</CardDescription>
          <div className="mt-3 grid gap-2">
            <div className="rounded-lg border border-slate-700 bg-slate-950/50 p-2 text-xs">
              <p className="font-medium text-slate-300">Active Task</p>
              <p className="mt-1 text-slate-400">{state?.active_task ? shortText(state.active_task) : "none"}</p>
            </div>
            <div className="rounded-lg border border-slate-700 bg-slate-950/50 p-2 text-xs">
              <p className="font-medium text-slate-300">Waiting Task</p>
              <p className="mt-1 text-slate-400">{state?.waiting_task ? shortText(state.waiting_task) : "none"}</p>
            </div>
          </div>
        </Card>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <Card>
          <CardTitle>Runtime Snapshot</CardTitle>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant={health?.connected ? "success" : "destructive"}>connected: {String(health?.connected ?? false)}</Badge>
            <Badge variant={health?.ready ? "success" : "warning"}>ready: {String(health?.ready ?? false)}</Badge>
            <Badge variant={health?.busy ? "warning" : "success"}>busy: {String(health?.busy ?? false)}</Badge>
            <Badge>method: {health?.method ?? "-"}</Badge>
          </div>
          <details className="mt-3 rounded-lg border border-slate-700 bg-slate-950/50">
            <summary className="cursor-pointer px-3 py-2 text-xs text-slate-400">Detailed Runtime JSON</summary>
            <pre className="max-h-64 overflow-auto border-t border-slate-700 p-3 text-xs text-slate-300">
              {stringify({
                runtime_status: state?.runtime_status ?? null,
                world: state?.world ?? null,
                last_error: state?.last_error ?? null,
                last_plan_command: state?.last_plan_command ?? null,
              })}
            </pre>
          </details>
        </Card>

        <Card>
          <CardTitle>Event Timeline</CardTitle>
          <CardDescription>Latest 200 events.</CardDescription>
          <ul className="mt-3 grid max-h-80 gap-2 overflow-auto">
            {events.length === 0 ? (
              <li className="rounded-lg border border-slate-700 bg-slate-950/50 p-2 text-xs text-slate-500">No events yet.</li>
            ) : (
              [...events].reverse().map((event, index) => (
                <li key={index} className="rounded-lg border border-slate-700 bg-slate-950/50 p-2 text-xs text-slate-200">
                  <p className="font-medium text-slate-300">{event.type ?? event.name ?? "event"}</p>
                  <p className="mt-1 text-slate-400">{shortText(event.payload ?? event)}</p>
                </li>
              ))
            )}
          </ul>
        </Card>
      </section>

      <div className="fixed bottom-4 left-1/2 z-30 w-[min(860px,calc(100vw-1rem))] -translate-x-1/2 rounded-2xl border border-slate-700 bg-slate-950/90 p-2 shadow-2xl backdrop-blur">
        <div className="flex items-center gap-2">
          <Input
            value={command}
            onChange={(event) => setCommand(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void (async () => {
                  if (!command.trim()) {
                    push({ title: "Command is empty", variant: "error" });
                    return;
                  }
                  try {
                    const response = await executeCommand(command.trim());
                    setAssistHint(`Accepted (${response.mode})`);
                    push({ title: "Command accepted", description: response.mode, variant: "success" });
                    setCommand("");
                  } catch (error) {
                    const message = String(error);
                    setAssistHint(`Execute failed: ${message}`);
                    push({ title: "Execute failed", description: message, variant: "error" });
                  }
                })();
              }
            }}
            placeholder="Type command, e.g. go forward then turn right"
            className="h-11 rounded-xl"
          />
          <Button
            variant="ghost"
            onClick={async () => {
              if (!command.trim()) {
                push({ title: "Command is empty", variant: "error" });
                return;
              }
              try {
                const response = await previewPlan(command.trim());
                setPlan(response);
                setAssistHint(
                  response.manual_assist_mode
                    ? "Waiting task exists: command will run as manual assist."
                    : "No waiting task: command will run as a new task."
                );
                push({ title: "Plan updated", variant: "success" });
              } catch (error) {
                push({ title: "Plan preview failed", description: String(error), variant: "error" });
              }
            }}
          >
            Preview
          </Button>
          <Button
            onClick={async () => {
              if (!command.trim()) {
                push({ title: "Command is empty", variant: "error" });
                return;
              }
              try {
                const response = await executeCommand(command.trim());
                setAssistHint(`Accepted (${response.mode})`);
                push({ title: "Command accepted", description: response.mode, variant: "success" });
                setCommand("");
              } catch (error) {
                const message = String(error);
                setAssistHint(`Execute failed: ${message}`);
                push({ title: "Execute failed", description: message, variant: "error" });
              }
            }}
          >
            Send
          </Button>
        </div>
        <p className="mt-2 px-1 text-xs text-slate-500">{assistHint}</p>
      </div>
    </main>
  );
}
