# WaterRower Arena

Gemeinsames Trainingslog und Live-Rennen für ein paar Freunde, die jeweils an
einem eigenen WaterRower sitzen. Der Server nimmt nur das entgegen, was die
Rudergeräte ohnehin aufzeichnen, vergleicht es und lässt Rennen laufen.

```
WaterRower S4 ──USB──► ESP32-S3 ──ausgehende WebSocket (wss)──► Arena ◄── Browser
                       (waterrower-mqtt,                        │
                        Branch esp-only)                        └── SQLite (/data/arena.db)
```

Die Rudergeräte bauen die Verbindung **nach außen** auf. Niemand braucht
Portfreigaben; mit einem Cloudflare Tunnel (siehe `docker-compose.yml`) braucht
der Server nicht einmal eine öffentliche IP.

## Was die Arena kann

- **Athleten und Einladungen:** Der Admin legt Athleten an und gibt ihnen einen
  einmaligen Einladungslink. Jeder wählt sein Passwort selbst (mindestens 12 Zeichen, davon drei der vier Arten Kleinbuchstabe, Großbuchstabe, Ziffer, Sonderzeichen).
- **Geräte-Token:** Jeder Athlet erzeugt für sein Rudergerät einen Token
  (*Konto → Tracker-Verbindung*). Er wird nur einmal angezeigt und nur als Hash gespeichert.
- **Live-Ansicht:** Wer gerade rudert, erscheint mit Distanz, Tempo, Schlagzahl und Watt.
- **Rennen** (der Admin richtet sie ein, rudert aber selbst nicht mit; dafür braucht er ein zweites Konto): Distanz (wer zuerst da ist), Zeit (wer am weitesten kommt) oder frei.
  Dazu **Geister**: eine aufgezeichnete Einheit läuft gegen die Rennuhr mit. Die
  Rennuhr gehört dem Server, Ziellinien werden zwischen zwei Messwerten interpoliert.
  Jedes Rudergerät bekommt Countdown, eigenen Platz und Abstand zugeschickt.
- **Bestleistungen:** schnellste 500 m / 1 / 2 / 5 / 10 km und weiteste Strecke in
  5 / 10 / 20 / 30 / 60 Minuten, auch aus dem Teilstück einer längeren Einheit.
- **Abzeichen:** Der Admin baut sie in der Oberfläche aus Kennzahl und Schwellwert,
  Prüfung nur auf dem Server.
- **Verlauf und Export:** Einheiten pro Athlet, Kopf-an-Kopf-Statistik, Excel
  (eine Einheit mit Diagrammen, oder alle in einer Tabelle) und CSV.
- **Backup:** konsistente Kopie der ganzen Datenbank per Klick (nur Admin).
- **Schutz vor Raten:** Sperren für Anmeldung, Einladungscodes und Geräte-Verbindungen,
  im Admin-Bereich einstellbar.

## Schnellstart

Voraussetzung: Docker mit Compose. Für den Tunnel ein Cloudflare-Konto; ohne
Tunnel siehe [Betrieb](docs/betrieb.md#ohne-cloudflare-tunnel).

```bash
git clone https://github.com/MojoOne1/waterrower-arena
cd waterrower-arena
cp .env.example .env        # ARENA_ADMIN_PASSWORD und TUNNEL_TOKEN eintragen
docker compose up -d --build
```

Im Cloudflare-Tunnel zeigt der öffentliche Hostname (z. B. `arena.example.com`)
auf `http://arena:8090`. Danach mit `admin` und dem Passwort aus der `.env` anmelden.

**Ein Rudergerät anbinden:** Athlet anlegen und einladen, dann Token unter
*Konto → Tracker-Verbindung* erzeugen. Im ESP (Weboberfläche, Karte *Arena*) **Adresse** (`https://arena.example.com`)
und **Token** eintragen und aktivieren. Der ESP schickt danach live mit und sendet
verpasste Einheiten nach.

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/betrieb.md](docs/betrieb.md) | Installation, Tunnel oder eigener Proxy, alle Einstellungen, Backup, Update, Passwort vergessen, Fehlersuche |
| [docs/protokoll.md](docs/protokoll.md) | WebSocket-Protokoll zwischen Rudergerät und Arena (für eigene Clients) |
| [docs/api.md](docs/api.md) | HTTP-API der Weboberfläche und Rechte pro Endpunkt |
| [tests/README.md](tests/README.md) | Tests |

## Aufbau

| Pfad | Inhalt |
|---|---|
| `server/app/main.py` | FastAPI-App, Start, `/ws/uplink` (Geräte) und `/ws/live` (Browser) |
| `server/app/ingest.py` | Uplink-Protokoll: Anmeldung, Messwerte, Zusammenfassung, Nachsenden |
| `server/app/race.py` | Rennmaschine (Modi, Geister, Rennuhr, Zielzeit) |
| `server/app/hub.py` | Live-Zustand aller Athleten, Verteilung an Browser, Befehle ans Gerät |
| `server/app/api.py` | HTTP-API |
| `server/app/auth.py` | Passwörter (scrypt), Sitzungen, Sperren, Token-Hashes |
| `server/app/db.py` | SQLite-Schema und Zugriffe (WAL) |
| `server/app/records.py`, `achievements.py` | Bestleistungen, Abzeichen |
| `server/app/xlsx_export.py` | Excel-Export |
| `server/app/static/` | Weboberfläche (reines JavaScript, kein Build-Schritt) |
| `server/Dockerfile` | Image (Python 3.12, uvicorn) mit Healthcheck auf `/api/health` |

## Entwickeln ohne Docker

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r server/requirements.txt httpx
cd server/app
DB_PATH=/tmp/arena.db ARENA_ADMIN_PASSWORD='mindestens-12-zeichen' ARENA_SECURE_COOKIES=0 \
  uvicorn main:app --port 8090
```

`ARENA_SECURE_COOKIES=0` ist nötig, solange du über `http://` zugreifst, sonst
verwirft der Browser das Anmelde-Cookie. Tests: `python tests/run_all.py`.

## Herkunft

Aus [MojoOne1/waterrower-mqtt](https://github.com/MojoOne1/waterrower-mqtt)
herausgelöst (Stand: Branch `esp-only`, Server unverändert bis auf die
Eingabeprüfung im Uplink). Die Firmware für die Rudergeräte bleibt dort. Die
frühere Git-Historie des Servers liegt in jenem Repository.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
