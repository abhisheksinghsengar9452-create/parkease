# Phase 0.5 — 3D Dashboard UI Foundation

## Purpose

Provide a runnable visual foundation ahead of the planned Phase 1 discovery and Phase 2 application setup. This layer intentionally uses simulated data; it has no authority to make billing, entry, exit, or barrier decisions.

## Data contract

`GET /api/dashboard/state` is the single dashboard read model. It returns `metrics`, `slots`, `anpr`, `devices`, and `sessions`. Later domain services may change its implementation, but should preserve this shape or version the endpoint.

## Replacement points

| Current component | Future replacement |
| --- | --- |
| `DashboardState` | MySQL repositories plus parking, billing, and reporting services |
| Fixed `snapshot()` fields | Transactionally consistent dashboard query/read model |
| Static ANPR value | Recognition event service and controlled MJPEG stream endpoint |
| Fixed device telemetry | MQTT consumer/device gateway with authenticated command service |
| Presentational barrier controls | RBAC-protected, audited, safety-checked hardware command workflow |

## Safety boundary

The prototype never opens a barrier and its buttons do not submit requests. A future barrier command needs an explicit safety policy, an authenticated user, an audit event, configured hardware, and confirmation of the correct session state.
