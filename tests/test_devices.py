import pytest
from devices.simulator import SimulatedBarrier
from services.device_control import authorize_barrier_open


def test_barrier_rejects_ocr_only_like_authorization():
    barrier = SimulatedBarrier()
    with pytest.raises(PermissionError): authorize_barrier_open(barrier, audit_reference='AUD-1')
    assert barrier.status().state == 'closed'


def test_verified_payment_can_open_simulated_exit():
    barrier = SimulatedBarrier()
    authorize_barrier_open(barrier, verified_payment=True, audit_reference='AUD-2')
    assert barrier.status().state == 'open'
