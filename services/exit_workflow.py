from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from database import db, transaction
from models import ParkingSession, ParkingSlot, Payment
from services.pricing import calculate_fee


def quote_exit(
    session_reference: str,
    hourly_rate: Decimal,
    minimum_charge: Decimal,
    increment_minutes: int,
    grace_period_minutes: int = 0,
    ev_kwh: Decimal = Decimal("0.00"),
    ev_kwh_rate: Decimal = Decimal("0.00")
):
    session = db.session.scalar(select(ParkingSession).where(ParkingSession.session_reference == session_reference))
    if not session or session.status not in {"active", "awaiting_payment"}: raise ValueError("No active session is available for exit.")
    entry_at = session.entry_at
    if entry_at.tzinfo is not None:
        entry_at = entry_at.astimezone(timezone.utc).replace(tzinfo=None)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if now < entry_at:
        now = entry_at
    kwh = ev_kwh if ev_kwh > 0 else (session.ev_kwh or Decimal("0.00"))
    return calculate_fee(
        entry_at,
        now,
        hourly_rate,
        minimum_charge,
        increment_minutes,
        grace_period_minutes=grace_period_minutes,
        ev_kwh=kwh,
        ev_kwh_rate=ev_kwh_rate
    )


def complete_paid_exit(session_reference: str, payment_key: str, amount: Decimal, method: str, provider_reference: str | None = None) -> dict:
    """Close only a confirmed payment; callers verify gateway signatures first."""
    with transaction():
        session = db.session.scalar(select(ParkingSession).where(ParkingSession.session_reference == session_reference).with_for_update())
        if not session or session.status not in {"active", "awaiting_payment"}: raise ValueError("Session cannot be closed.")
        payment = db.session.scalar(select(Payment).where(Payment.idempotency_key == payment_key).with_for_update())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if payment is None:
            payment = Payment(parking_session_id=session.id, amount=amount, method=method, status="paid", idempotency_key=payment_key, provider_reference=provider_reference, paid_at=now); db.session.add(payment)
        elif payment.status != "paid": payment.status, payment.paid_at = "paid", now
        slot = db.session.get(ParkingSlot, session.slot_id, with_for_update=True) if session.slot_id else None
        if slot: slot.status = "available"
        session.status, session.exit_at, session.calculated_charge = "closed", now, amount
        return {"receipt_number": f"RCT-{payment_key[-12:].upper()}", "session_reference": session_reference, "amount": str(amount), "status": "paid"}
