# WaterRower Arena

🇬🇧 English · 🇩🇪 Die Dokumentation gibt es auch auf Deutsch: [docs_de/](docs_de/)

A shared training log and live races for a few friends who each sit at their own
WaterRower. The server only receives what the rowing devices record anyway, compares it
and runs races.

```
WaterRower S4 ──USB──► ESP32-S3 ──outbound WebSocket (wss)──► Arena ◄── browser
                       (waterrower-esp)                        │
                                                               └── SQLite (/data/arena.db)
```

The rowing devices connect **outwards**. Nobody needs port forwarding; with a Cloudflare
Tunnel (see `docker-compose.yml`) the server does not even need a public IP. The firmware
for the devices lives in [MojoOne1/waterrower-esp](https://github.com/MojoOne1/waterrower-esp).

## What the arena does

- **Athletes and invitations:** the admin creates athletes and gives each a one-time
  invitation link. Everyone chooses their own password (at least 12 characters, three of
  the four kinds lower case, upper case, digit, special character).
- **Device tokens:** each athlete creates a token for their rowing device (*Account →
  Tracker connection*). It is shown only once and stored only as a hash.
- **Live view:** whoever is rowing right now appears with distance, pace, stroke count and watts.
- **Races** (the admin sets them up but does not row; for that they need a second
  account): distance (first there wins), time (furthest wins) or free. Plus **ghosts**: a
  recorded workout runs along against the race clock. The race clock belongs to the
  server, finish lines are interpolated between two samples. Every rowing device gets a
  countdown, its own place and the gap sent to it.
- **Personal bests:** fastest 500 m / 1 / 2 / 5 / 10 km and furthest distance in 5 / 10 /
  20 / 30 / 60 minutes, also from a part of a longer workout.
- **Badges:** the admin builds them in the UI from a metric and a threshold; checked on
  the server only.
- **History and export:** workouts per athlete, head-to-head statistics, Excel (one
  workout with charts, or all in one table) and CSV.
- **Backup:** a consistent copy of the whole database at the click of a button (admin only).
- **Protection against guessing:** lockouts for sign-in, invitation codes and device
  connections, adjustable in the admin area.

> **Real-world multiplayer is untested.** Everything works end to end and is covered by automated checks, but two people with two rowing machines racing at the same moment has not happened yet. See [Status and limits](docs_en/features.md#status-and-limits).

## Quick start

Requirement: Docker with Compose. For the tunnel a Cloudflare account; without the tunnel
see [Operation](docs_en/operation.md#without-cloudflare-tunnel).

```bash
git clone https://github.com/MojoOne1/waterrower-arena
cd waterrower-arena
cp .env.example .env        # enter ARENA_ADMIN_PASSWORD and TUNNEL_TOKEN
docker compose up -d --build
```

In the Cloudflare tunnel the public hostname (e.g. `arena.example.com`) points to
`http://arena:8090`. Then sign in with `admin` and the password from `.env`.

**Connecting a rowing device:** create and invite an athlete, then create a token under
*Account → Tracker connection*. In the ESP (web UI, *Arena* card) enter **address**
(`https://arena.example.com`) and **token** and enable it. The ESP then sends live and
re-sends missed workouts.

## Documentation

Everything is available in English (`docs_en/`) and German (`docs_de/`).

| Topic | English | Deutsch |
|---|---|---|
| Installation, tunnel or own proxy, all settings, backup, update, forgotten password, troubleshooting | [operation.md](docs_en/operation.md) | [betrieb.md](docs_de/betrieb.md) |
| Races, badges, records, limits, versioning | [features.md](docs_en/features.md) | [funktionen.md](docs_de/funktionen.md) |
| WebSocket protocol between rowing device and arena (for your own clients) | [protocol.md](docs_en/protocol.md) | [protokoll.md](docs_de/protokoll.md) |
| HTTP API of the web UI and permissions per endpoint | [api.md](docs_en/api.md) | [api.md](docs_de/api.md) |
| Tests | [tests.md](docs_en/tests.md) | [tests.md](docs_de/tests.md) |

## Code layout

| Path | Content |
|---|---|
| `server/app/main.py` | FastAPI app, startup, `/ws/uplink` (devices) and `/ws/live` (browsers) |
| `server/app/ingest.py` | Uplink protocol: sign-in, samples, summary, re-sending |
| `server/app/race.py` | Race engine (modes, ghosts, race clock, finish time) |
| `server/app/hub.py` | Live state of all athletes, distribution to browsers, commands to the device |
| `server/app/api.py` | HTTP API |
| `server/app/auth.py` | Passwords (scrypt), sessions, lockouts, token hashes |
| `server/app/db.py` | SQLite schema and access (WAL) |
| `server/app/records.py`, `achievements.py` | Personal bests, badges |
| `server/app/xlsx_export.py` | Excel export |
| `server/app/static/` | Web UI (plain JavaScript, no build step) |
| `server/Dockerfile` | Image (Python 3.12, uvicorn) with healthcheck on `/api/health` |

## Developing without Docker

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r server/requirements.txt httpx
cd server/app
DB_PATH=/tmp/arena.db ARENA_ADMIN_PASSWORD='at-least-12-chars' ARENA_SECURE_COOKIES=0 \
  uvicorn main:app --port 8090
```

`ARENA_SECURE_COOKIES=0` is needed as long as you access it over `http://`, otherwise the
browser discards the sign-in cookie. Tests: `python tests/run_all.py` ([details](docs_en/tests.md)).

## Licence

MIT, see [LICENSE](LICENSE).
