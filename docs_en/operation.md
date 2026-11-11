# Operation

[🇩🇪 Deutsch](../docs_de/betrieb.md) · 🇬🇧 English

## Contents

- [Requirements](#requirements)
- [Installation with Cloudflare Tunnel](#installation-with-cloudflare-tunnel)
- [Without Cloudflare Tunnel](#without-cloudflare-tunnel)
- [First steps in the arena](#first-steps-in-the-arena)
- [Settings](#settings)
- [Data and backup](#data-and-backup)
- [Update](#update)
- [Forgotten password](#forgotten-password)
- [Lockouts](#lockouts)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## Requirements

- Docker with the Compose plugin (`docker compose`), architecture amd64 or arm64
- A place where the container can run permanently (VM, mini PC, NAS, Raspberry Pi)
- For the tunnel: a Cloudflare account with a domain. Alternatively your own reverse proxy with HTTPS.

The rowing devices contact the arena at an `https://` address over `wss://` and verify
the certificate against public certificate authorities; the ESP does not accept
self-signed certificates. If you give the ESP an `http://` address it talks unencrypted
over `ws://`. That is meant for tests on the home network, not for the path over the
internet.

## Installation with Cloudflare Tunnel

1. In Cloudflare Zero Trust create a tunnel under *Networks → Tunnels* and copy the token.
2. In the tunnel create a **Public Hostname**, e.g. `arena.example.com`, with the
   service `http://arena:8090` (`arena` is the container name in the Compose network).
3. Fetch the repository and create `.env`:

   ```bash
   git clone https://github.com/MojoOne1/waterrower-arena
   cd waterrower-arena
   cp .env.example .env
   ```

   Set in `.env`: `ARENA_ADMIN_PASSWORD` (at least 12 characters, three of the four kinds
   lower case, upper case, digit, special character; a weaker password is flagged in the
   log) and `TUNNEL_TOKEN`.
4. Start:

   ```bash
   docker compose up -d --build
   docker compose logs -f arena      # check the start
   ```

5. Open `https://arena.example.com` and sign in with `admin` and the password from `.env`.

The container runs with `no-new-privileges`; the database lives in the volume
`./server/data` (`/data` in the container). The healthcheck queries `/api/health`, which
also reads the database, so a broken volume shows up as `unhealthy` (`docker compose ps`).

## Without Cloudflare Tunnel

The Compose file demands `TUNNEL_TOKEN` as long as the `cloudflared` service is in it,
even if you only start the arena. If you use your own reverse proxy (Caddy, Traefik,
nginx, Nginx Proxy Manager …):

1. Delete the whole `cloudflared:` block from `docker-compose.yml`.
2. Publish a port on the `arena` service, ideally only locally or in the proxy's network:

   ```yaml
       ports:
         - "127.0.0.1:8090:8090"
   ```

3. Point the proxy at `http://127.0.0.1:8090`. **WebSocket forwarding must be on**; the
   paths `/ws/uplink` and `/ws/live` need it. Long idle times are fine: arena and devices
   ping each other every 20 seconds.
4. If the proxy is another machine or container, restrict forwarding of the client address
   (see `ARENA_TRUSTED_PROXIES` below).

**For testing over `http://` only:** publish the port as above (without `127.0.0.1:` if you
access it from another machine) and set `ARENA_SECURE_COOKIES=0` in `.env`. With the value
`1` the browser discards the sign-in cookie over `http://` and the login does not "stick".
In this case you can give the ESP `http://<host>:8090` as the address.

## First steps in the arena

1. Sign in as `admin` and create athletes under *Account → Athletes*: user name (2–32
   characters, lower-cased) and display name. The arena shows an **invitation link** of the
   form `https://arena.example.com/#join?code=…`.
2. The athlete opens the link and chooses a password. The code works once. If someone
   forgot their password, the admin clicks *Reset password*: that deletes the old password
   and creates a new invitation link.
   **Important:** an admin account sets up races but **does not row**: it cannot join a
   race and creates no lane of its own when creating one. Whoever wants to row needs an
   additional normal athlete account without admin rights.
3. Each athlete creates a **token** for their rowing device under *Account → Tracker
   connection*. The token is shown only once; if lost, create a new one and revoke the old one.
4. In the ESP (web UI → *Arena* card) enter the address and token and enable it. The
   athlete then appears online in the arena.

## Settings

All settings are environment variables of the container. **The Compose file only passes
through these:** `TZ`, `ARENA_ADMIN_USER`, `ARENA_ADMIN_NAME`, `ARENA_ADMIN_PASSWORD`,
`ARENA_ADMIN_RESET`, `ARENA_SECURE_COOKIES`. Everything else in the table you must add
yourself under `environment:` of the `arena` service, e.g. `ARENA_COUNTDOWN: "15"`.

| Variable | Default | Meaning |
|---|---|---|
| `ARENA_ADMIN_PASSWORD` | – | Password of the first admin. Only read while the account does not exist yet (or with `ARENA_ADMIN_RESET=1`). Without a password the server starts but stays locked and says so in the log. |
| `ARENA_ADMIN_USER` | `admin` | User name of the first admin |
| `ARENA_ADMIN_NAME` | `Admin` | Display name |
| `ARENA_ADMIN_RESET` | `0` | `1` resets the admin account's password to `ARENA_ADMIN_PASSWORD` on start ([Forgotten password](#forgotten-password)) |
| `ARENA_SECURE_COOKIES` | `1` | Only the value `0` switches off the Secure flag on the cookie |
| `ARENA_SESSION_DAYS` | `30` | Lifetime of a browser sign-in |
| `ARENA_UPLINK_TIMEOUT` | `50` | Seconds of silence until a device counts as offline |
| `ARENA_END_AT_FINISH` | `0` | `1` ends all participants' workouts at the finish. Default: everyone ends their own, because whoever is across the line often keeps rowing out. |
| `ARENA_COUNTDOWN` | `10` | Seconds of countdown before the start |
| `ARENA_TICK_HZ` | `2` | How many times per second race data goes to the browsers |
| `ARENA_FINISH_GRACE` | `600` | Seconds stragglers get after the winner before the race is scored |
| `ARENA_TRUSTED_PROXIES` | `*` | Whose `X-Forwarded-For` is believed (list of IPs/networks for uvicorn). `*` is only safe if solely the tunnel/proxy can reach the port; otherwise anyone could put any address in the header and bypass all lockouts. |
| `ARENA_LOGIN_IP_LIMIT` / `_MINUTES` | `10` / `15` | Sign-in attempts per address, then locked for that many minutes |
| `ARENA_LOGIN_NAME_LIMIT` / `_MINUTES` | `30` / `15` | Failed attempts against one account from anywhere. Deliberately looser, because it could be used to lock someone out. |
| `ARENA_INVITE_IP_LIMIT` / `_MINUTES` | `10` / `60` | Wrong invitation codes per address |
| `ARENA_UPLINK_IP_LIMIT` / `_MINUTES` | `10` / `15` | Device connections with an invalid token per address |
| `DB_PATH` | `/data/arena.db` | Path of the SQLite database |
| `TZ` | `Europe/Berlin` (Compose) | Time zone for displayed times |

The limits are only **initial values**: what an admin saves in the admin area under
*Security* is stored in the database and applies from then on. A limit of `0` switches the
respective lockout off.

## Data and backup

Everything lives in one SQLite file: `./server/data/arena.db` (athletes, workouts,
samples, races, badges, settings).

**Backup:** as admin download under *Account → Backup → Download database*
(`GET /api/backup`). This is deliberately not a file copy: the database runs in WAL mode,
the newest rows sit in `arena.db-wal`, and copying only `arena.db` can yield a stale or
damaged file. The backup file contains password hashes and invitation codes and belongs in
a private place.

**Restore:** stop the container (`docker compose stop arena`), put the file in place as
`server/data/arena.db`, remove any existing `arena.db-wal` and `arena.db-shm`, start the
container.

**Delete a single workout:** in the arena. Excel/CSV export per workout or for all is
available to every signed-in athlete.

## Update

```bash
cd waterrower-arena
git pull
docker compose up -d --build
```

The database stays in the volume. The UI shows the version (endpoint `/api/version`,
signed in only).

Optionally the workflow `.github/workflows/docker-publish.yml` builds the image on every
push to `main` for amd64 and arm64 and publishes it as
`ghcr.io/mojoone1/waterrower-arena/arena` (tags `latest`, version from `VERSION`, and
commit). New packages on GHCR are private at first; to pull without signing in, set the
package to public in the GitHub package settings. The Compose file still uses
`build: ./server`.

## Forgotten password

Admin: set a new `ARENA_ADMIN_PASSWORD` in `.env` and `ARENA_ADMIN_RESET=1`, then
`docker compose up -d`. The account keeps its workouts; only the password and all open
browser sign-ins disappear. **Afterwards set `ARENA_ADMIN_RESET` back to `0`**, otherwise
the password from the file is set again on every restart.

Other athletes: the admin resets the password under *Account → Athletes* and passes on the
new invitation link.

## Lockouts

The arena locks an address or an account after too many failed attempts (values above).
Admins see the lockouts in the account area under *Security* and can lift them there one
by one or with *Lift all lockouts*. If you are the only admin and lock yourself out, wait
for the lock time to pass or restart the container: the counters live only in memory and
are gone afterwards.

A rowing device with a wrong token is disconnected with code 4403 (4401: no valid
`hello`, 4429: locked). The ESP then waits 20 minutes before trying again so it does not
lock itself out.

## Security

- Passwords: scrypt with salt, at least 12 characters and three of the four character
  kinds. Old, weaker hashes are renewed at the next login.
- Browser sign-in: cookie `arena_session`, `HttpOnly`, `SameSite=Lax`, `Secure` (except
  with `ARENA_SECURE_COOKIES=0`).
- Device tokens: 256 bit, stored in the database only as a hash, visible only once.
- Device input: samples are checked for type and value range before storing (no text,
  NaN or absurd numbers), workout IDs are limited to 64 printable characters, re-sending to
  20,000 samples per workout.
- The container runs with `no-new-privileges`. The arena has no TLS terminator; HTTPS
  comes from the tunnel or your proxy.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Sign-in seems to work but does not persist | Access over `http://` with `ARENA_SECURE_COOKIES=1`. Either use HTTPS or set `ARENA_SECURE_COOKIES=0` for testing. |
| `docker compose` aborts with "required variable TUNNEL_TOKEN is missing" | Enter `TUNNEL_TOKEN` in `.env` or delete the `cloudflared` block ([Without Cloudflare Tunnel](#without-cloudflare-tunnel)). |
| `ARENA_ADMIN_PASSWORD` missing | The server starts but nobody can get in; the log says so. Enter it in `.env`, restart. |
| Device stays offline | In the ESP under *Arena* check address and token. The address looks like `https://arena.example.com`, without a path (the ESP appends `/ws/uplink` itself). With code 4403 the token is invalid or revoked, with 4429 the arena has locked the address. The ESP then waits 20 minutes. |
| Device online but workouts missing | The ESP re-sends missed workouts on the next connect (*backfill*). The arena log shows `Backfilled …` per workout. |
| Times shifted by hours | Check `TZ` in the container and the time zone in the ESP. Unix times are stored; `TZ` only affects the display. |
| Race hangs after the winner | Stragglers get `ARENA_FINISH_GRACE` seconds (default 600). The admin can abort or finish the race. |
| Tunnel shows 502 | The hostname in the tunnel must point to `http://arena:8090` and both containers must run in the same Compose project. Check with `docker compose ps`. |
