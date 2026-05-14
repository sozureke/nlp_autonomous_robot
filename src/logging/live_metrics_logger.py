from __future__ import annotations

import argparse
import csv
import json
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunRecord:
    timestamp: str
    segment: int
    canonical_id: str
    command: str
    mode: str
    status: str
    steps: int
    error: str
    plan_source: str
    plan_message: str
    executor: str
    runtime_status: str
    safety_violations: str


class LiveLogger:
    def __init__(self, *, base_url: str, poll_interval: float, out_dir: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.out_dir = out_dir
        self.raw_dir = out_dir / "raw"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self._stop = False
        self.offset = 0
        self.segment = 1
        self.prev_total_commands: Optional[int] = None
        self.command_keys: Dict[str, str] = {}
        self.records: List[RunRecord] = []
        """Latest command_plan_ready payload for merge into the run row."""
        self._last_plan_trace: Optional[Dict[str, Any]] = None

        self.events_jsonl = out_dir / "events.jsonl"

    def stop(self, *_: Any) -> None:
        self._stop = True

    def run(self) -> None:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        print(f"[logger] output: {self.out_dir}")
        print(f"[logger] polling {self.base_url} every {self.poll_interval:.1f}s")
        while not self._stop:
            try:
                self._tick()
            except Exception as exc:
                print(f"[logger] tick error: {exc}")
            time.sleep(self.poll_interval)

        self._write_outputs()
        print("[logger] stopped")

    def _append_events_jsonl(self, events_batch: List[Dict[str, Any]]) -> None:
        if not events_batch:
            return
        with self.events_jsonl.open("a", encoding="utf-8") as f:
            for ev in events_batch:
                line = json.dumps({"received_at": utc_now(), "event": ev}, ensure_ascii=False)
                f.write(line + "\n")

    def _tick(self) -> None:
        metrics_resp = requests.get(f"{self.base_url}/api/metrics", timeout=5)
        metrics_resp.raise_for_status()
        metrics_payload = metrics_resp.json()
        metrics = metrics_payload.get("metrics") or {}

        total_commands = int(metrics.get("total_commands", 0))
        if self.prev_total_commands is not None and total_commands < self.prev_total_commands:
            self.segment += 1
            self._last_plan_trace = None
            print(f"[logger] detected metrics reset -> segment {self.segment}")
        self.prev_total_commands = total_commands

        events_resp = requests.get(
            f"{self.base_url}/api/events",
            params={"offset": self.offset, "limit": 500},
            timeout=5,
        )
        events_resp.raise_for_status()
        events_payload = events_resp.json()
        events = events_payload.get("events", [])
        self.offset = int(events_payload.get("next_offset", self.offset))

        self._append_events_jsonl(events)

        for ev in events:
            self._consume_event(ev)

        snapshot = {
            "timestamp": utc_now(),
            "segment": self.segment,
            "offset": self.offset,
            "metrics": metrics,
        }
        latest_path = self.raw_dir / f"segment_{self.segment}_latest.json"
        latest_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    def _trace_key(self, command: str, mode: str) -> str:
        return f"{mode.strip().lower()}::{command.strip().lower()}"

    def _record_run(
        self,
        *,
        command: str,
        mode: str,
        status: str,
        steps: int,
        error: str,
        plan_source: str,
        plan_message: str,
        executor: str,
        runtime_status: str,
        safety_violations: str,
    ) -> None:
        key = self._trace_key(command, mode)
        canonical_id = self._canonical_id(key)
        self.records.append(
            RunRecord(
                timestamp=utc_now(),
                segment=self.segment,
                canonical_id=canonical_id,
                command=command,
                mode=mode,
                status=status,
                steps=steps,
                error=error,
                plan_source=plan_source,
                plan_message=plan_message,
                executor=executor,
                runtime_status=runtime_status,
                safety_violations=safety_violations,
            )
        )

    def _consume_event(self, event: Dict[str, Any]) -> None:
        ev_type = event.get("type")
        name = event.get("name")
        payload = event.get("payload") or {}
        if ev_type != "action":
            return

        if name == "command_plan_ready":
            self._last_plan_trace = dict(payload)
            return

        if name == "llm_plan" and self._last_plan_trace is None:
            self._last_plan_trace = {
                "command": payload.get("command"),
                "execution_mode": payload.get("mode", "llm"),
                "plan_source": payload.get("plan_source", ""),
                "plan_message": "",
                "step_count": len(payload.get("steps") or []) if isinstance(payload.get("steps"), list) else 0,
            }

        if name == "execution_finished":
            command = str(payload.get("command", "")).strip()
            if not command:
                return
            mode = str(payload.get("execution_mode", "llm")).strip().lower() or "llm"
            trace = self._last_plan_trace or {}
            same_cmd = str(trace.get("command", "")).strip() == command
            same_mode = str(trace.get("execution_mode", "")).strip().lower() == mode
            ps = str(trace.get("plan_source", "") if same_cmd and same_mode else "")
            pm = str(trace.get("plan_message", "") if same_cmd and same_mode else "")
            steps = trace.get("step_count") if same_cmd and same_mode else None
            if steps is None and same_cmd and same_mode:
                steps = len(trace.get("steps") or []) if isinstance(trace.get("steps"), list) else 0
            if steps is None:
                steps = 0

            executor = str(payload.get("executor", ""))
            rs = str(payload.get("runtime_status", ""))
            safety = ""
            if executor == "direct_executor":
                dr = payload.get("direct_result") or {}
                safety = str(dr.get("safety_violations", ""))
                if not rs and isinstance(dr.get("success"), bool):
                    rs = "completed" if dr.get("success") else "failed"

            row_status = rs or "unknown"

            self._record_run(
                command=command,
                mode=mode,
                status=row_status,
                steps=int(steps) if steps is not None else 0,
                error="",
                plan_source=ps,
                plan_message=pm,
                executor=executor,
                runtime_status=rs,
                safety_violations=safety,
            )
            self._last_plan_trace = None
            return

        if name == "ui_no_plan":
            command = str(payload.get("command", "")).strip()
            if not command:
                return
            mode = str(payload.get("execution_mode", "llm")).strip().lower() or "llm"
            self._record_run(
                command=command,
                mode=mode,
                status="failed",
                steps=0,
                error="no_plan",
                plan_source=str(payload.get("plan_source", "")),
                plan_message=str(payload.get("plan_message", "")),
                executor="",
                runtime_status="",
                safety_violations="",
            )
            self._last_plan_trace = None
            return

        if name == "ui_execution_error":
            command = str(payload.get("command", "")).strip()
            if not command:
                return
            trace = self._last_plan_trace or {}
            mode = str(trace.get("execution_mode", "llm")).strip().lower() or "llm"
            if str(trace.get("command", "")).strip() != command:
                mode = "llm"
            ps = str(trace.get("plan_source", ""))
            pm = str(trace.get("plan_message", ""))
            steps = trace.get("step_count", 0)
            try:
                steps_i = int(steps)
            except (TypeError, ValueError):
                steps_i = len(trace.get("steps") or []) if isinstance(trace.get("steps"), list) else 0
            self._record_run(
                command=command,
                mode=mode,
                status="failed",
                steps=steps_i,
                error=str(payload.get("error", "")),
                plan_source=ps,
                plan_message=pm,
                executor="",
                runtime_status="",
                safety_violations="",
            )
            self._last_plan_trace = None
            return

    def _canonical_id(self, key: str) -> str:
        if key in self.command_keys:
            return self.command_keys[key]
        new_id = f"CMD{len(self.command_keys) + 1:03d}"
        self.command_keys[key] = new_id
        return new_id

    def _write_outputs(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "created_at": utc_now(),
            "base_url": self.base_url,
            "poll_interval": self.poll_interval,
            "records": len(self.records),
            "segments": self.segment,
        }
        (self.out_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        csv_path = self.out_dir / "per_command.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp_utc",
                    "segment",
                    "canonical_id",
                    "command",
                    "mode",
                    "status",
                    "steps",
                    "error",
                    "plan_source",
                    "plan_message",
                    "executor",
                    "runtime_status",
                    "safety_violations",
                ]
            )
            for r in self.records:
                writer.writerow(
                    [
                        r.timestamp,
                        r.segment,
                        r.canonical_id,
                        r.command,
                        r.mode,
                        r.status,
                        r.steps,
                        r.error,
                        r.plan_source,
                        r.plan_message,
                        r.executor,
                        r.runtime_status,
                        r.safety_violations,
                    ]
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll /api/events and write session logs (CSV + JSONL)")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--output-dir", default="", help="Default: ./results/live_session_<timestamp>")
    args = parser.parse_args()

    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("results") / f"live_session_{stamp}"

    logger = LiveLogger(
        base_url=args.base_url,
        poll_interval=max(0.2, float(args.poll_interval)),
        out_dir=out_dir,
    )
    logger.run()


if __name__ == "__main__":
    main()
