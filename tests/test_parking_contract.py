from pathlib import Path


def test_parking_lifecycle_uses_row_locks_and_transaction():
    source = Path('services/parking.py').read_text(encoding='utf-8')
    assert 'with_for_update()' in source
    assert 'with transaction()' in source
    assert 'Vehicle already has an active parking session.' in source
