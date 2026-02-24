from src.real.real_robot import RealRobot
from src.core.world_model import WorldModel
from src.core.planner import Planner
from src.core.control_api import ControlAPI
from src.core.executor import RobotExecutor
from src.memory.memory import ShortTermMemory
from src.nlp.llm_agent import build_default_translator


def main():
    robot = RealRobot()
    world = WorldModel()
    planner = Planner(robot, world)

    control = ControlAPI(planner=planner)
    executor = RobotExecutor(control=control)

    memory = ShortTermMemory()
    translator = build_default_translator()

    print("LLM control ready. Type commands (or 'exit').")

    while True:
        try:
            text = input("> ").strip()
            if text in {"exit", "quit"}:
                planner.stop()
                break

            # Build context for the LLM.
            world_state = world.to_dict()
            memory_state = memory.to_dict()

            # Natural language -> structured intent.
            try:
                intent = translator.infer_intent(
                    text,
                    world_state=world_state,
                    memory=memory_state,
                )
            except Exception as e:
                # Network / API failure: fall back to local rule-based intent.
                print(f"LLM error, falling back to heuristic intent: {e}")
                intent = translator._rule_based_fallback(text)  # type: ignore[attr-defined]

            cmd = intent.to_command_dict()

            # Update internal world state and memory about the chosen action.
            world.set_internal_state(moving=True, last_action=cmd.get("action"))
            memory.add_action_event("llm_intent", payload=cmd)

            # Execute via the unified executor stack.
            executor.execute_llm_intent(intent)

            # After execution, mark robot as not moving.
            world.set_internal_state(moving=False)

        except KeyboardInterrupt:
            planner.stop()
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
