"""Transactional parking-session lifecycle; independent of HTTP and hardware."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from database import db, transaction
from models import ParkingSession, ParkingSlot, Vehicle
from services.plates import normalize_plate


def create_entry(plate_text: str) -> ParkingSession:
    normalized = normalize_plate(plate_text)
    with transaction():
        vehicle = db.session.scalar(select(Vehicle).where(Vehicle.normalized_registration == normalized).with_for_update())
        if vehicle is None:
            vehicle = Vehicle(registration_number=plate_text.strip().upper(), normalized_registration=normalized)
            db.session.add(vehicle)
            db.session.flush()
        existing = db.session.scalar(select(ParkingSession).where(ParkingSession.vehicle_id == vehicle.id, ParkingSession.status.in_(("active", "awaiting_payment"))).with_for_update())
        if existing:
            raise ValueError("Vehicle already has an active parking session.")
        slot = db.session.scalar(select(ParkingSlot).where(ParkingSlot.status == "available").order_by(ParkingSlot.slot_code).limit(1).with_for_update())
        if slot is None:
            raise ValueError("No parking slots are currently available.")
        slot.status = "occupied"
        session = ParkingSession(session_reference=f"PS-{uuid4().hex[:12].upper()}", vehicle_id=vehicle.id, slot_id=slot.id, entry_at=datetime.now(timezone.utc), status="active", calculated_charge=Decimal("0.00"))
        db.session.add(session)
        db.session.flush()
        return session


def release_session(session_reference: str) -> ParkingSession:
    """Administrative release only; billing/exit workflow replaces this in Phase 7."""
    with transaction():
        session = db.session.scalar(select(ParkingSession).where(ParkingSession.session_reference == session_reference).with_for_update())
        if session is None or session.status not in {"active", "awaiting_payment"}:
            raise ValueError("No releasable active session exists.")
        slot = db.session.get(ParkingSlot, session.slot_id, with_for_update=True) if session.slot_id else None
        if slot: slot.status = "available"
        session.status, session.exit_at = "cancelled", datetime.now(timezone.utc)
        return session
