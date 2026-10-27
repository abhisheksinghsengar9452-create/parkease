from __future__ import annotations
from database import db
from models import AuditLog


def record(user_id: int | None, action: str, entity_type: str, entity_id: str | None = None) -> None:
    """Queue an audit record inside the caller's existing transaction."""
    db.session.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id))
