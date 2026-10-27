# Payment gateway integration

ParkEase currently includes a local simulation gateway only. It supports payment
intent creation, idempotency, and explicit simulated completion without sending
money or card/UPI details anywhere.

For a real gateway, select a provider (for example Razorpay, Stripe, or PayU),
store its secret key only in environment variables, verify provider webhooks,
and update `payments.status` from verified webhook events—not from browser input.

Never release a slot or open an exit barrier merely because a browser says that a
payment succeeded. Require an authenticated, verified payment record and the
configured exit safety checks.
