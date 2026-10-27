from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DeviceStatus:
    device_code: str
    state: str
    observed_at: datetime
    detail: str = ""


class BarrierDriver(ABC):
    @abstractmethod
    def open(self, authorization_reference: str) -> None: ...
    @abstractmethod
    def close(self) -> None: ...
    @abstractmethod
    def status(self) -> DeviceStatus: ...


class OccupancySensor(ABC):
    @abstractmethod
    def occupied(self) -> bool: ...
