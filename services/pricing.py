from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_UP


@dataclass(frozen=True)
class FeeQuote:
    billable_minutes: int
    amount: Decimal
    base_amount: Decimal = Decimal("0.00")
    ev_charge: Decimal = Decimal("0.00")
    is_grace_period: bool = False


def calculate_fee(
    entry_at: datetime,
    exit_at: datetime,
    hourly_rate: Decimal,
    minimum_charge: Decimal,
    billing_increment_minutes: int,
    grace_period_minutes: int = 0,
    ev_kwh: Decimal = Decimal("0.00"),
    ev_kwh_rate: Decimal = Decimal("0.00")
) -> FeeQuote:
    """Return a deterministic fee; callers must persist the selected rule first."""
    if exit_at < entry_at:
        if (entry_at - exit_at).total_seconds() < 2:
            exit_at = entry_at
        else:
            raise ValueError("Exit time cannot precede entry time.")
    if hourly_rate < 0 or minimum_charge < 0 or billing_increment_minutes <= 0:
        raise ValueError("Invalid pricing rule.")

    elapsed = Decimal((exit_at - entry_at).total_seconds()) / Decimal(60)

    # Grace period check: Free parking if exiting within grace window
    is_grace = grace_period_minutes > 0 and elapsed <= Decimal(grace_period_minutes)

    if is_grace:
        base_fee = Decimal("0.00")
        billable = int(elapsed.to_integral_value(rounding=ROUND_UP))
    else:
        increments = (elapsed / Decimal(billing_increment_minutes)).to_integral_value(rounding=ROUND_UP)
        billable_dec = max(Decimal(1), increments) * Decimal(billing_increment_minutes)
        billable = int(billable_dec)
        base_fee = max(minimum_charge, (billable_dec / Decimal(60)) * hourly_rate).quantize(Decimal("0.01"))

    ev_fee = (Decimal(str(ev_kwh)) * Decimal(str(ev_kwh_rate))).quantize(Decimal("0.01")) if ev_kwh > 0 else Decimal("0.00")
    total_fee = base_fee + ev_fee

    return FeeQuote(
        billable_minutes=billable,
        amount=total_fee,
        base_amount=base_fee,
        ev_charge=ev_fee,
        is_grace_period=is_grace
    )
