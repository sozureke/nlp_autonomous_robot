"""
Quick diagnostic: read raw accel/gyro + compute heading from MPU6050 over I2C.
Run: python scripts/test_mpu6050.py
"""

import math
import struct
import time

import smbus2

BUS = 1
ADDR = 0x68

PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

ACCEL_SCALE = 16384.0  # ±2g
GYRO_SCALE = 131.0     # ±250 °/s


def init(bus: smbus2.SMBus) -> None:
    bus.write_byte_data(ADDR, PWR_MGMT_1, 0x00)
    time.sleep(0.1)


def read_raw(bus: smbus2.SMBus, reg: int) -> tuple[int, int, int]:
    data = bus.read_i2c_block_data(ADDR, reg, 6)
    x = struct.unpack(">h", bytes(data[0:2]))[0]
    y = struct.unpack(">h", bytes(data[2:4]))[0]
    z = struct.unpack(">h", bytes(data[4:6]))[0]
    return x, y, z


def accel_g(bus: smbus2.SMBus) -> tuple[float, float, float]:
    ax, ay, az = read_raw(bus, ACCEL_XOUT_H)
    return ax / ACCEL_SCALE, ay / ACCEL_SCALE, az / ACCEL_SCALE


def gyro_dps(bus: smbus2.SMBus) -> tuple[float, float, float]:
    gx, gy, gz = read_raw(bus, GYRO_XOUT_H)
    return gx / GYRO_SCALE, gy / GYRO_SCALE, gz / GYRO_SCALE


def pitch_roll_from_accel(ax: float, ay: float, az: float) -> tuple[float, float]:
    pitch = math.atan2(ay, math.sqrt(ax * ax + az * az)) * 180.0 / math.pi
    roll = math.atan2(-ax, az) * 180.0 / math.pi
    return pitch, roll


def main() -> None:
    bus = smbus2.SMBus(BUS)
    init(bus)

    print("MPU6050 diagnostic — press Ctrl+C to stop\n")
    print(f"{'ax':>7} {'ay':>7} {'az':>7}  {'gx':>8} {'gy':>8} {'gz':>8}  {'pitch':>7} {'roll':>7}  {'heading':>8}")
    print("-" * 90)

    heading = 0.0
    prev_time = time.monotonic()

    try:
        while True:
            ax, ay, az = accel_g(bus)
            gx, gy, gz = gyro_dps(bus)
            pitch, roll = pitch_roll_from_accel(ax, ay, az)

            now = time.monotonic()
            dt = now - prev_time
            prev_time = now

            # Integrate Z-axis gyro for yaw (heading estimate).
            # MPU6050 has no magnetometer so this drifts over time,
            # but is fine for short-term turn measurement.
            heading += gz * dt
            heading %= 360.0

            print(
                f"{ax:7.3f} {ay:7.3f} {az:7.3f}  "
                f"{gx:8.2f} {gy:8.2f} {gz:8.2f}  "
                f"{pitch:7.1f} {roll:7.1f}  "
                f"{heading:8.1f}"
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nDone.")
    finally:
        bus.close()


if __name__ == "__main__":
    main()
