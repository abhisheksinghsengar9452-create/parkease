from __future__ import annotations
from devices.base import BarrierDriver


def authorize_barrier_open(barrier: BarrierDriver, *, verified_payment: bool = False, authorized_entry: bool = False, manual_override: bool = False, audit_reference: str = "") -> None:
    """Only explicit, auditable business authorization can operate a barrier."""
    if not audit_reference:
        raise ValueError("Barrier commands require an audit reference.")
    if not (verified_payment or authorized_entry or manual_override):
        raise PermissionError("OCR and sensor events alone cannot open a barrier.")
    barrier.open(audit_reference)
