from __future__ import annotations

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from database import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="operator")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    __table_args__ = (db.CheckConstraint("role IN ('administrator', 'operator')", name="ck_users_role"),)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="scrypt")

    def verify_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Vehicle(db.Model):
    __tablename__ = "vehicles"
    id = db.Column(db.BigInteger, primary_key=True)
    registration_number = db.Column(db.String(32), nullable=False)
    normalized_registration = db.Column(db.String(32), nullable=False, unique=True, index=True)
    vehicle_type = db.Column(db.String(30))


class ParkingSlot(db.Model):
    __tablename__ = "parking_slots"
    id = db.Column(db.BigInteger, primary_key=True)
    slot_code = db.Column(db.String(20), nullable=False, unique=True)
    zone = db.Column(db.String(40))
    status = db.Column(db.String(20), nullable=False, default="available", index=True)
    sensor_identifier = db.Column(db.String(100), unique=True)
    slot_type = db.Column(db.String(30), nullable=False, default="standard")


class PricingRule(db.Model):
    __tablename__ = "pricing_rules"
    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hourly_rate = db.Column(db.Numeric(10, 2), nullable=False)
    minimum_charge = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    billing_increment_minutes = db.Column(db.SmallInteger, nullable=False, default=60)
    grace_period_minutes = db.Column(db.SmallInteger, nullable=False, default=15)
    ev_kwh_rate = db.Column(db.Numeric(6, 2), nullable=False, default=15.00)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class ParkingSession(db.Model):
    __tablename__ = "parking_sessions"
    id = db.Column(db.BigInteger, primary_key=True)
    session_reference = db.Column(db.String(40), nullable=False, unique=True)
    vehicle_id = db.Column(db.BigInteger, db.ForeignKey("vehicles.id"), nullable=False, index=True)
    slot_id = db.Column(db.BigInteger, db.ForeignKey("parking_slots.id"), index=True)
    status = db.Column(db.String(24), nullable=False, default="active", index=True)
    entry_at = db.Column(db.DateTime, nullable=False)
    exit_at = db.Column(db.DateTime)
    calculated_charge = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    ev_kwh = db.Column(db.Numeric(6, 2), nullable=False, default=0.00)
    notes = db.Column(db.String(250), nullable=True)
    slot = db.relationship("ParkingSlot", foreign_keys=[slot_id])
    vehicle = db.relationship("Vehicle", foreign_keys=[vehicle_id])


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(80))
    occurred_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", foreign_keys=[user_id])


class HardwareDevice(db.Model):
    __tablename__ = "hardware_devices"
    id = db.Column(db.BigInteger, primary_key=True)
    device_code = db.Column(db.String(80), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    device_type = db.Column(db.String(30), nullable=False, default="simulator")
    status = db.Column(db.String(20), nullable=False, default="offline")
    configuration = db.Column(db.JSON, nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.BigInteger, primary_key=True)
    parking_session_id = db.Column(db.BigInteger, db.ForeignKey("parking_sessions.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    idempotency_key = db.Column(db.String(100), nullable=False, unique=True)
    provider_reference = db.Column(db.String(120), unique=True)
    paid_at = db.Column(db.DateTime)
    session = db.relationship("ParkingSession", foreign_keys=[parking_session_id])


class ParkingReservation(db.Model):
    __tablename__ = "parking_reservations"
    id = db.Column(db.BigInteger, primary_key=True)
    reservation_reference = db.Column(db.String(40), nullable=False, unique=True)
    vehicle_id = db.Column(db.BigInteger, db.ForeignKey("vehicles.id"), nullable=False, index=True)
    slot_id = db.Column(db.BigInteger, db.ForeignKey("parking_slots.id"), nullable=False, index=True)
    start_at = db.Column(db.DateTime, nullable=False, index=True)
    end_at = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="confirmed", index=True)
    notes = db.Column(db.String(250), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    slot = db.relationship("ParkingSlot", foreign_keys=[slot_id])
    vehicle = db.relationship("Vehicle", foreign_keys=[vehicle_id])
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])


class RecognitionLog(db.Model):
    __tablename__ = "recognition_logs"
    id = db.Column(db.BigInteger, primary_key=True)
    device_id = db.Column(db.BigInteger, db.ForeignKey("hardware_devices.id"), nullable=True, index=True)
    vehicle_id = db.Column(db.BigInteger, db.ForeignKey("vehicles.id"), nullable=True, index=True)
    parking_session_id = db.Column(db.BigInteger, db.ForeignKey("parking_sessions.id"), nullable=True, index=True)
    direction = db.Column(db.String(10), nullable=False, default="entry")
    recognized_text = db.Column(db.String(64), nullable=True)
    normalized_text = db.Column(db.String(32), nullable=True, index=True)
    confidence = db.Column(db.Numeric(5, 2), nullable=True)
    image_reference = db.Column(db.String(500), nullable=True)
    review_status = db.Column(db.String(20), nullable=False, default="accepted", index=True)
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    recognized_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    device = db.relationship("HardwareDevice", foreign_keys=[device_id])
    vehicle = db.relationship("Vehicle", foreign_keys=[vehicle_id])
    session = db.relationship("ParkingSession", foreign_keys=[parking_session_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_user_id])
