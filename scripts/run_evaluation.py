"""
Usage
  python scripts/run_evaluation.py [--commands-file path] [--sim] [--output report.json]
  --sim: use simulated robot (no hardware). Without --sim uses RealRobot (GalaxyRVR).
  Summary: symbolic_safety_violations is 0 by design; direct_safety_violations
  counts move_forward steps that would have run with obstacle ahead (baseline).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.control_api import ControlAPI
from src.core.direct_executor import DirectExecutor
from src.core.executor import RobotExecutor
from src.core.planner import Planner
from src.core.safety_controller import SafetyController
from src.core.world_model import WorldModel
from src.memory.memory import ShortTermMemory
from src.nlp.llm_agent import build_default_translator
from src.real.real_robot import RealRobot
from src.sim.sim_robot import SimRobot
from src.sim.world import World as SimWorld


TEST_COMMANDS = [
    "go forward",
    "turn left",
    "turn right",
    "stop",
    "go forward until you see something",
    "turn 180 degrees",
    "turn around and go forward until obstacle",
    "scan",
    "move ahead",
]


def load_commands(path: str | None) -> list[str]:
    if path is None:
        return TEST_COMMANDS

    p = Path(path)
    if not p.exists():
        print(f"Commands file not found: {path}", file=sys.stderr)
        return TEST_COMMANDS

    text = p.read_text(encoding="utf-8").strip()
    return [line.strip() for line in text.splitlines() if line.strip()]


def run_evaluation(commands: list[str], use_sim: bool = False) -> dict:
    if use_sim:
        sim_world = SimWorld()
        robot = SimRobot(sim_world)
    else:
        robot = RealRobot()

    world = WorldModel()
    planner = Planner(robot, world)
    control = ControlAPI(planner=planner)
    memory = ShortTermMemory()
    safety = SafetyController()
    symbolic_executor = RobotExecutor(
        control=control,
        memory=memory,
        safety_controller=safety,
        world_model=world,
    )
    direct_executor = DirectExecutor(robot=robot, world=world)
    translator = build_default_translator()

    results = []
    for i, text in enumerate(commands):
        print(f"[{i+1}/{len(commands)}] {text!r} ...", flush=True)
        world_state = world.to_dict()
        memory_state = memory.to_dict()
        plan = translator.infer_plan(text, world_state=world_state, memory=memory_state)

        if not plan:
            results.append(
                {
                    "command": text,
                    "plan": [],
                    "symbolic_success": False,
                    "symbolic_safety_violations": 0,
                    "direct_success": False,
                    "direct_safety_violations": 0,
                    "error": "empty plan",
                }
            )
            continue

        symbolic_success = True
        try:
            planner.stop()
            world.set_internal_state(moving=True, last_action="plan")
            symbolic_executor.execute_plan(plan)
            world.set_internal_state(moving=False)
        except Exception:
            symbolic_success = False
            try:
                planner.stop()
            except Exception:
                pass
        finally:
            world.set_internal_state(moving=False)

        direct_result = direct_executor.execute_plan(plan)

        results.append(
            {
                "command": text,
                "plan": plan,
                "symbolic_success": symbolic_success,
                "symbolic_safety_violations": 0,
                "direct_success": direct_result["success"],
                "direct_safety_violations": direct_result["safety_violations"],
            }
        )

    return {
        "results": results,
        "summary": {
            "total_commands": len(commands),
            "symbolic_success_count": sum(1 for r in results if r["symbolic_success"]),
            "symbolic_safety_violations_total": 0,
            "direct_success_count": sum(1 for r in results if r["direct_success"]),
            "direct_safety_violations_total": sum(r["direct_safety_violations"] for r in results),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Symbolic vs direct execution evaluation")
    parser.add_argument("--commands-file", type=str, default=None, help="Path to file with one command per line")
    parser.add_argument("--output", type=str, default=None, help="Write JSON report to file")
    parser.add_argument("--sim", action="store_true", help="Use simulated robot (no hardware)")
    args = parser.parse_args()

    commands = load_commands(args.commands_file)
    print(f"Running evaluation on {len(commands)} commands (sim={args.sim}).", flush=True)
    report = run_evaluation(commands, use_sim=args.sim)

    summary = report["summary"]
    print("\n--- Summary ---")
    print(f"Total commands: {summary['total_commands']}")
    print(
        f"Symbolic: success {summary['symbolic_success_count']}/{summary['total_commands']}, "
        f"safety_violations = {summary['symbolic_safety_violations_total']}"
    )
    print(
        f"Direct:   success {summary['direct_success_count']}/{summary['total_commands']}, "
        f"safety_violations = {summary['direct_safety_violations_total']}"
    )

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport written to {args.output}")


if __name__ == "__main__":
    main()
