# Razorpay integration

ParkEase uses Razorpay Orders API. Create an order server-side using the amount
stored in the parking session; never accept an amount from browser JavaScript.
The checkout response must be signature-verified server-side. Webhook payloads
must be verified with `RAZORPAY_WEBHOOK_SECRET` before marking a payment paid.

Use Razorpay Test Mode keys first. Test mode does not deduct real money. After
KYC and live-mode review, replace only the environment variables with live keys.
Configure payment webhooks in Razorpay for captured/failed payment events.
