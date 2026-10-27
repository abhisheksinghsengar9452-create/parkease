"""Payment provider boundary. The simulator is safe for local development only."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from secrets import token_urlsafe


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"


@dataclass(frozen=True)
class PaymentIntent:
    idempotency_key: str
    amount: Decimal
    currency: str
    reference: str
    status: PaymentStatus
    provider_reference: str | None = None


class SimulatedPaymentGateway:
    """Deterministic local-only gateway; never contacts a financial provider."""
    def __init__(self) -> None:
        self._intents: dict[str, PaymentIntent] = {}

    def create_intent(self, *, amount: Decimal, currency: str, reference: str, idempotency_key: str) -> PaymentIntent:
        if amount <= 0 or currency != "INR":
            raise ValueError("Payment amount must be positive and currency must be INR.")
        if idempotency_key in self._intents:
            return self._intents[idempotency_key]
        intent = PaymentIntent(idempotency_key, amount.quantize(Decimal("0.01")), currency, reference, PaymentStatus.PENDING, f"sim_{token_urlsafe(10)}")
        self._intents[idempotency_key] = intent
        return intent

    def mark_paid(self, idempotency_key: str) -> PaymentIntent:
        intent = self._intents.get(idempotency_key)
        if intent is None:
            raise KeyError("Payment intent not found.")
        paid = PaymentIntent(intent.idempotency_key, intent.amount, intent.currency, intent.reference, PaymentStatus.PAID, intent.provider_reference)
        self._intents[idempotency_key] = paid
        return paid
