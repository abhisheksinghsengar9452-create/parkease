"""Razorpay Orders API integration; secrets are environment-only."""
from __future__ import annotations
import hmac
import os
from decimal import Decimal
import razorpay


class RazorpayGateway:
    def __init__(self) -> None:
        self.key_id = os.environ["RAZORPAY_KEY_ID"]
        self.key_secret = os.environ["RAZORPAY_KEY_SECRET"]
        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

    def create_order(self, amount: Decimal, receipt: str, notes: dict[str, str] | None = None) -> dict:
        if amount <= 0 or len(receipt) > 40:
            raise ValueError("Amount must be positive and receipt may contain at most 40 characters.")
        return self.client.order.create({"amount": int(amount * 100), "currency": "INR", "receipt": receipt, "notes": notes or {}})

    def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        try:
            self.client.utility.verify_payment_signature({"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": signature})
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        expected = hmac.new(os.environ["RAZORPAY_WEBHOOK_SECRET"].encode(), payload, "sha256").hexdigest()
        return hmac.compare_digest(expected, signature)
