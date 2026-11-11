# Tests

[🇩🇪 Deutsch](../docs_de/tests.md) · 🇬🇧 English

Two suites, no framework: each prints one line per check and exits with a non-zero code if
something failed. `run_all.py` runs them all as separate processes and summarises.

```bash
python -m pip install -r server/requirements.txt httpx
python tests/run_all.py
```

| Suite | What it covers | Needs |
|---|---|---|
| `smoke.py` | The arena in-process via FastAPI's test client: sign-in and lockouts, invitations, device tokens, a normal workout over the uplink, personal bests, races with countdown, finish and ghosts, the `reset`/`end` commands to the device, permissions, healthcheck, Excel export, backup, delivery of the UI | nothing outside the checkout |
| `uplink_protocol.py` | The [uplink protocol](protocol.md) message by message: `hello`/`welcome`/`known`, close codes 4401 and 4403, live samples and `summary`, validation and discarding of invalid values, `backfill` with `ack` (also repeated, too large, without an ID), `sync`, `ping`/`pong` | nothing outside the checkout |

Each test creates its own temporary database and does not touch `server/data`. They do not
access the network.

Deliberately **not** covered:

- **A real rowing device.** The protocol is checked with self-built messages modelled on
  the firmware (`firmware/src/uplink.c` in the repository
  [waterrower-esp](https://github.com/MojoOne1/waterrower-esp)). Only a test with hardware
  shows that the ESP really speaks like that.
- **The Docker image and the tunnel.** `docker compose config` is not run in CI; building
  the image happens only in the `docker-publish.yml` workflow.
- **A race with two real people.**

The origin repository used to have an additional `integration.py` that ran the old tracker
client against a real arena process. That client belonged to the old ESPHome variant and is
no longer included here; `uplink_protocol.py` replaces it at protocol level. The CSV export
and the chart in the Excel export are not tested specifically.
