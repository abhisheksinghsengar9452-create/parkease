-- ParkEase MySQL 8.0+ application schema. Run after 00_create_database.sql
-- and 01_users.sql while connected to the `parkease` database.

CREATE TABLE IF NOT EXISTS vehicles (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    registration_number VARCHAR(32) NOT NULL,
    normalized_registration VARCHAR(32) NOT NULL UNIQUE,
    vehicle_type VARCHAR(30) NULL,
    owner_name VARCHAR(100) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_vehicles_normalized_registration (normalized_registration)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS parking_slots (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    slot_code VARCHAR(20) NOT NULL UNIQUE,
    zone VARCHAR(40) NULL,
    status ENUM('available','occupied','maintenance','unavailable') NOT NULL DEFAULT 'available',
    sensor_identifier VARCHAR(100) NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_slots_status_zone (status, zone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pricing_rules (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    hourly_rate DECIMAL(10,2) NOT NULL,
    minimum_charge DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    billing_increment_minutes SMALLINT UNSIGNED NOT NULL DEFAULT 60,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from DATETIME NOT NULL,
    effective_to DATETIME NULL,
    created_by_user_id INT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_pricing_rate CHECK (hourly_rate >= 0),
    CONSTRAINT ck_pricing_increment CHECK (billing_increment_minutes > 0),
    CONSTRAINT fk_pricing_creator FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX ix_pricing_active_effective (is_active, effective_from, effective_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS parking_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_reference VARCHAR(40) NOT NULL UNIQUE,
    vehicle_id BIGINT UNSIGNED NOT NULL,
    slot_id BIGINT UNSIGNED NULL,
    pricing_rule_id BIGINT UNSIGNED NULL,
    entry_at DATETIME NOT NULL,
    exit_at DATETIME NULL,
    status ENUM('active','awaiting_payment','closed','cancelled') NOT NULL DEFAULT 'active',
    calculated_charge DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    entry_operator_id INT UNSIGNED NULL,
    exit_operator_id INT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active_vehicle_key BIGINT UNSIGNED GENERATED ALWAYS AS (CASE WHEN status IN ('active','awaiting_payment') THEN vehicle_id ELSE NULL END) STORED,
    active_slot_key BIGINT UNSIGNED GENERATED ALWAYS AS (CASE WHEN status IN ('active','awaiting_payment') THEN slot_id ELSE NULL END) STORED,
    CONSTRAINT fk_session_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    -- slot_id participates in the generated active_slot_key, so MySQL cannot
    -- apply ON DELETE SET NULL here. Preserve historical session integrity.
    CONSTRAINT fk_session_slot FOREIGN KEY (slot_id) REFERENCES parking_slots(id) ON DELETE RESTRICT,
    CONSTRAINT fk_session_pricing FOREIGN KEY (pricing_rule_id) REFERENCES pricing_rules(id) ON DELETE SET NULL,
    CONSTRAINT fk_session_entry_operator FOREIGN KEY (entry_operator_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_session_exit_operator FOREIGN KEY (exit_operator_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_session_exit_after_entry CHECK (exit_at IS NULL OR exit_at >= entry_at),
    UNIQUE KEY uq_active_session_per_vehicle (active_vehicle_key),
    UNIQUE KEY uq_active_session_per_slot (active_slot_key),
    INDEX ix_sessions_status_entry (status, entry_at),
    INDEX ix_sessions_vehicle_entry (vehicle_id, entry_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS payments (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    parking_session_id BIGINT UNSIGNED NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    method ENUM('cash','card','upi','online','other') NOT NULL,
    status ENUM('pending','paid','failed','refunded','void') NOT NULL DEFAULT 'pending',
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    provider_reference VARCHAR(120) NULL UNIQUE,
    received_by_user_id INT UNSIGNED NULL,
    paid_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_payment_amount CHECK (amount >= 0),
    CONSTRAINT fk_payment_session FOREIGN KEY (parking_session_id) REFERENCES parking_sessions(id),
    CONSTRAINT fk_payment_user FOREIGN KEY (received_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX ix_payments_session_status (parking_session_id, status),
    INDEX ix_payments_paid_at (paid_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS hardware_devices (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_code VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    device_type ENUM('camera','barrier','slot_sensor','gateway','simulator') NOT NULL,
    status ENUM('online','offline','degraded','maintenance') NOT NULL DEFAULT 'offline',
    configuration JSON NULL,
    last_seen_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_devices_type_status (device_type, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recognition_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT UNSIGNED NULL,
    vehicle_id BIGINT UNSIGNED NULL,
    parking_session_id BIGINT UNSIGNED NULL,
    direction ENUM('entry','exit','unknown') NOT NULL DEFAULT 'unknown',
    recognized_text VARCHAR(64) NULL,
    normalized_text VARCHAR(32) NULL,
    confidence DECIMAL(5,2) NULL,
    image_reference VARCHAR(500) NULL,
    review_status ENUM('pending','accepted','corrected','rejected') NOT NULL DEFAULT 'pending',
    reviewed_by_user_id INT UNSIGNED NULL,
    recognized_at DATETIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_recognition_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 100),
    CONSTRAINT fk_recognition_device FOREIGN KEY (device_id) REFERENCES hardware_devices(id) ON DELETE SET NULL,
    CONSTRAINT fk_recognition_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL,
    CONSTRAINT fk_recognition_session FOREIGN KEY (parking_session_id) REFERENCES parking_sessions(id) ON DELETE SET NULL,
    CONSTRAINT fk_recognition_reviewer FOREIGN KEY (reviewed_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX ix_recognition_text_time (normalized_text, recognized_at),
    INDEX ix_recognition_review_time (review_status, recognized_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS device_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT UNSIGNED NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    severity ENUM('info','warning','error','critical') NOT NULL DEFAULT 'info',
    payload JSON NULL,
    occurred_at DATETIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_device_event_device FOREIGN KEY (device_id) REFERENCES hardware_devices(id),
    INDEX ix_device_events_device_time (device_id, occurred_at),
    INDEX ix_device_events_severity_time (severity, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id VARCHAR(80) NULL,
    details JSON NULL,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX ix_audit_entity (entity_type, entity_id),
    INDEX ix_audit_user_time (user_id, occurred_at),
    INDEX ix_audit_action_time (action, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
