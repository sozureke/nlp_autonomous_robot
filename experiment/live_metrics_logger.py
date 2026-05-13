from __future__ import annotations

import argparse
import csv
import json
import signal
import sys
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


class LiveLogger:
    def __init__(self, *, base_url: str, poll_interval: float, out_dir: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.out_dir = out_dir
        self.raw_dir = out_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self._stop = False
        self.offset = 0
        self.segment = 1
        self.prev_total_commands: Optional[int] = None
        self.command_keys: Dict[str, str] = {}
        self.pending: Dict[str, Dict[str, Any]] = {}
        self.records: List[RunRecord] = []

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

    def _tick(self) -> None:
        metrics_resp = requests.get(f"{self.base_url}/api/metrics", timeout=5)
        metrics_resp.raise_for_status()
        metrics_payload = metrics_resp.json()
        metrics = metrics_payload.get("metrics") or {}

        total_commands = int(metrics.get("total_commands", 0))
        if self.prev_total_commands is not None and total_commands < self.prev_total_commands:
            self.segment += 1
            self.pending.clear()
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

    def _consume_event(self, event: Dict[str, Any]) -> None:
        ev_type = event.get("type")
        name = event.get("name")
        payload = event.get("payload") or {}
        if ev_type != "action":
            return

        if name == "llm_plan":
            command = str(payload.get("command", "")).strip()
            if not command:
                return
            mode = str(payload.get("mode", "llm")).strip().lower() or "llm"
            steps = payload.get("steps", [])
            self.pending[command] = {
                "command": command,
                "mode": mode,
                "steps": len(steps) if isinstance(steps, list) else 0,
            }
            return

        if name in ("task_completed", "task_stopped_obstacle", "ui_execution_error"):
            command = str(payload.get("task") or payload.get("command") or "").strip()
            if not command:
                return
            base = self.pending.pop(command, {"command": command, "mode": "llm", "steps": 0})
            status_map = {
                "task_completed": "completed",
                "task_stopped_obstacle": "interrupted",
                "ui_execution_error": "failed",
            }
            status = status_map.get(name, "unknown")
            key = f"{base['mode']}::{base['command'].lower()}"
            canonical_id = self._canonical_id(key)
            self.records.append(
                RunRecord(
                    timestamp=utc_now(),
                    segment=self.segment,
                    canonical_id=canonical_id,
                    command=base["command"],
                    mode=base["mode"],
                    status=status,
                    steps=int(base["steps"]),
                    error=str(payload.get("error", "")),
                )
            )

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
                    "timestamp",
                    "segment",
                    "canonical_id",
                    "command",
                    "mode",
                    "status",
                    "steps",
                    "error",
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
                    ]
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Live logger for robot metrics/events")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("experiment") / "results" / f"live_session_{stamp}"

    logger = LiveLogger(
        base_url=args.base_url,
        poll_interval=max(0.2, float(args.poll_interval)),
        out_dir=out_dir,
    )
    logger.run()


if __name__ == "__main__":
    main()
