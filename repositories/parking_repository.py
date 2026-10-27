from __future__ import annotations

from sqlalchemy import select
from database import db, transaction


class ParkingRepository:
    """Concurrency-safe primitives for later entry/exit services.

    MySQL `FOR UPDATE` locks are acquired before an available bay is claimed.
    The database's generated unique active-slot key remains the final guard.
    """
    def lock_next_available_slot(self):
        from models import ParkingSlot
        query = (select(ParkingSlot).where(ParkingSlot.status == "available")
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
