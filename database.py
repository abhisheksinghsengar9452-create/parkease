"""Database extension and transaction primitives for ParkEase."""
from contextlib import contextmanager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

@contextmanager
def transaction():
    """Commit atomically or roll back on every failure."""
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
