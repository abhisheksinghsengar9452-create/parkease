# ParkEase — Phase 0.5 UI Foundation

A Flask/Jinja dashboard prototype with a Three.js interactive 3D lot and simulated ANPR, sessions, billing, and IoT telemetry. It is intentionally hardware- and database-independent.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Integration seams for later phases

- Replace `DashboardState` in `app.py` with MySQL-backed repositories and service-layer transactions (Phase 5).
- Publish MQTT/camera updates into a state service or event broker; the UI consumes `/api/dashboard/state` (Phase 6–8).
- The camera pane is a stylized simulator. It does not claim to stream OpenCV frames yet.
- Barrier buttons are presentational only. They cannot operate hardware.
