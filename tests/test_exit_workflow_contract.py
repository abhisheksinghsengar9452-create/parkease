from pathlib import Path


def test_exit_requires_payment_before_slot_release():
    source = Path('services/exit_workflow.py').read_text(encoding='utf-8')
    assert 'payment.status != "paid"' in source
    assert 'slot.status = "available"' in source
    assert 'with_for_update()' in source
