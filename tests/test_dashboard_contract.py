from pathlib import Path


def test_dashboard_api_uses_database_read_model():
    source = Path('app.py').read_text(encoding='utf-8')
    assert 'dashboard_summary()' in source
    assert 'services.dashboard' in source
