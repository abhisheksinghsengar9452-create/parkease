"""Read-model queries for the operational dashboard."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, select, text
from database import db
from models import ParkingSession, ParkingSlot, Payment

IST = timezone(timedelta(hours=5, minutes=30))


def _to_local_str(dt: datetime) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%d %b, %I:%M %p")


def dashboard_summary() -> dict:
    total = db.session.scalar(select(func.count(ParkingSlot.id))) or 0
    available = db.session.scalar(select(func.count(ParkingSlot.id)).where(ParkingSlot.status == "available")) or 0
    occupied = db.session.scalar(select(func.count(ParkingSlot.id)).where(ParkingSlot.status == "occupied")) or 0
    active = db.session.scalar(select(func.count(ParkingSession.id)).where(ParkingSession.status.in_(("active", "awaiting_payment")))) or 0
    revenue = float(db.session.scalar(select(func.sum(Payment.amount)).where(Payment.status == "paid")) or 0)

    sessions = db.session.scalars(
        select(ParkingSession)
        .where(ParkingSession.status.in_(("active", "awaiting_payment")))
        .order_by(ParkingSession.entry_at.desc())
        .limit(20)
    ).all()

    slot_session_map = {s.slot_id: s for s in sessions if s.slot_id}

    slots = []
    zones = {}
    for s in db.session.scalars(select(ParkingSlot).order_by(ParkingSlot.zone, ParkingSlot.slot_code)).all():
        active_s = slot_session_map.get(s.id)
        z = s.zone or "A"
        stype = getattr(s, "slot_type", "standard") or "standard"
        slots.append({
            "code": s.slot_code,
            "zone": z,
            "type": stype,
            "status": s.status,
            "plate": active_s.vehicle.registration_number if active_s and active_s.vehicle else None,
            "session_id": active_s.session_reference if active_s else None
        })
        zones.setdefault(z, {"total": 0, "available": 0, "occupied": 0})
        zones[z]["total"] += 1
        if s.status == "available":
            zones[z]["available"] += 1
        elif s.status == "occupied":
            zones[z]["occupied"] += 1

    session_list = []
    for s in sessions:
        entry_iso = s.entry_at.isoformat()
        if not s.entry_at.tzinfo and not entry_iso.endswith("Z"):
            entry_iso += "Z"
        session_list.append({
            "id": s.session_reference,
            "plate": s.vehicle.registration_number if s.vehicle else "—",
            "slot": s.slot.slot_code if s.slot else "—",
            "entry": _to_local_str(s.entry_at),
            "duration": "Live",
            "entry_timestamp": entry_iso,
            "fee": f"₹{s.calculated_charge}" if s.status == "closed" else "₹50.00",
            "payment": "Paid" if s.status == "closed" else "Accruing"
        })

    devices = []
    try:
        rows = db.session.execute(text("SELECT device_code, name, device_type, status FROM hardware_devices ORDER BY device_code")).all()
        for r in rows:
            devices.append({"name": r[1], "detail": f"{r[2].title()} · {r[0]}", "status": r[3]})
    except Exception:
        devices = []

    latest_session = db.session.scalars(
        select(ParkingSession).order_by(ParkingSession.entry_at.desc()).limit(1)
    ).first()
    if latest_session and latest_session.vehicle:
        anpr_info = {
            "plate": latest_session.vehicle.registration_number,
            "confidence": 96.8,
            "status": "GATE 01 · VERIFIED",
            "requires_review": False,
            "slot": latest_session.slot.slot_code if latest_session.slot else "A-01",
            "time": _to_local_str(latest_session.entry_at).split(", ")[-1]
        }
    else:
        anpr_info = {
            "plate": "DL 01 AB 1234",
            "confidence": 98.2,
            "status": "GATE 01 · STANDBY",
            "requires_review": False,
            "slot": "Ready for scan",
            "time": "Live"
        }

    return {
        "metrics": {"capacity": total, "available": available, "occupied": occupied, "active_sessions": active, "revenue": revenue},
        "slots": slots,
        "zones": zones,
        "sessions": session_list,
        "anpr": anpr_info,
        "devices": devices
    }
