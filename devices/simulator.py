from __future__ import annotations
from datetime import datetime, timezone
from devices.base import BarrierDriver, DeviceStatus, OccupancySensor


class SimulatedBarrier(BarrierDriver):
    def __init__(self, device_code: str = "ENTRY-BARRIER-SIM") -> None:
        self.device_code, self._open = device_code, False

    def open(self, authorization_reference: str) -> None:
        if not authorization_reference:
            raise ValueError("A verified authorization reference is required.")
        self._open = True

    def close(self) -> None: self._open = False
    def status(self) -> DeviceStatus:
        return DeviceStatus(self.device_code, "open" if self._open else "closed", datetime.now(timezone.utc), "simulation")


class SimulatedOccupancySensor(OccupancySensor):
    def __init__(self, is_occupied: bool = False) -> None: self.is_occupied = is_occupied
    def occupied(self) -> bool: return self.is_occupied
