# Phase 8 — IoT integration

`devices.base` defines driver contracts. `devices.simulator` is the default
development driver and requires no GPIO, MQTT broker, camera, or barrier.

Future GPIO, MQTT, and serial adapters must implement these same contracts.
Each command must be audited; device failures default to a closed barrier and an
operator-visible degraded/offline status.
