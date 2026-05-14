"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  connectRobot,
  disconnectRobot,
  executeCommand,
  fetchEvents,
  fetchHealth,
  fetchMetrics,
  fetchState,
  previewPlan,
  resetMetrics as apiResetMetrics,
} from "@/lib/api";
import {
  clearConnectSession,
  loadConnectSession,
  saveConnectSession,
} from "@/lib/connect-session";
import { loadExecCommandMode } from "@/lib/exec-command-mode";
import { getCommandAvailability } from "@/lib/command-availability";
import {
  labelCommandMode,
  type CommandMode,
  type EventItem,
  type HealthResponse,
  type MetricsResponse,
  type PlanResponse,
  type StateResponse,
} from "@/lib/types";

/** ~10 Hz for `/api/state`. */
const STATE_POLL_MS = 100;
/** Health + event log. */
const AUX_POLL_MS = 800;
/** Metrics (experiment comparison) — slower refresh. */
const METRICS_POLL_MS = 5000;

const MAX_EVENTS = 200;
const API_OFFLINE_AFTER_FAILURES = 10;
const POLL_SLOW_UI_MS = 450;

export function useRobot() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [state, setState] = useState<StateResponse | null>(null);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<number | null>(null);
  const [apiReachable, setApiReachable] = useState(true);

  const offsetRef = useRef(0);
  const mountedRef = useRef(true);
  const pollFailStreakRef = useRef(0);
  const loadingRef = useRef(false);
  const healthRef = useRef<HealthResponse | null>(null);
  const stateRef = useRef<StateResponse | null>(null);
  const apiReachableRef = useRef(true);
  const initialAutoConnectSentRef = useRef(false);
  const pollSlowUiTimerRef = useRef<ReturnType<typeof globalThis.setTimeout> | null>(null);

  loadingRef.current = loading;
  healthRef.current = health;
  stateRef.current = state;
  apiReachableRef.current = apiReachable;

  const isRobotConnected = useCallback(() => {
    const h = healthRef.current?.connected;
    const s = stateRef.current?.connected;
    return Boolean(h ?? s);
  }, []);

  const pollStateOnly = useCallback(async () => {
    try {
      const s = await fetchState();
      if (!mountedRef.current) return;
      setState(s);
      pollFailStreakRef.current = 0;
      setApiReachable(true);
      setLastSyncedAt(Date.now());
    } catch {
      if (!mountedRef.current) return;
      pollFailStreakRef.current += 1;
      if (pollFailStreakRef.current >= API_OFFLINE_AFTER_FAILURES) {
        setApiReachable(false);
      }
    }
  }, []);

  const pollHealthEvents = useCallback(async () => {
    pollSlowUiTimerRef.current = globalThis.setTimeout(() => {
      if (mountedRef.current) setPolling(true);
    }, POLL_SLOW_UI_MS);

    try {
      const [hr, er] = await Promise.allSettled([
        fetchHealth(),
        fetchEvents(offsetRef.current),
      ]);

      if (!mountedRef.current) return;

      const h = hr.status === "fulfilled" ? hr.value : null;
      const ev = er.status === "fulfilled" ? er.value : null;

      if (h) setHealth(h);
      if (ev && ev.events.length > 0) {
        offsetRef.current = ev.next_offset;
        setEvents((prev) => [...prev, ...ev.events].slice(-MAX_EVENTS));
      }
    } finally {
      if (pollSlowUiTimerRef.current != null) {
        globalThis.clearTimeout(pollSlowUiTimerRef.current);
        pollSlowUiTimerRef.current = null;
      }
      if (mountedRef.current) {
        setPolling(false);
      }
    }
  }, []);

  const refreshAfterSessionChange = useCallback(() => {
    void pollStateOnly();
    void pollHealthEvents();
  }, [pollStateOnly, pollHealthEvents]);

  // State poll loop (~10 Hz)
  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    const loop = async () => {
      while (!cancelled && mountedRef.current) {
        await pollStateOnly();
        if (cancelled) break;
        await new Promise<void>((r) => {
          globalThis.setTimeout(r, STATE_POLL_MS);
        });
      }
    };

    void loop();

    return () => {
      cancelled = true;
      mountedRef.current = false;
      if (pollSlowUiTimerRef.current != null) {
        globalThis.clearTimeout(pollSlowUiTimerRef.current);
        pollSlowUiTimerRef.current = null;
      }
    };
  }, [pollStateOnly]);

  // Health + events poll loop
  useEffect(() => {
    let cancelled = false;

    const loop = async () => {
      while (!cancelled && mountedRef.current) {
        await pollHealthEvents();
        if (cancelled) break;
        await new Promise<void>((r) => {
          globalThis.setTimeout(r, AUX_POLL_MS);
        });
      }
    };

    void loop();

    return () => {
      cancelled = true;
    };
  }, [pollHealthEvents]);

  // Metrics poll loop (slower — experiment dashboard)
  useEffect(() => {
    let cancelled = false;

    const loop = async () => {
      while (!cancelled && mountedRef.current) {
        try {
          const m = await fetchMetrics();
          if (mountedRef.current) setMetrics(m);
        } catch {
          /* metrics endpoint may not always be available */
        }
        if (cancelled) break;
        await new Promise<void>((r) => {
          globalThis.setTimeout(r, METRICS_POLL_MS);
        });
      }
    };

    void loop();

    return () => {
      cancelled = true;
    };
  }, []);

  const resetEvents = useCallback(() => {
    offsetRef.current = 0;
    setEvents([]);
  }, []);

  const connect = useCallback(
    async (serial_port: string | null, opts?: { silent?: boolean }) => {
      const command_mode = loadExecCommandMode();
      const silent = opts?.silent === true;
      let tid: string | number | undefined;
      if (!silent) {
        tid = toast.loading("Connecting…");
      }
      setLoading(true);
      try {
        const res = await connectRobot({ serial_port, command_mode });
        resetEvents();
        if (tid != null) toast.dismiss(tid);
        if (res.connected) {
          saveConnectSession({
            method: "real",
            serial: serial_port,
            command_mode,
            auto: true,
          });
          const modeLabel = labelCommandMode(res.command_mode ?? command_mode);
          if (!silent) {
            toast.success("Connected", { description: modeLabel });
          } else {
            toast.success("Reconnected", { description: modeLabel, duration: 2500 });
          }
          refreshAfterSessionChange();
        } else {
          if (!silent) toast.error("Connection failed", { description: res.error });
        }
        return res;
      } catch (err) {
        if (tid != null) toast.dismiss(tid);
        if (!silent) toast.error("Connection failed", { description: String(err) });
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [resetEvents, refreshAfterSessionChange],
  );

  const disconnect = useCallback(async () => {
    clearConnectSession();
    const tid = toast.loading("Disconnecting…");
    setLoading(true);
    try {
      await disconnectRobot();
      resetEvents();
      refreshAfterSessionChange();
      toast.dismiss(tid);
      toast.info("Disconnected");
    } catch (err) {
      toast.dismiss(tid);
      toast.error("Disconnect failed", { description: String(err) });
      throw err;
    } finally {
      setLoading(false);
    }
  }, [resetEvents, refreshAfterSessionChange]);

  /** One-shot after load: restore session once. */
  useEffect(() => {
    if (!apiReachable) return;
    if (initialAutoConnectSentRef.current) return;
    initialAutoConnectSentRef.current = true;

    const session = loadConnectSession();
    if (!session?.auto) return;

    const id = window.setTimeout(() => {
      if (!mountedRef.current || loadingRef.current) return;
      if (isRobotConnected()) return;
      void connect(session.serial, { silent: true }).catch(() => {
        /* user can press Connect */
      });
    }, 800);
    return () => window.clearTimeout(id);
  }, [apiReachable, connect, isRobotConnected]);

  const preview = useCallback(async (command: string, mode: CommandMode) => {
    const tid = toast.loading("Building plan…");
    setLoading(true);
    try {
      const res = await previewPlan(command, mode);
      setPlan(res);
      toast.dismiss(tid);
      toast.success("Plan generated", {
        description: `${res.plan.length} step(s) · ${labelCommandMode(mode)}`,
      });
      return res;
    } catch (err) {
      toast.dismiss(tid);
      toast.error("Plan preview failed", { description: String(err) });
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const execute = useCallback(async (command: string, mode: CommandMode) => {
    const { canSend, blockHint } = getCommandAvailability(
      apiReachableRef.current,
      healthRef.current,
      stateRef.current,
    );
    if (!canSend) {
      toast.error("Cannot send command", { description: blockHint || "Not available." });
      return;
    }

    const tid = toast.loading("Sending command…");
    setLoading(true);
    try {
      const res = await executeCommand(command, mode);
      toast.dismiss(tid);
      toast.success("Command sent", {
        description: `Server mode: ${res.mode} · ${labelCommandMode(mode)}`,
      });
      return res;
    } catch (err) {
      toast.dismiss(tid);
      toast.error("Execution failed", { description: String(err) });
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshMetrics = useCallback(async () => {
    try {
      const m = await fetchMetrics();
      if (mountedRef.current) setMetrics(m);
    } catch (err) {
      toast.error("Failed to load metrics", { description: String(err) });
    }
  }, []);

  const resetMetrics = useCallback(async () => {
    const tid = toast.loading("Resetting metrics…");
    try {
      await apiResetMetrics();
      toast.dismiss(tid);
      toast.success("Metrics reset");
      await refreshMetrics();
    } catch (err) {
      toast.dismiss(tid);
      toast.error("Reset failed", { description: String(err) });
      throw err;
    }
  }, [refreshMetrics]);

  const commandAvailability = useMemo(
    () => getCommandAvailability(apiReachable, health, state),
    [apiReachable, health, state],
  );

  return {
    health,
    state,
    plan,
    events,
    metrics,
    loading,
    polling,
    lastSyncedAt,
    apiReachable,
    commandAvailability,
    connect,
    disconnect,
    preview,
    execute,
    resetMetrics,
  };
}
