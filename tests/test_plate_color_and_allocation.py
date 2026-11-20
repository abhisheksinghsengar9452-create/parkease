import numpy as np
import pytest
from app import create_app, db
from models import ParkingSlot, ParkingSession, User, Vehicle
from services.recognition import detect_plate_color
from services.rto_decoder import decode_indian_plate
from services.parking import create_entry


def test_plate_color_detection_green_ev():
    """Test optical detection of Green Indian EV number plates."""
    crop = np.full((60, 200, 3), (35, 145, 35), dtype=np.uint8)  # Forest Green in BGR
    color, name, ratio = detect_plate_color(crop)
    assert color == "green"
    assert "Electric Vehicle" in name
    assert ratio > 0.5


def test_plate_color_detection_yellow_transport():
    """Test optical detection of Yellow Indian Commercial Transport number plates."""
    crop = np.full((60, 200, 3), (0, 215, 255), dtype=np.uint8)  # Yellow in BGR
    color, name, ratio = detect_plate_color(crop)
    assert color == "yellow"
    assert "Commercial" in name
    assert ratio > 0.5


def test_plate_color_detection_white_private():
    """Test optical detection of White Indian Private / Petrol / Diesel number plates."""
    crop = np.full((60, 200, 3), (240, 240, 240), dtype=np.uint8)  # White in BGR
    color, name, ratio = detect_plate_color(crop)
    assert color == "white"
    assert "Private" in name or "Petrol" in name
    assert ratio > 0.5


def test_rto_decoder_with_plate_colors():
    """Test that Indian MoRTH series decoder accurately incorporates plate colors."""
    # White plate private
    res_white = decode_indian_plate("DL04CA8821", detected_color="white")
    assert res_white["plate_color"] == "white"
    assert res_white["allowed_slot_type"] == "standard"
    assert not res_white["is_ev"]

    # Green plate EV
    res_green = decode_indian_plate("DL04CA8821", detected_color="green")
    assert res_green["plate_color"] == "green"
    assert res_green["allowed_slot_type"] == "ev"
    assert res_green["is_ev"]

    # Yellow plate commercial
    res_yellow = decode_indian_plate("DL04CA8821", detected_color="yellow")
    assert res_yellow["plate_color"] == "yellow"
    assert res_yellow["allowed_slot_type"] == "transport"
    assert res_yellow["is_commercial"]


@pytest.fixture
def test_app():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    with app.app_context():
        # Setup clean dedicated test slots with 0- prefix to sort first
        slots = []
        for code, stype in [("0-TEST-DIS", "disabled"), ("0-TEST-EV", "ev"), ("0-TEST-STD", "standard")]:
            s = ParkingSlot.query.filter_by(slot_code=code).first()
            if not s:
                s = ParkingSlot(slot_code=code, zone="TestZone", status="available", slot_type=stype)
                db.session.add(s)
            else:
                ParkingSession.query.filter_by(slot_id=s.id).delete()
                s.status = "available"
            slots.append(s)
        db.session.commit()
        yield app

        # Cleanup
        for s in slots:
            ParkingSession.query.filter_by(slot_id=s.id).delete()
            db.session.delete(s)
        for p in ["DL01DIS001", "UP14PETROL1", "DL01PETROL9", "DL01PWD999", "MH02EV8888"]:
            v = Vehicle.query.filter_by(normalized_registration=p).first()
            if v:
                ParkingSession.query.filter_by(vehicle_id=v.id).delete()
                db.session.delete(v)
        db.session.commit()


def test_slot_allocation_pwd_disabled_gets_disabled_slot(test_app):
    """Person with Disability (PwD) must be prioritized and allocated disabled slots."""
    with test_app.app_context():
        session = create_entry("DL01DIS001", is_disabled=True)
        assert session.slot.slot_type == "disabled"
        assert session.slot.slot_code == "0-TEST-DIS"
        assert "Accessible" in session.vehicle.vehicle_type or "PwD" in session.vehicle.vehicle_type


def test_slot_allocation_petrol_diesel_cannot_take_disabled_or_ev(test_app):
    """Petrol/Diesel vehicles must ONLY park in standard bays, NEVER in EV or Disabled bays."""
    with test_app.app_context():
        session = create_entry("UP14PETROL1", is_disabled=False, plate_color="white")
        assert session.slot.slot_type == "standard"
        assert session.slot.slot_code == "0-TEST-STD"


def test_petrol_diesel_rejected_when_only_ev_and_disabled_available(test_app):
    """When only EV and Disabled slots are available, Petrol/Diesel vehicle is rejected with clear error."""
    with test_app.app_context():
        # Ensure all standard slots are occupied so only EV and Disabled remain available
        std_slots = ParkingSlot.query.filter_by(slot_type="standard", status="available").all()
        for s in std_slots:
            s.status = "occupied"
        db.session.commit()

        try:
            # Attempt to enter normal Petrol/Diesel vehicle
            with pytest.raises(ValueError, match="No standard parking slots available for Petrol/Diesel"):
                create_entry("DL01PETROL9", is_disabled=False, plate_color="white")

            # But a PwD driver CAN enter and claim the disabled slot!
            pwd_session = create_entry("DL01PWD999", is_disabled=True)
            assert pwd_session.slot.slot_type == "disabled"
            assert pwd_session.slot.slot_code == "0-TEST-DIS"
        finally:
            for s in std_slots:
                s.status = "available"
            db.session.commit()


def test_ev_green_plate_gets_ev_slot(test_app):
    """Electric Vehicles with Green Plates are allocated to EV Charging bays."""
    with test_app.app_context():
        session = create_entry("MH02EV8888", is_disabled=False, plate_color="green")
        assert session.slot.slot_type == "ev"
        assert session.slot.slot_code == "0-TEST-EV"
        assert "Electric Vehicle" in session.vehicle.vehicle_type
