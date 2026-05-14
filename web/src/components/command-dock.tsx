"use client";

import { useEffect, useState } from "react";
import { ArrowUp, Eye, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { persistExecCommandMode, loadExecCommandMode } from "@/lib/exec-command-mode";
import { labelCommandMode, type CommandMode } from "@/lib/types";
import { cn } from "@/lib/utils";

const EXECUTION_MODES: { value: CommandMode; description: string }[] = [
  { value: "llm", description: "LLM (symbolic + safety)" },
  { value: "rules", description: "Rules (spaCy)" },
  { value: "direct", description: "Direct (baseline)" },
];

interface CommandDockProps {
  loading: boolean;
  hasWaitingTask: boolean;
  canSendCommands: boolean;
  commandBlockHint: string;
  onExecute: (cmd: string, mode: CommandMode) => Promise<void>;
  onPreview: (cmd: string, mode: CommandMode) => Promise<void>;
}

export function CommandDock({
  loading,
  hasWaitingTask,
  canSendCommands,
  commandBlockHint,
  onExecute,
  onPreview,
}: CommandDockProps) {
  const [command, setCommand] = useState("");
  const [execMode, setExecMode] = useState<CommandMode>("llm");
  const [hint, setHint] = useState("Enter a natural-language command for the robot.");

  useEffect(() => {
    setExecMode(loadExecCommandMode());
  }, []);

  const onModeChange = (next: CommandMode) => {
    setExecMode(next);
    persistExecCommandMode(next);
  };

  const trimmed = command.trim();
  const disabled = loading || !trimmed;
  const execDisabled = disabled || !canSendCommands;

  async function handleExecute() {
    if (execDisabled) return;
    try {
      await onExecute(trimmed, execMode);
      setCommand("");
      setHint(`Command sent (${labelCommandMode(execMode)}).`);
    } catch {
      setHint("Execution failed.");
    }
  }

  async function handlePreview() {
    if (disabled) return;
    try {
      await onPreview(trimmed, execMode);
      setHint(`Plan generated (${labelCommandMode(execMode)}) — see Plan Preview above.`);
    } catch {
      setHint("Preview failed.");
    }
  }

  const statusLine = loading
    ? "Working…"
    : !canSendCommands && commandBlockHint
      ? commandBlockHint
      : hasWaitingTask
        ? "Waiting task detected — command runs as manual assist."
        : hint;

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 flex justify-center px-3 pb-12 pt-8 pointer-events-none max-sm:pb-10">
      <div
        className={cn(
          "pointer-events-auto w-full max-w-[800px] rounded-xl border bg-card p-2 shadow-2xl transition-colors",
          loading ? "border-primary/40 ring-2 ring-primary/20" : "border-border",
          !canSendCommands && !loading && "opacity-90",
        )}
      >
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={execMode}
            onChange={(e) => onModeChange(e.target.value as CommandMode)}
            disabled={loading}
            aria-label="Command execution mode"
            className={cn(
              "h-12 min-w-[10.5rem] shrink-0 rounded-lg border border-input bg-muted/50 px-2.5 text-sm text-foreground outline-none transition-colors",
              "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
              "disabled:cursor-not-allowed disabled:opacity-50",
            )}
          >
            {EXECUTION_MODES.map((o) => (
              <option key={o.value} value={o.value}>
                {o.description}
              </option>
            ))}
          </select>

          <Input
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleExecute();
              }
            }}
            placeholder="e.g. move forward for 3 seconds, then turn right..."
            disabled={loading || !canSendCommands}
            className="h-12 min-w-[180px] flex-1 rounded-lg border-transparent bg-muted/50 px-3.5 text-sm placeholder:text-muted-foreground focus-visible:border-ring"
          />

          <Button
            variant="outline"
            disabled={disabled}
            onClick={() => void handlePreview()}
            title="Preview plan without executing"
            className="shrink-0"
          >
            {loading ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Eye className="size-3.5" />
            )}
            Preview
          </Button>

          <Button
            disabled={execDisabled}
            onClick={() => void handleExecute()}
            className="shrink-0"
          >
            {loading ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <ArrowUp className="size-3.5" />
            )}
            Send
          </Button>
        </div>

        <p
          className={cn(
            "mt-1 px-1 text-[11px]",
            !canSendCommands && !loading
              ? "text-amber-600 dark:text-amber-500"
              : "text-muted-foreground",
          )}
        >
          {statusLine}
        </p>
      </div>
    </div>
  );
}
