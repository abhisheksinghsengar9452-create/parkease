from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from services.plates import normalize_plate
from services.pricing import calculate_fee


def test_plate_normalization_is_consistent():
    assert normalize_plate("UP 14 AB-1234") == "UP14AB1234"


def test_invalid_plate_is_rejected():
    with pytest.raises(ValueError): normalize_plate("???")


def test_fee_uses_minimum_and_rounds_up():
    start = datetime(2026, 1, 1, 10, 0)
    quote = calculate_fee(start, start + timedelta(minutes=61), Decimal("50"), Decimal("40"), 60)
    assert quote.billable_minutes == 120
    assert quote.amount == Decimal("100.00")
