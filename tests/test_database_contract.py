from pathlib import Path


def test_mysql_schema_contains_core_integrity_guards():
    schema = Path("sql/02_parkease_schema.sql").read_text(encoding="utf-8")
    assert "uq_active_session_per_vehicle" in schema
    assert "uq_active_session_per_slot" in schema
    assert "idempotency_key" in schema
    assert "FOREIGN KEY" in schema


def test_application_has_no_sqlite_runtime_fallback():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "sqlite:///" not in source
    assert "mysql+pymysql://" in source
