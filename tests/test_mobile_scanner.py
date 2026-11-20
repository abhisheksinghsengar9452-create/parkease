import pytest
from app import create_app, db
from models import User
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def test_client():
    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False})
    with app.app_context():
        # Ensure an admin user exists
        u = db.session.scalar(db.select(User).where(User.email == 'admin@parkease.local'))
        if not u:
            u = User(email='admin@parkease.local', display_name='Admin', role='administrator', is_active=True)
            u.set_password('Admin@123')
            db.session.add(u)
            db.session.commit()
    with app.test_client() as client:
        # Log in
        with client.session_transaction() as sess:
            sess['user_id'] = u.id
        yield client


def test_mobile_scanner_info(test_client):
    res = test_client.get('/api/anpr/mobile-scanner-info')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'ok'
    assert 'scanner_url' in data
    assert 'qr_b64' in data
    assert len(data['qr_b64']) > 50


def test_mobile_scanner_view(test_client):
    res = test_client.get('/mobile-scanner')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'ParkEase Mobile ANPR Camera Node' in html
    assert 'cameraVideo' in html
    assert 'phoneCameraInput' in html


def test_mobile_scan_and_broadcast(test_client):
    img_path = ROOT / 'anpr_gate_capture.png'
    assert img_path.is_file()

    with open(img_path, 'rb') as f:
        img_bytes = f.read()

    from io import BytesIO
    res = test_client.post(
        '/api/anpr/mobile-scan',
        data={
            'image': (BytesIO(img_bytes), 'test.png'),
            'direction': 'entry',
            'mobile_token': 'test_token'
        },
        content_type='multipart/form-data'
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'ok'
    assert data['plate'] == 'UP14AB1234'
    assert 'rto' in data

    # Verify poller picks it up
    res_poll = test_client.get('/api/anpr/latest-mobile-scan')
    assert res_poll.status_code == 200
    poll_data = res_poll.get_json()
    assert poll_data['status'] == 'ok'
    assert poll_data['scan']['plate'] == 'UP14AB1234'
    assert poll_data['scan']['direction'] == 'entry'
    assert poll_data['scan']['thumbnail'] is not None


def test_favicon_endpoint(test_client):
    res = test_client.get('/favicon.ico')
    assert res.status_code == 200
    assert 'image' in res.content_type
