-- Optional non-production bootstrap data. Password hashes are intentionally
-- excluded: create the first administrator through `flask --app app create-admin`.
INSERT INTO pricing_rules (name, hourly_rate, minimum_charge, billing_increment_minutes, is_active, effective_from)
SELECT 'Standard hourly', 50.00, 40.00, 60, TRUE, UTC_TIMESTAMP()
WHERE NOT EXISTS (SELECT 1 FROM pricing_rules WHERE name = 'Standard hourly');

INSERT INTO parking_slots (slot_code, zone, status)
VALUES ('A-01','A','available'),('A-02','A','available'),('A-03','A','available'),('A-04','A','available'),('A-05','A','available')
ON DUPLICATE KEY UPDATE zone=VALUES(zone);
