import serial
import time
from ..core.robot_api import BaseRobot, RobotState


class RealRobot(BaseRobot):
    """
    Real robot adapter for GalaxyRVR (Arduino over USB serial).
    """

    def __init__(self, port="/dev/ttyUSB0", baudrate=115200):
        self._ser = serial.Serial(port, baudrate, timeout=0.05)
        time.sleep(2)  # wait for Arduino reset

        # last known valid state
        self._last_state = RobotState(
            distance_front=float("inf"),
            obstacle_left=False,
            obstacle_right=False,
        )

        # wait until Arduino is ready
        self._wait_ready()

    def _wait_ready(self):
        start = time.time()
        while time.time() - start < 5.0:
            line = self._readline()
            if line == "READY":
                return
        raise RuntimeError("Arduino did not send READY")

    def _readline(self) -> str:
        try:
            return self._ser.readline().decode(errors="ignore").strip()
        except Exception:
            return ""

    def move(self, linear: float, angular: float) -> None:
        # dead-zones to avoid jitter
        if abs(linear) < 0.05:
            linear = 0.0
        if abs(angular) < 0.05:
            angular = 0.0

        # map [-1, 1] -> [-100, 100]
        left = int((linear - angular) * 100)
        right = int((linear + angular) * 100)

        left = max(-100, min(100, left))
        right = max(-100, min(100, right))

        cmd = f"M {left} {right}\n"
        self._ser.write(cmd.encode())

    def stop(self) -> None:
        self._ser.write(b"S\n")
        self._ser.flush()

    def get_state(self) -> RobotState:
        # read all available lines, keep last valid state
        while self._ser.in_waiting:
            line = self._readline()
            if line.startswith("D"):
                try:
                    _, dist, ir_l, ir_r = line.split()
                    self._last_state = RobotState(
                        distance_front=float(dist) / 100.0,
                        obstacle_left=bool(int(ir_l)),
                        obstacle_right=bool(int(ir_r)),
                    )
                except Exception:
                    pass

        return self._last_state
