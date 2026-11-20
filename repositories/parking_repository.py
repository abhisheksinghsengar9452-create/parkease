from __future__ import annotations

from sqlalchemy import select
from database import db, transaction


class ParkingRepository:
    """Concurrency-safe primitives for later entry/exit services.

    MySQL `FOR UPDATE` locks are acquired before an available bay is claimed.
    The database's generated unique active-slot key remains the final guard.
    """
    def lock_next_available_slot(self, slot_type: str | None = None, is_disabled: bool = False):
        from models import ParkingSlot
        if is_disabled:
            query = (select(ParkingSlot).where(ParkingSlot.status == "available", ParkingSlot.slot_type == "disabled")
                     .order_by(ParkingSlot.slot_code).limit(1).with_for_update())
            slot = db.session.scalar(query)
            if slot is None:
                query = (select(ParkingSlot).where(ParkingSlot.status == "available", ParkingSlot.slot_type == "standard")
                         .order_by(ParkingSlot.slot_code).limit(1).with_for_update())
                slot = db.session.scalar(query)
            return slot
        if slot_type:
            query = (select(ParkingSlot).where(ParkingSlot.status == "available", ParkingSlot.slot_type == slot_type)
                     .order_by(ParkingSlot.slot_code).limit(1).with_for_update())
            return db.session.scalar(query)
        query = (select(ParkingSlot).where(ParkingSlot.status == "available", ParkingSlot.slot_type != "disabled")
                 .order_by(ParkingSlot.slot_code).limit(1).with_for_update())
        return db.session.scalar(query)

    def claim_slot(self, slot) -> None:
        if slot is None or slot.status != "available":
            raise ValueError("No available parking slot can be claimed.")
        slot.status = "occupied"

    def release_slot(self, slot) -> None:
        if slot is None or slot.status != "occupied":
            raise ValueError("Only an occupied parking slot can be released.")
        slot.status = "available"

    def allocate_next_slot(self):
        with transaction():
            slot = self.lock_next_available_slot()
            self.claim_slot(slot)
            return slot
