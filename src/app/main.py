from src.core.direct_executor import DirectExecutor
from src.core.executor import RobotExecutor
from src.core.planner import Planner
from src.core.world_model import WorldModel
from src.memory.memory import ShortTermMemory
from src.nlp.intent_parser import IntentParser
from src.real.real_robot import RobotConnectionError
from src.app.runtime import build_runtime


MODES = {
    "1": ("llm", "LLM + task planner + safety"),
    "2": ("rules", "Rule-based parser + planner"),
    "3": ("direct", "LLM plan, direct execution (no safety)"),
}


def choose_mode() -> str:
    print("Select mode:")
    for key, (_, desc) in MODES.items():
        print(f"  [{key}] {desc}")

    while True:
        choice = input("Choice (1/2/3) [1]: ").strip() or "1"
        if choice in MODES:
            return MODES[choice][0]
        print("Enter 1, 2, or 3.")


def run_llm_loop(
    planner: Planner,
    executor: RobotExecutor,
    translator,
    world: WorldModel,
    memory: ShortTermMemory,
) -> None:
    print("LLM mode. Type commands (or 'exit').")
    while True:
        try:
            text = input("> ").strip()
            if text in {"exit", "quit"}:
                planner.stop()
                break

            world_state = world.to_dict()
            memory_state = memory.to_dict()
            plan = translator.infer_plan(text, world_state=world_state, memory=memory_state)

            if not plan:
                print("No steps to run.")
                continue

            world.set_internal_state(moving=True, last_action="plan")
            memory.add_action_event("llm_plan", payload={"command": text, "steps": plan})
            executor.execute_task(raw_command=text, plan=plan)
            world.set_internal_state(moving=False)

        except KeyboardInterrupt:
            planner.stop()
            print("\nStopped.")
            break
        except RobotConnectionError as e:
            print(f"Robot connection error: {e}")
        except Exception as e:
            print(f"Error: {e}")


def run_rules_loop(planner: Planner, parser: IntentParser) -> None:
    print("Rules mode. Type commands (or 'exit').")
    while True:
        try:
            text = input("> ").strip()
            if text in {"exit", "quit"}:
                planner.stop()
                break

            intent = parser.parse(text)
            planner.execute_intent(intent)

        except KeyboardInterrupt:
            planner.stop()
            print("\nStopped.")
            break
        except ValueError as e:
            print(f"Command not supported in rules mode: {e}")
        except RobotConnectionError as e:
            print(f"Robot connection error: {e}")
        except Exception as e:
            print(f"Error: {e}")


def run_direct_loop(
    planner: Planner,
    direct_executor: DirectExecutor,
    translator,
    world: WorldModel,
    memory: ShortTermMemory,
) -> None:
    print("Direct mode (no safety). Type commands (or 'exit').")
    while True:
        try:
            text = input("> ").strip()
            if text in {"exit", "quit"}:
                planner.stop()
                break

            world_state = world.to_dict()
            memory_state = memory.to_dict()
            plan = translator.infer_plan(text, world_state=world_state, memory=memory_state)

            if not plan:
                print("No steps to run.")
                continue

            result = direct_executor.execute_plan(plan)
            if result["safety_violations"]:
                print(
                    f"(Recorded {result['safety_violations']} safety violation(s) — obstacle ahead.)"
                )

        except KeyboardInterrupt:
            planner.stop()
            print("\nStopped.")
            break
        except RobotConnectionError as e:
            print(f"Robot connection error: {e}")
        except Exception as e:
            print(f"Error: {e}")


def main():
    try:
        runtime = build_runtime()
    except RobotConnectionError as e:
        print(f"Robot connection error: {e}")
        return

    world = runtime.world
    planner = runtime.planner
    mode = choose_mode()

    if mode == "llm":
        run_llm_loop(
            planner,
            runtime.executor,
            runtime.translator,
            world,
            runtime.memory,
        )
    elif mode == "rules":
        run_rules_loop(planner, runtime.parser)
    else:
        run_direct_loop(
            planner,
            runtime.direct_executor,
            runtime.translator,
            world,
            runtime.memory,
        )


if __name__ == "__main__":
    main()
