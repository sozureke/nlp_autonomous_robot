from __future__ import annotations

from dataclasses import dataclass

from src.core.robot_api import BaseRobot
from src.core.control_api import ControlAPI
from src.core.direct_executor import DirectExecutor
from src.core.executor import RobotExecutor
from src.core.planner import Planner
from src.core.safety_controller import SafetyController
from src.core.world_model import WorldModel
from src.memory.memory import MetricsCollector, ShortTermMemory
from src.nlp.intent_parser import IntentParser
from src.nlp.llm_agent import LLMIntentTranslator, build_default_translator
from src.real.real_robot import RealRobot
from src.sim.sim_robot import SimRobot
from src.sim.world import World


@dataclass
class RobotRuntime:
    robot: BaseRobot
    world: WorldModel
    planner: Planner
    memory: ShortTermMemory
    translator: LLMIntentTranslator
    control: ControlAPI
    safety: SafetyController
    executor: RobotExecutor
    direct_executor: DirectExecutor
    parser: IntentParser
    metrics: MetricsCollector


def build_runtime() -> RobotRuntime:
    """
    Build the shared runtime stack for CLI and Web API.
    """
    robot = RealRobot()
    world = WorldModel()
    planner = Planner(robot, world)
    memory = ShortTermMemory()
    translator = build_default_translator()
    control = ControlAPI(planner=planner)
    safety = SafetyController()
    executor = RobotExecutor(
        control=control,
        translator=translator,
        memory=memory,
        safety_controller=safety,
        world_model=world,
    )
    direct_executor = DirectExecutor(robot=robot, world=world)
    parser = IntentParser()
    metrics = MetricsCollector()
    return RobotRuntime(
        robot=robot,
        world=world,
        planner=planner,
        memory=memory,
        translator=translator,
        control=control,
        safety=safety,
        executor=executor,
        direct_executor=direct_executor,
        parser=parser,
        metrics=metrics,
    )


def build_runtime_with_mode(
    *,
    method: str,
    serial_port: str | None = None,
) -> RobotRuntime:
    """
    Build runtime for a selected connection method.
    """
    method_norm = method.strip().lower()
    if method_norm == "real":
        robot = RealRobot(port=serial_port) if serial_port else RealRobot()
        return _build_runtime_from_robot(robot)
    if method_norm == "sim":
        world = World(width=8.0, height=8.0)
        # Add a couple of default obstacles for meaningful simulation.
        world.add_obstacle(1.2, -0.4, 1.6, 0.4)
        world.add_obstacle(2.2, 0.8, 2.8, 1.2)
        robot = SimRobot(world=world)
        return _build_runtime_from_robot(robot)
    raise ValueError(f"Unsupported connection method: {method}")


def _build_runtime_from_robot(robot: BaseRobot) -> RobotRuntime:
    world = WorldModel()
    planner = Planner(robot, world)
    memory = ShortTermMemory()
    translator = build_default_translator()
    control = ControlAPI(planner=planner)
    safety = SafetyController()
    executor = RobotExecutor(
        control=control,
        translator=translator,
        memory=memory,
        safety_controller=safety,
        world_model=world,
    )
    direct_executor = DirectExecutor(robot=robot, world=world)
    parser = IntentParser()
    metrics = MetricsCollector()
    return RobotRuntime(
        robot=robot,
        world=world,
        planner=planner,
        memory=memory,
        translator=translator,
        control=control,
        safety=safety,
        executor=executor,
        direct_executor=direct_executor,
        parser=parser,
        metrics=metrics,
    )
