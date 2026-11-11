# Uplink protocol (rowing device ↔ arena)

[🇩🇪 Deutsch](../docs_de/protokoll.md) · 🇬🇧 English

Each rowing device keeps **one WebSocket connection** to the arena:

```
wss://<arena>/ws/uplink        (or ws:// for an http address)
```

All messages are JSON text frames with a `type` field. The reference implementation of
the device side is `firmware/src/uplink.c` in the repository
[MojoOne1/waterrower-esp](https://github.com/MojoOne1/waterrower-esp), that of the server
side is `server/app/ingest.py`. The protocol has no version number; unknown messages and
fields are ignored.

## Flow

```
Device                                  Arena
  │── hello {token, agent} ───────────────►│   deadline: 15 s, otherwise disconnected
  │◄───────── welcome {athlete, server_time, known}
  │── sample … (1 Hz during a workout) ────►│
  │── summary (workout ended) ─────────────►│
  │── backfill {…, samples:[…]} ──────────►│   for workouts the arena does not have
  │◄───────── ack {session, stored}
  │◄───────── cmd {cmd: "reset"|"end"|"race"}
  │◄───────── ping   ── pong ─────────────►│   every 20 s
```

## Device → arena

### `hello`

```json
{"type": "hello", "token": "<device-token>", "agent": "waterrower-esp/3.0.0-esp"}
```

Must be the first message. `agent` is free text (truncated to 80 characters) and appears
in the arena next to the athlete.

### `sample`

One sample per second during a running workout.

```json
{"type": "sample", "session": "20261111T184500", "started_at": 1762886700, "t": 42,
 "distance_m": 180, "speed_ms": 4.31, "stroke_rate": 24, "strokes": 84, "watts": 140}
```

| Field | Meaning |
|---|---|
| `session` | ID of the workout **from the device's point of view**, 1–64 printable characters. One value per workout and device; the arena assigns it to the athlete. |
| `started_at` | Start of the workout, Unix seconds (up to the year 2100). If missing or invalid the arena uses `now − t`. |
| `t` | Seconds since the start of the workout (integer, at most 7 days) |
| `distance_m`, `speed_ms`, `stroke_rate`, `strokes`, `watts` | Numbers. Any other kind (text, boolean, NaN) or a value outside 0 … 10,000,000 is discarded and not stored. `distance_m` and `strokes` become integers. |

The arena trusts the device's clock only for these seconds since the start. **The race
clock belongs to the server**: progress in a race is placed by the arrival time of the
samples, and the finish time is interpolated between the two samples that enclose the line.

### `summary`

Ends the workout; the ESP sends it at the end of every workout. If the arena did not get
all samples live (the connection was down in between), the ESP additionally delivers the
complete workout later via `backfill`.

```json
{"type": "summary", "session": "20261111T184500", "started_at": 1762886700,
 "distance_m": 2000, "duration_s": 480, "strokes": 190, "avg_speed_ms": 4.17, "avg_spm": 23.7}
```

`duration_s` is capped at 7 days, `avg_speed_ms` and `avg_spm` at 0 … 1000. After closing,
the arena computes personal bests and checks badges.

### `backfill`

A complete workout after the fact, e.g. when the device was offline.

```json
{"type": "backfill", "session": "20261110T071500", "started_at": 1762758900, "ended_at": 1762759380,
 "summary": {"distance_m": 2000, "duration_s": 480, "strokes": 190, "avg_speed_ms": 4.17, "avg_spm": 23.7},
 "samples": [{"t": 0, "distance_m": 0, "speed_ms": 0, "stroke_rate": 0, "strokes": 0, "watts": 0}, …]}
```

At most **20,000** samples per message; more (or a missing/invalid `session`) is answered
with `ack` and `stored: false`. A `session` the arena already knows is **supplemented, not
replaced**: samples for seconds that are already stored are ignored, missing ones are
added, the summary is set anew. So a backfill can safely be repeated.

### `sync`

Asks which workouts the arena already has. Answer: `known`.

### `pong`

Answer to `ping`. Every incoming message also updates the "last seen" time.

## Arena → device

### `welcome`

```json
{"type": "welcome", "athlete": {"id": 3, "name": "jan", "display_name": "Jan", "color": "#2a78d6", …},
 "server_time": 1762886712.4, "known": ["20261110T071500", …]}
```

`athlete` contains `id`, `name`, `display_name`, `color` and `is_admin`. `known` lists the
device IDs of all workouts the arena has stored for this athlete (the newest 500). An ID
is listed even if the workout is incomplete, so `known` only says "I know it", not "I have
it completely". The ESP does not evaluate the list; it keeps its own record of which
workouts the arena confirmed via `ack` and sends only the rest via `backfill`.

### `ack`

```json
{"type": "ack", "session": "20261110T071500", "stored": true}
```

Confirms a `backfill`. Only with `stored: true` may the device mark the workout as
transferred.

### `known`

Answer to `sync`: `{"type": "known", "known": ["…"]}`.

### `cmd`

| `cmd` | Effect on the device |
|---|---|
| `reset` | Close the workout and set the monitor to zero, **before** a race starts |
| `end` | Close the workout, keep the display, **after** the finish |
| `race` | Race data for this device (see below); `race: null` means no race is running |

The `race` message contains only this rowing device's slice, not the whole field:

```json
{"type": "cmd", "cmd": "race", "race": {
  "state": "running", "name": "2 km Sunday", "mode": "distance", "target": 2000,
  "elapsed": 61.4, "countdown_in": null, "place": 1, "progress": 255.0,
  "gap_m": 0.0, "finished": false, "time_s": null, "lanes": 3}}
```

`state` is `countdown`, `running` or `finished`; `mode` is `distance`, `time` or `free`.
It is sent on every change, never the same thing twice.

### `ping`

Every 20 seconds so the tunnel does not drop the connection as idle. The device answers
with `pong`.

## Close codes

| Code | Reason | ESP behaviour |
|---|---|---|
| 4401 | first message was not a valid `hello` | waits 20 minutes |
| 4403 | token unknown or revoked | waits 20 minutes |
| 4429 | too many failed attempts from this address, locked | waits 20 minutes |
| other | connection gone | reconnects with backoff 3 → 60 seconds |

The lockout for failed attempts (default: 10 in 15 minutes) can be changed in the admin
area, see [Operation](operation.md#lockouts).

## `/ws/live` (browser)

Not for devices. The web UI subscribes with it to live tiles, race ticks and new
workouts; sign-in is via the `arena_session` cookie, and without a valid cookie the arena
closes with 4401. The format is internal and may change.

## Writing your own client

1. Create a token (*Account → Tracker connection*).
2. Connect, send `hello`, wait for `welcome`.
3. Send `sample` every second; `summary` at the end.
4. After connecting, deliver workouts not listed in `known` via `backfill` and wait for `ack`.
5. Answer `ping` with `pong`; do not reconnect immediately on 4401/4403/4429.
