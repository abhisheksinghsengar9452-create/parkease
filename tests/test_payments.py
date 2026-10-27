from decimal import Decimal
import pytest
from services.payments import PaymentStatus, SimulatedPaymentGateway


def test_gateway_is_idempotent():
    gateway = SimulatedPaymentGateway()
    first = gateway.create_intent(amount=Decimal("100"), currency="INR", reference="PS-1", idempotency_key="key-1")
    second = gateway.create_intent(amount=Decimal("100"), currency="INR", reference="PS-1", idempotency_key="key-1")
    assert first.provider_reference == second.provider_reference
    assert gateway.mark_paid("key-1").status is PaymentStatus.PAID


def test_gateway_rejects_invalid_amount():
    with pytest.raises(ValueError):
        SimulatedPaymentGateway().create_intent(amount=Decimal("0"), currency="INR", reference="PS-1", idempotency_key="key")
