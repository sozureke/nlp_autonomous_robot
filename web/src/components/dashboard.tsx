"use client";

import { CommandDock } from "@/components/command-dock";
import { GlobalActivityBar } from "@/components/global-activity-bar";
import { SyncStatus } from "@/components/sync-status";
import { ConnectionCard } from "@/components/widgets/connection-card";
import { EventTimeline } from "@/components/widgets/event-timeline";
import { ExecutionProgressCard } from "@/components/widgets/execution-progress-card";
import { MetricsCard } from "@/components/widgets/metrics-card";
import { PlanPreview } from "@/components/widgets/plan-preview";
import { RuntimeCard } from "@/components/widgets/runtime-card";
import { SensorsCard } from "@/components/widgets/sensors-card";
import { StatusGrid } from "@/components/widgets/status-grid";
import { useRobot } from "@/hooks/use-robot";

export function Dashboard() {
  const {
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
    execute,
    preview,
    resetMetrics,
  } = useRobot();

  const connected = health?.connected ?? state?.connected ?? false;

  return (
    <>
      <GlobalActivityBar active={loading} />

      <main className="mx-auto grid w-full max-w-5xl gap-2 px-3 pb-48 pt-4 sm:px-4">
        <div className="mb-1 flex justify-center">
          <SyncStatus polling={polling} lastSyncedAt={lastSyncedAt} apiReachable={apiReachable} />
        </div>

        <ConnectionCard
          connected={connected}
          loading={loading}
          activeCommandMode={health?.command_mode ?? state?.command_mode}
          onConnect={(serial) => connect(serial)}
          onDisconnect={disconnect}
        />

        <StatusGrid health={health} state={state} />

        {/* Execution progress — always shown so layout is stable */}
        <ExecutionProgressCard
          activeTask={state?.active_task ?? null}
          waitingTask={state?.waiting_task ?? null}
          busy={state?.busy ?? false}
        />

        {/* Sensors + Plan Preview side by side */}
        <section className="grid gap-2 md:grid-cols-2">
          <SensorsCard
            world={state?.world ?? null}
            connected={connected}
            lastUpdatedAt={lastSyncedAt}
          />
          <PlanPreview plan={plan} />
        </section>

        {/* Experiment metrics */}
        <MetricsCard metrics={metrics} onReset={resetMetrics} />

        {/* Runtime details + event log */}
        <section className="grid gap-2 md:grid-cols-2">
          <RuntimeCard health={health} state={state} />
          <EventTimeline events={events} />
        </section>

        <CommandDock
          loading={loading}
          hasWaitingTask={state?.waiting_task != null}
          canSendCommands={commandAvailability.canSend}
          commandBlockHint={commandAvailability.blockHint}
          onExecute={async (cmd, mode) => { await execute(cmd, mode); }}
          onPreview={async (cmd, mode) => { await preview(cmd, mode); }}
        />
      </main>
    </>
  );
}
