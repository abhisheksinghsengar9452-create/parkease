from decimal import Decimal
from datetime import datetime, timezone, timedelta
from services.rto_decoder import decode_indian_plate
from services.pricing import calculate_fee


def test_indian_rto_decoder():
    delhi = decode_indian_plate("DL04CA8821")
    assert delhi["is_valid"]
    assert delhi["state_code"] == "DL"
    assert "Delhi" in delhi["state"]
    assert "Janakpuri" in delhi["rto_office"]

    bh = decode_indian_plate("22BH1234AA")
    assert bh["is_valid"]
    assert bh["category"] == "Pan-India Bharat Series"
    assert bh["registration_year"] == "2022"

    ev = decode_indian_plate("MH02EV1000")
    assert ev["is_valid"]
    assert ev["is_ev"]


def test_pricing_grace_period_and_ev():
    entry = datetime(2026, 10, 27, 10, 0, 0)
    # Exiting within 15-minute grace window -> Free
    grace_exit = datetime(2026, 10, 27, 10, 12, 0)
    quote_grace = calculate_fee(
        entry, grace_exit,
        hourly_rate=Decimal("60.00"),
        minimum_charge=Decimal("20.00"),
        billing_increment_minutes=60,
        grace_period_minutes=15
    )
    assert quote_grace.is_grace_period
    assert quote_grace.amount == Decimal("0.00")

    # Exiting after 1 hour with 10.0 kWh EV fast charging @ 15/kWh
    exit_with_ev = datetime(2026, 10, 27, 11, 0, 0)
    quote_ev = calculate_fee(
        entry, exit_with_ev,
        hourly_rate=Decimal("50.00"),
        minimum_charge=Decimal("20.00"),
        billing_increment_minutes=60,
        grace_period_minutes=15,
        ev_kwh=Decimal("10.00"),
        ev_kwh_rate=Decimal("15.00")
    )
    assert not quote_ev.is_grace_period
    assert quote_ev.base_amount == Decimal("50.00")
    assert quote_ev.ev_charge == Decimal("150.00")
    assert quote_ev.amount == Decimal("200.00")
