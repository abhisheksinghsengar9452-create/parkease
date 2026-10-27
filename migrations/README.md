# Database migrations

The current install scripts are versioned under `sql/`. Before production use,
initialize Alembic/Flask-Migrate and generate a migration for every schema
change. Never use `db.create_all()` as a deployment migration strategy.

Migration rules:

- Each migration is forward-only and has a reviewed downgrade where safe.
- Lock and back up production data before destructive/schema-rewrite changes.
- Apply migrations in CI against MySQL 8.0, then a staging database.
- Do not alter an already-applied migration.
