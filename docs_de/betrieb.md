# Betrieb

🇩🇪 Deutsch · [🇬🇧 English](../docs_en/operation.md)

## Inhalt

- [Voraussetzungen](#voraussetzungen)
- [Installation mit Cloudflare Tunnel](#installation-mit-cloudflare-tunnel)
- [Ohne Cloudflare Tunnel](#ohne-cloudflare-tunnel)
- [Erste Schritte in der Arena](#erste-schritte-in-der-arena)
- [Einstellungen](#einstellungen)
- [Daten und Backup](#daten-und-backup)
- [Update](#update)
- [Passwort vergessen](#passwort-vergessen)
- [Sperren](#sperren)
- [Sicherheit](#sicherheit)
- [Fehlersuche](#fehlersuche)

## Voraussetzungen

- Docker mit Compose-Plugin (`docker compose`), Architektur amd64 oder arm64
- Ein Ort, an dem der Container dauerhaft laufen kann (VM, Mini-PC, NAS, Raspberry Pi)
- Für den Tunnel: ein Cloudflare-Konto mit einer Domain. Alternativ ein eigener Reverse-Proxy mit HTTPS.

Die Rudergeräte sprechen die Arena aus einer `https://`-Adresse über `wss://` an und
prüfen das Zertifikat gegen öffentliche Zertifizierungsstellen; selbstsignierte
Zertifikate nimmt der ESP nicht an. Gibt man dem ESP eine `http://`-Adresse, spricht
er unverschlüsselt über `ws://`. Das ist für Tests im Heimnetz gedacht, nicht für
den Weg übers Internet.

## Installation mit Cloudflare Tunnel

1. In Cloudflare Zero Trust unter *Networks → Tunnels* einen Tunnel anlegen und
   den Token kopieren.
2. Im Tunnel einen **Public Hostname** anlegen, z. B. `arena.example.com`, mit dem
   Dienst `http://waterrower-arena:8090` (`waterrower-arena` ist der Name des Dienstes im Compose-Netz).
3. Repository holen und `.env` anlegen:

   ```bash
   git clone https://github.com/MojoOne1/waterrower-arena
   cd waterrower-arena
   cp .env.example .env
   ```

   In der `.env` setzen: `ARENA_ADMIN_PASSWORD` (mindestens 12 Zeichen, drei der vier
   Arten Klein-/Großbuchstabe, Ziffer, Sonderzeichen; ein schwächeres Passwort wird im
   Log bemängelt) und `TUNNEL_TOKEN`.
4. Starten:

   ```bash
   docker compose up -d --build
   docker compose logs -f waterrower-arena      # Start prüfen
   ```

5. `https://arena.example.com` öffnen, mit `admin` und dem Passwort aus der `.env` anmelden.

Der Container läuft mit `no-new-privileges`, die Datenbank liegt im Volume
`./server/data` (im Container `/data`). Der Healthcheck fragt `/api/health` ab, das
auch die Datenbank liest; ein defektes Volume zeigt sich also als `unhealthy`
(`docker compose ps`).

## Ohne Cloudflare Tunnel

Die Compose-Datei verlangt `TUNNEL_TOKEN`, solange der Dienst `cloudflared` darin
steht, auch wenn du nur die Arena startest. Wer einen eigenen Reverse-Proxy
(Caddy, Traefik, nginx, Nginx Proxy Manager …) benutzt:

1. Den kompletten Block `cloudflared:` aus `docker-compose.yml` löschen.
2. Beim Dienst `waterrower-arena` einen Port veröffentlichen, am besten nur lokal oder im
   Netz des Proxys:

   ```yaml
       ports:
         - "127.0.0.1:8090:8090"
   ```

3. Den Proxy auf `http://127.0.0.1:8090` zeigen lassen. **WebSocket-Weiterleitung
   muss an sein**, die Pfade `/ws/uplink` und `/ws/live` brauchen sie. Lange
   Leerlaufzeiten sind unkritisch: Arena und Geräte schicken sich alle 20 Sekunden
   Pings.
4. Sitzt der Proxy außerhalb der privaten Netze (z. B. auf einer öffentlichen Adresse),
   ihn in `ARENA_TRUSTED_PROXIES` eintragen (siehe unten).

**Nur zum Testen über `http://`:** Port veröffentlichen wie oben (ohne `127.0.0.1:`,
wenn du von einem anderen Rechner zugreifst) und in der `.env`
`ARENA_SECURE_COOKIES=0` setzen. Mit dem Wert `1` verwirft der Browser das
Anmelde-Cookie über `http://`, und die Anmeldung „klebt“ nicht. Dem ESP kannst du in
diesem Fall `http://<host>:8090` als Adresse geben.

## Erste Schritte in der Arena

1. Als `admin` anmelden und unter *Konto → Athleten* Athleten anlegen: Benutzername
   (2–32 Zeichen, wird kleingeschrieben) und Anzeigename. Die Arena zeigt dazu einen
   **Einladungslink** der Form `https://arena.example.com/#join?code=…`.
2. Der Athlet öffnet den Link und wählt sein Passwort. Der Code gilt nur einmal. Hat
   jemand sein Passwort vergessen, geht der Admin auf *Passwort zurücksetzen*: Das
   löscht das alte Passwort und erzeugt einen neuen Einladungslink.
   **Wichtig:** Ein Admin-Konto richtet Rennen ein, **rudert aber nicht mit**: Es kann einem
   Rennen nicht beitreten und legt beim Erstellen keine eigene Bahn an. Wer selbst
   mitrudern will, braucht zusätzlich ein normales Athletenkonto ohne Admin-Recht.
3. Jeder Athlet erzeugt unter *Konto → Tracker-Verbindung* einen **Token** für sein
   Rudergerät. Der Token wird nur einmal angezeigt; verloren heißt: neuen erzeugen,
   den alten widerrufen.
4. Im ESP (Weboberfläche → Karte *Arena*) Adresse und Token eintragen und aktivieren.
   In der Arena erscheint der Athlet danach als online.

## Einstellungen

Alle Einstellungen sind Umgebungsvariablen des Containers. **Die Compose-Datei reicht
nur diese durch:** `TZ`, `ARENA_ADMIN_USER`, `ARENA_ADMIN_NAME`, `ARENA_ADMIN_PASSWORD`,
`ARENA_ADMIN_RESET`, `ARENA_SECURE_COOKIES`. Alles andere in der Tabelle musst du unter
`environment:` des Dienstes `waterrower-arena` selbst eintragen, z. B. `ARENA_COUNTDOWN: "15"`.

| Variable | Standard | Bedeutung |
|---|---|---|
| `ARENA_ADMIN_PASSWORD` | – | Passwort des ersten Admins. Wird nur gelesen, solange es das Konto noch nicht gibt (oder bei `ARENA_ADMIN_RESET=1`). Ohne Passwort startet der Server, bleibt aber gesperrt und sagt es im Log. |
| `ARENA_ADMIN_USER` | `admin` | Benutzername des ersten Admins |
| `ARENA_ADMIN_NAME` | `Admin` | Anzeigename |
| `ARENA_ADMIN_RESET` | `0` | `1` setzt beim Start das Passwort des Admin-Kontos auf `ARENA_ADMIN_PASSWORD` zurück ([Passwort vergessen](#passwort-vergessen)) |
| `ARENA_SECURE_COOKIES` | `1` | Nur der Wert `0` schaltet das Secure-Flag am Cookie ab |
| `ARENA_SESSION_DAYS` | `30` | Laufzeit der Browser-Anmeldung |
| `ARENA_UPLINK_TIMEOUT` | `50` | Sekunden Stille, bis ein Gerät als offline gilt |
| `ARENA_END_AT_FINISH` | `0` | `1` beendet bei Zieleinlauf die Einheiten aller Teilnehmer. Standard: jeder beendet seine eigene, denn wer im Ziel ist, rudert oft noch aus. |
| `ARENA_COUNTDOWN` | `10` | Sekunden Countdown vor dem Start |
| `ARENA_TICK_HZ` | `2` | Wie oft pro Sekunde Renndaten an die Browser gehen |
| `ARENA_FINISH_GRACE` | `600` | Sekunden, die Nachzügler nach dem Sieger noch bekommen, bevor das Rennen gewertet wird |
| `ARENA_TRUSTED_PROXIES` | Loopback und private Netze | Welche direkten Gegenstellen die Adresse des Aufrufers nennen dürfen (IPs/Netze, kommagetrennt). Nur von ihnen liest die Arena `CF-Connecting-IP`, sonst den **letzten** Eintrag aus `X-Forwarded-For`; alle anderen gelten mit ihrer Socket-Adresse. Der Standard passt für cloudflared und einen Proxy im selben Docker-Netz oder LAN. `*` vertraut jeder Gegenstelle. |
| `ARENA_LOGIN_IP_LIMIT` / `_MINUTES` | `10` / `15` | Anmeldeversuche pro Adresse, dann so viele Minuten gesperrt |
| `ARENA_LOGIN_NAME_LIMIT` / `_MINUTES` | `30` / `15` | Fehlversuche gegen ein Konto von überall. Absichtlich lockerer, weil man so jemanden aussperren könnte. |
| `ARENA_INVITE_IP_LIMIT` / `_MINUTES` | `10` / `60` | Falsche Einladungscodes pro Adresse |
| `ARENA_UPLINK_IP_LIMIT` / `_MINUTES` | `10` / `15` | Geräte-Verbindungen mit ungültigem Token pro Adresse |
| `DB_PATH` | `/data/arena.db` | Pfad der SQLite-Datenbank |
| `TZ` | `Europe/Berlin` (Compose) | Zeitzone für angezeigte Zeiten |

Die Limits sind nur **Startwerte**: Was ein Admin im Admin-Bereich unter *Sicherheit*
speichert, steht in der Datenbank und gilt ab dann. Ein Limit von `0` schaltet die
jeweilige Sperre ab.

## Daten und Backup

Alles liegt in einer SQLite-Datei: `./server/data/arena.db` (Athleten, Einheiten,
Messwerte, Rennen, Abzeichen, Einstellungen).

**Backup:** Als Admin unter *Konto → Sicherung → Datenbank herunterladen*
(`GET /api/backup`) laden. Das ist
absichtlich keine Dateikopie: Die Datenbank läuft im WAL-Modus, die neuesten Zeilen
stehen in `arena.db-wal`, und ein Kopieren nur von `arena.db` kann eine veraltete oder
beschädigte Datei liefern. Die Backup-Datei enthält Passwort-Hashes und Einladungscodes
und gehört an einen privaten Ort.

**Wiederherstellen:** Container stoppen (`docker compose stop waterrower-arena`), die
Datei als `server/data/arena.db` ablegen, dabei vorhandene `arena.db-wal` und
`arena.db-shm` entfernen, Container starten.

**Einzelne Einheit löschen:** in der Arena. Excel/CSV-Export pro Einheit oder für alle
steht jedem angemeldeten Athleten zur Verfügung.

## Update

```bash
cd waterrower-arena
git pull
docker compose up -d --build
```

Die Datenbank bleibt im Volume. Die Version zeigt die Oberfläche an (Endpunkt `/api/version`, nur angemeldet).

**Update von einem Image vor 2.1 (Container lief als root):** Der Container läuft jetzt als
Benutzer `1000`. Den Datenordner einmalig auf ihn umstellen, sonst kann die Arena ihre
Datenbank nicht schreiben:

```bash
docker compose down
sudo chown -R 1000:1000 ./server/data      # bzw. der Pfad deines Volumes
docker compose up -d
```

Optional baut der Workflow `.github/workflows/docker-publish.yml` das Image bei jedem
Push auf `main` für amd64 und arm64 und veröffentlicht es als
`ghcr.io/mojoone1/waterrower-arena/arena` (Tags `latest`, Version aus `VERSION` und
Commit). Neue Pakete in GHCR sind zunächst privat; zum Ziehen ohne Anmeldung muss
das Paket in den GitHub-Paketeinstellungen auf öffentlich gestellt werden. Die
Compose-Datei benutzt weiterhin `build: ./server`.

## Passwort vergessen

Admin: in der `.env` ein neues `ARENA_ADMIN_PASSWORD` setzen und `ARENA_ADMIN_RESET=1`,
dann `docker compose up -d`. Das Konto behält seine Einheiten, nur Passwort und alle
offenen Browser-Anmeldungen verschwinden. **Danach `ARENA_ADMIN_RESET` wieder auf `0`
setzen**, sonst wird bei jedem Neustart das Passwort aus der Datei neu gesetzt.

Andere Athleten: Der Admin setzt das Passwort unter *Konto → Athleten* zurück und
gibt den neuen Einladungslink weiter.

## Sperren

Die Arena sperrt eine Adresse oder ein Konto nach zu vielen Fehlversuchen (Werte
siehe oben). Admins sehen die Sperren im Konto-Bereich unter *Sicherheit* und können sie dort
einzeln oder mit *Alle Sperren aufheben* lösen. Wer sich als einziger Admin selbst
aussperrt, wartet die Sperrzeit ab oder startet den Container neu: Die Zähler liegen nur im
Speicher und sind danach weg.

Ein Rudergerät mit falschem Token wird mit Code 4403 getrennt (4401: kein gültiges
`hello`, 4429: gesperrt). Der ESP wartet danach 20 Minuten, bevor er es erneut
versucht, damit er sich nicht selbst aussperrt.

## Sicherheit

- Passwörter: scrypt mit Salt, mindestens 12 Zeichen und drei der vier Zeichenarten. Alte, schwächere Hashes werden
  beim nächsten Login erneuert.
- Browser-Anmeldung: Cookie `arena_session`, `HttpOnly`, `SameSite=Lax`, `Secure`
  (außer mit `ARENA_SECURE_COOKIES=0`).
- Geräte-Token: 256 Bit, in der Datenbank nur als Hash, nur einmal sichtbar.
- Eingaben der Geräte: Messwerte werden vor dem Speichern auf Typ und Wertebereich
  geprüft (keine Texte, NaN oder absurden Zahlen), Einheiten-IDs sind auf 64 druckbare
  Zeichen begrenzt, Nachsenden auf 20 000 Messwerte pro Einheit.
- Adresse des Aufrufers für Sperren und Sicherheitsprotokoll: Nur vertrauenswürdige
  Proxys dürfen sie nennen (`CF-Connecting-IP`, sonst der letzte `X-Forwarded-For`-Eintrag).
  Ein gefälschter Header umgeht so weder eine Sperre noch sperrt er jemand anderen aus.
- Widerruf wirkt sofort: Abmelden, Passwort zurücksetzen oder ändern, Geräte-Token
  widerrufen und Athlet löschen schließen die betroffenen offenen Verbindungen.
- Anfragen sind auf 1 MiB begrenzt, auch in Teilen (chunked) gesendete; eine
  WebSocket-Nachricht auf 4 MiB; höchstens 16 Geräte dürfen gleichzeitig beim Verbinden
  (vor dem `hello`) sein.
- Den Live-Feed öffnet nur die eigene Seite der Arena (`Origin`-Prüfung).
- Excel-Export: Text, der wie eine Formel aussieht (`=…`), wird als Text geschrieben.
- Der Container läuft als unprivilegierter Benutzer mit `no-new-privileges`. Die Arena
  hat keinen TLS-Terminator; HTTPS liefert der Tunnel oder dein Proxy.

## Fehlersuche

| Symptom | Ursache und Lösung |
|---|---|
| Die Anmeldung scheint zu klappen, bleibt aber nicht bestehen | Zugriff über `http://` bei `ARENA_SECURE_COOKIES=1`. Entweder HTTPS verwenden oder zum Testen `ARENA_SECURE_COOKIES=0` setzen. |
| `docker compose` bricht mit „required variable TUNNEL_TOKEN is missing“ ab | `TUNNEL_TOKEN` in `.env` eintragen oder den `cloudflared`-Block löschen ([Ohne Cloudflare Tunnel](#ohne-cloudflare-tunnel)). |
| `ARENA_ADMIN_PASSWORD` fehlt | Der Server startet, aber niemand kommt hinein; das Log sagt es. In `.env` eintragen, neu starten. |
| Gerät bleibt offline | Im ESP unter *Arena* Adresse und Token prüfen. Die Adresse sieht aus wie `https://arena.example.com`, ohne Pfad (der ESP hängt `/ws/uplink` selbst an). Bei Code 4403 ist der Token ungültig oder widerrufen, bei 4429 hat die Arena die Adresse gesperrt. Der ESP wartet danach 20 Minuten. |
| Gerät online, aber Einheiten fehlen | Der ESP sendet verpasste Einheiten beim nächsten Verbinden nach (*Backfill*). Das Log der Arena zeigt `Backfilled …` pro Einheit. |
| Zeiten um Stunden verschoben | `TZ` im Container und Zeitzone im ESP prüfen. Gespeichert werden Unix-Zeiten, `TZ` betrifft nur die Anzeige. |
| Rennen hängt nach dem Sieger | Nachzügler bekommen `ARENA_FINISH_GRACE` Sekunden (Standard 600). Der Admin kann das Rennen abbrechen oder abschließen. |
| Tunnel zeigt 502 | Hostname im Tunnel muss auf `http://waterrower-arena:8090` zeigen und beide Container im selben Compose-Projekt laufen. Mit `docker compose ps` prüfen. |
