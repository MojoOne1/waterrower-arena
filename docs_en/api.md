# HTTP API

[🇩🇪 Deutsch](../docs_de/api.md) · 🇬🇧 English

The web UI uses this API; it is not promised as a stable public interface. Everything is
JSON, sign-in is via the `arena_session` cookie (`HttpOnly`, `SameSite=Lax`).

**Permissions:** *open* = without sign-in, *signed in* = any athlete, *admin* = admins
only, *own* = only the athlete themselves or an admin.

Errors come as `{"detail": "…"}` with the matching HTTP status (401 not signed in, 403 no
permission, 404 does not exist, 409 name taken, 429 locked).

## Sign-in and account

| Method and path | Permission | Purpose |
|---|---|---|
| `GET /api/health` | open | Liveness; reads the database (container healthcheck) |
| `GET /api/version` | signed in | Version and commit |
| `GET /api/me` | signed in (otherwise 401) | own profile |
| `POST /api/login` | open, with lockouts | `{name, password}` |
| `POST /api/logout` | – | end the session |
| `POST /api/invite` | open, with lockouts | `{code}`: whom an invitation is for (POST so codes stay out of access logs) |
| `POST /api/join` | open, with lockouts | `{code, password}`: redeem invitation, set password |
| `POST /api/password` | signed in | `{old_password, password}`: change password |

## Athletes and device tokens

| Method and path | Permission | Purpose |
|---|---|---|
| `GET /api/athletes` | signed in | all athletes (without hashes and codes) |
| `POST /api/athletes` | admin | `{name, display_name, is_admin}` → athlete and invitation code |
| `PATCH /api/athletes/{id}` | own | display name, colour; admin right only by admins, the last admin stays admin |
| `POST /api/athletes/{id}/invite` | admin | new invitation code, **deletes the password** (this is the reset) |
| `DELETE /api/athletes/{id}` | admin | delete athlete |
| `GET /api/athletes/{id}/tokens` | own | tokens without plain text (`id`, `label`, `created_at`, `last_seen_at`) |
| `POST /api/athletes/{id}/tokens` | own | `{label}` → new token. The plain text appears **only in this response**. |
| `DELETE /api/athletes/{id}/tokens/{token_id}` | own | revoke token |

## Workouts, live and export

| Method and path | Permission | Purpose |
|---|---|---|
| `GET /api/sessions` | signed in | list (filters and limits as query parameters) |
| `GET /api/sessions/{id}` | signed in | workout with all samples |
| `DELETE /api/sessions/{id}` | own | delete workout |
| `GET /api/sessions/{id}/export.xlsx` | signed in | Excel: summary, samples, two charts |
| `GET /api/sessions/{id}/export.csv` | signed in | CSV |
| `GET /api/export.xlsx` | signed in | all workouts in one table plus totals |
| `GET /api/live` | signed in | current state of all athletes |
| `POST /api/session/end` | signed in | end my workout on the device (command `end`) |
| `POST /api/session/reset` | signed in | close my workout, monitor to zero (command `reset`) |
| `GET /api/records` | signed in | personal bests per athlete and standard distance/time |
| `GET /api/totals` | signed in | totals |
| `GET /api/h2h` | signed in | who beat whom in finished races |
| `GET /api/backup` | admin | whole database as a consistent SQLite file |
| `POST /api/reindex` | admin | recompute personal bests from the samples (e.g. after an import) |

## Races

There is at most one active race. Errors from the race engine come as 403 with text. Only
non-admins may join. Starting and finishing is allowed to the creator or an admin; a
foreign lane may only be removed by its owner, the creator or an admin.

| Method and path | Permission | Purpose |
|---|---|---|
| `GET /api/race` | signed in | active race |
| `POST /api/race` | signed in | create a race: `{name, mode, target, template_id}` with mode `distance`, `time` or `free` |
| `POST /api/race/join`, `/leave`, `/ready` | signed in | join, leave the lane, report ready |
| `POST /api/race/ghost` | signed in | let a recorded workout run along as a ghost |
| `POST /api/race/start` | creator/admin | countdown and start |
| `POST /api/race/finish`, `/abort` | creator/admin | score or abort |
| `POST /api/race/clear` | signed in | remove a finished race from the live view |
| `GET /api/races`, `GET /api/races/{id}` | signed in | race history |
| `DELETE /api/races/{id}` | admin | delete a race from the history |

## Badges and templates

| Method and path | Permission | Purpose |
|---|---|---|
| `GET /api/achievements` | signed in | badges (hidden ones stay a silhouette until earned) |
| `GET /api/achievements/metrics` | admin | metrics a badge can be built from |
| `POST /api/achievements` | admin | create a badge |
| `DELETE /api/achievements/{id}` | admin | delete a badge including all awards |
| `GET /api/templates` | signed in | race templates |
| `POST /api/templates`, `DELETE /api/templates/{id}` | admin | manage race templates |

## Security

| Method and path | Permission | Purpose |
|---|---|---|
| `GET /api/security`, `POST /api/security` | admin | read and change lockouts (limit 0 = off) |
| `POST /api/security/unblock` | admin | lift lockouts |

## WebSockets

| Path | Who | Description |
|---|---|---|
| `/ws/uplink` | rowing devices | [protocol](protocol.md), sign-in by device token |
| `/ws/live` | browsers | live tiles, race ticks, new workouts; sign-in by cookie |
