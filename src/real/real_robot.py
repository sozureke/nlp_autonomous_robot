import os
import serial
import time

from dotenv import load_dotenv

from ..core.robot_api import BaseRobot, RobotState


load_dotenv()

# Ports to try when ROBOT_SERIAL_PORT is not set (order matters)
DEFAULT_PORTS = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0"]


def _resolve_port() -> str:
    """Use ROBOT_SERIAL_PORT from env, or first available of DEFAULT_PORTS."""
    port = os.getenv("ROBOT_SERIAL_PORT", "").strip()
    if port and os.path.exists(port):
        return port
    for p in DEFAULT_PORTS:
        if os.path.exists(p):
            return p
    return os.getenv("ROBOT_SERIAL_PORT", "/dev/ttyUSB0")


def _connection_lost_msg(e: Exception) -> str:
    return (
        f"Serial connection lost: {e}. "
        "Often happens when motors draw current (USB power drop or controller reset). "
        "Check USB cable, use a powered hub, set ROBOT_SERIAL_PORT if needed. Reconnect and restart."
    )


class RobotConnectionError(Exception):
    """Raised when serial connection to the robot fails or is lost."""


class RealRobot(BaseRobot):
    """
    Real robot adapter for GalaxyRVR (Arduino over USB serial).
    """

    def __init__(
        self,
        port: str | None = None,
        baudrate=115200,
        left_trim: float | None = None,
        right_trim: float | None = None,
        left_offset: int | None = None,
        right_offset: int | None = None,
    ):
        port = port or _resolve_port()
        try:
            self._ser = serial.Serial(port, baudrate, timeout=0.05)
        except (OSError, serial.SerialException) as e:
            raise RobotConnectionError(
                f"Cannot open serial port {port}: {e}. "
                "Check USB cable, set ROBOT_SERIAL_PORT (e.g. /dev/ttyUSB1) if needed."
            ) from e
        time.sleep(2)  # wait for Arduino reset

        # Motor calibration compensates open-loop drift.
        # Example: if the robot drifts left, the right motor is likely stronger,
        # so reduce MOTOR_RIGHT_TRIM below 1.0.
        self._left_trim = (
            left_trim if left_trim is not None else self._read_float_env("MOTOR_LEFT_TRIM", 1.0)
        )
        self._right_trim = (
            right_trim if right_trim is not None else self._read_float_env("MOTOR_RIGHT_TRIM", 1.0)
        )
        self._left_offset = (
            left_offset if left_offset is not None else self._read_int_env("MOTOR_LEFT_OFFSET", 0)
        )
        self._right_offset = (
            right_offset if right_offset is not None else self._read_int_env("MOTOR_RIGHT_OFFSET", 0)
        )

        # last known valid state
        self._last_state = RobotState(
            distance_front=float("inf"),
            obstacle_left=False,
            obstacle_right=False,
        )

        # wait until Arduino is ready
        self._wait_ready()

    def _read_float_env(self, name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    def _read_int_env(self, name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    def _apply_motor_calibration(self, power: int, trim: float, offset: int) -> int:
        if power == 0:
            return 0

        calibrated = int(power * trim)

        # Offset is applied with the current motor direction so it behaves
        # consistently in both forward and backward motion.
        if offset:
            calibrated += (1 if power > 0 else -1) * offset

        return max(-100, min(100, calibrated))

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
        except (OSError, serial.SerialException) as e:
            raise RobotConnectionError(_connection_lost_msg(e)) from e
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

        left = self._apply_motor_calibration(left, self._left_trim, self._left_offset)
        right = self._apply_motor_calibration(right, self._right_trim, self._right_offset)

        cmd = f"M {left} {right}\n"
        self._write(cmd.encode())

    def stop(self) -> None:
        self._write(b"S\n")
        try:
            self._ser.flush()
        except (OSError, serial.SerialException) as e:
            raise RobotConnectionError(_connection_lost_msg(e)) from e

    def _write(self, data: bytes) -> None:
        try:
            self._ser.write(data)
        except (OSError, serial.SerialException) as e:
            raise RobotConnectionError(_connection_lost_msg(e)) from e

    def get_state(self) -> RobotState:
        # read all available lines, keep last valid state
        try:
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
        except (OSError, serial.SerialException) as e:
            raise RobotConnectionError(_connection_lost_msg(e)) from e
