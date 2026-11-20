"""Transactional parking-session lifecycle; independent of HTTP and hardware."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from database import db, transaction
from models import ParkingSession, ParkingSlot, Vehicle
from services.plates import normalize_plate


def create_entry(
    plate_text: str,
    is_disabled: bool = False,
    plate_color: str | None = None,
    vehicle_type: str | None = None
) -> ParkingSession:
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

        # Decode Indian plate series & combine with optical plate color
        from services.rto_decoder import decode_indian_plate
        rto_info = decode_indian_plate(normalized, detected_color=plate_color)
        effective_color = rto_info.get("plate_color") or plate_color or "white"

        is_ev = (effective_color == "green") or rto_info.get("is_ev") or bool(vehicle_type and "ev" in vehicle_type.lower())
        is_commercial = (effective_color == "yellow") or rto_info.get("is_commercial") or bool(vehicle_type and any(k in vehicle_type.lower() for k in ("transport", "commercial")))

        # Update vehicle classification in registry
        if is_disabled:
            vehicle.vehicle_type = "Accessible / PwD"
        elif is_ev:
            vehicle.vehicle_type = "Electric Vehicle (EV)"
        elif is_commercial:
            vehicle.vehicle_type = "Commercial Transport"
        else:
            vehicle.vehicle_type = "Petrol / Diesel (Private)"

        # Strict Rule-Based Slot Allocation
        slot = None
        if is_disabled:
            # ♿ PERSON WITH DISABILITY (PwD / Accessible):
            # Prioritize dedicated disabled parking slots. If full, allocate accessible standard bay.
            slot = db.session.scalar(
                select(ParkingSlot)
                .where(ParkingSlot.status == "available", ParkingSlot.slot_type == "disabled")
                .order_by(ParkingSlot.slot_code)
                .limit(1)
                .with_for_update()
            )
            if slot is None:
                # Fallback to standard or EV if disabled bays are full
                target_types = ("standard", "ev") if is_ev else ("standard",)
                slot = db.session.scalar(
                    select(ParkingSlot)
                    .where(ParkingSlot.status == "available", ParkingSlot.slot_type.in_(target_types))
                    .order_by(ParkingSlot.slot_code)
                    .limit(1)
                    .with_for_update()
                )
            if slot is None:
                raise ValueError("No parking slots are currently available for Person with Disability (PwD).")

        elif is_ev:
            # ⚡ ELECTRIC VEHICLES (Green Plate):
            # Must be parked in EV fast-charging bays. Non-EV vehicles CANNOT park here.
            slot = db.session.scalar(
                select(ParkingSlot)
                .where(ParkingSlot.status == "available", ParkingSlot.slot_type == "ev")
                .order_by(ParkingSlot.slot_code)
                .limit(1)
                .with_for_update()
            )
            if slot is None:
                # If EV bays are temporarily full, fall back to standard, but NEVER to disabled!
                slot = db.session.scalar(
                    select(ParkingSlot)
                    .where(ParkingSlot.status == "available", ParkingSlot.slot_type == "standard")
                    .order_by(ParkingSlot.slot_code)
                    .limit(1)
                    .with_for_update()
                )
            if slot is None:
                raise ValueError("No EV charging or standard parking slots are currently available.")

        elif is_commercial:
            # 🚖 COMMERCIAL TRANSPORT VEHICLES (Yellow Plate - Taxis, Cabs):
            # Park in transport or standard bays; NEVER in EV bays and NEVER in disabled bays.
            slot = db.session.scalar(
                select(ParkingSlot)
                .where(ParkingSlot.status == "available", ParkingSlot.slot_type.in_(("transport", "standard")))
                .order_by(ParkingSlot.slot_code)
                .limit(1)
                .with_for_update()
            )
            if slot is None:
                raise ValueError("No parking slots are currently available for commercial transport vehicles.")

        else:
            # 🚗 NORMAL VEHICLES (White Plate - Petrol / Diesel / CNG):
            # Must ONLY be parked in standard bays.
            # Strictly prohibited from occupying EV charging bays or Disabled bays!
            slot = db.session.scalar(
                select(ParkingSlot)
                .where(ParkingSlot.status == "available", ParkingSlot.slot_type == "standard")
                .order_by(ParkingSlot.slot_code)
                .limit(1)
                .with_for_update()
            )
            if slot is None:
                raise ValueError("No standard parking slots available for Petrol/Diesel vehicles.")

        slot.status = "occupied"
        note_str = "PwD Accessible Driver" if is_disabled else ("EV Green Plate" if is_ev else ("Commercial Transport Yellow Plate" if is_commercial else "Petrol / Diesel White Plate"))
        session = ParkingSession(
            session_reference=f"PS-{uuid4().hex[:12].upper()}",
            vehicle_id=vehicle.id,
            slot_id=slot.id,
            entry_at=datetime.now(timezone.utc),
            status="active",
            calculated_charge=Decimal("0.00"),
            notes=note_str
        )
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
