# Phase 2 — Development Environment and Project Foundation

## Deliverables

- Python 3.11+ Flask application factory and MySQL-only configuration.
- SQLAlchemy database extension, MySQL driver, migration conventions, and SQL install scripts.
- Environment-variable configuration with `.env.example`; secrets are never committed.
- Structured logging with secrets excluded.
- pytest test suite for database contracts and business services.

## Local setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your local MySQL and Razorpay Test Mode values.
mysql -u root -p < sql/00_create_database.sql
mysql -u root -p parkease < sql/01_users.sql
mysql -u root -p parkease < sql/02_parkease_schema.sql
python -m pytest
flask --app app create-admin
flask --app app run --debug
```

## Acceptance criteria

- Application fails clearly without a MySQL `DATABASE_URL`.
- No SQLite runtime fallback exists.
- Schema scripts install in sequence on MySQL 8.0+.
- Automated tests pass before changes are accepted.
- Logging does not expose credentials, tokens, passwords, or payment secrets.
