# ParkEase deployment runbook

## Production prerequisites

- MySQL 8.0+ with a dedicated least-privilege application user.
- HTTPS reverse proxy; set `COOKIE_SECURE=true` only behind HTTPS.
- A long random `SECRET_KEY` and all Razorpay secrets supplied as environment variables.
- A persistent MySQL backup target, monitored logs, and a tested restore procedure.

## Container deployment

1. Copy `.env.example` to `.env` and add `MYSQL_APP_PASSWORD`,
   `MYSQL_ROOT_PASSWORD`, `SECRET_KEY`, and Razorpay values. Never commit it.
2. Run `docker compose up --build -d`.
3. Create the first administrator using the web container's `create-admin` command.
4. Put an HTTPS reverse proxy in front of port 8000.
5. Configure Razorpay webhooks against the public HTTPS callback endpoint after
   the callback is implemented and tested with Test Mode.

## Operations

- Review error logs and device-health events daily.
- Back up MySQL before every migration and test restores periodically.
- Rotate application, database, and Razorpay secrets on staff changes or exposure.
- Keep barriers closed on gateway/device/database failures.

## Final acceptance checklist

- [ ] MySQL schema installed and backups verified.
- [ ] Administrator login and RBAC verified.
- [ ] Entry, exit, payment, OCR review, and barrier simulator tested.
- [ ] Razorpay Test Mode callback/webhook verification tested.
- [ ] HTTPS and secure cookies enabled.
- [ ] Monitoring, log retention, image retention, and recovery process approved.
