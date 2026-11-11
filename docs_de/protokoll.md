# Uplink-Protokoll (Rudergerät ↔ Arena)

🇩🇪 Deutsch · [🇬🇧 English](../docs_en/protocol.md)

Jedes Rudergerät hält **eine WebSocket-Verbindung** zur Arena:

```
wss://<arena>/ws/uplink        (bzw. ws:// bei http-Adresse)
```

Alle Nachrichten sind JSON-Textframes mit einem Feld `type`. Die Referenzimplementierung
der Geräteseite ist `firmware/src/uplink.c` im Repository
[MojoOne1/waterrower-esp](https://github.com/MojoOne1/waterrower-esp),
die der Serverseite `server/app/ingest.py`. Das Protokoll hat keine Versionsnummer;
unbekannte Nachrichten und Felder werden ignoriert.

## Ablauf

```
Gerät                                   Arena
  │── hello {token, agent} ───────────────►│   Frist: 15 s, sonst wird getrennt
  │◄───────── welcome {athlete, server_time, known}
  │── sample … (1 Hz während einer Einheit) ►│
  │── summary (Einheit beendet) ───────────►│
  │── backfill {…, samples:[…]} ──────────►│   für Einheiten, die die Arena nicht hat
  │◄───────── ack {session, stored}
  │◄───────── cmd {cmd: "reset"|"end"|"race"}
  │◄───────── ping   ── pong ─────────────►│   alle 20 s
```

## Gerät → Arena

### `hello`

```json
{"type": "hello", "token": "<geräte-token>", "agent": "waterrower-esp/3.0.0-esp"}
```

Muss die erste Nachricht sein. `agent` ist freier Text (auf 80 Zeichen gekürzt) und
erscheint in der Arena beim Athleten.

### `sample`

Ein Messwert pro Sekunde während einer laufenden Einheit.

```json
{"type": "sample", "session": "20261111T184500", "started_at": 1762886700, "t": 42,
 "distance_m": 180, "speed_ms": 4.31, "stroke_rate": 24, "strokes": 84, "watts": 140}
```

| Feld | Bedeutung |
|---|---|
| `session` | ID der Einheit **aus Sicht des Geräts**, 1–64 druckbare Zeichen. Ein Wert pro Einheit und Gerät; die Arena ordnet ihn dem Athleten zu. |
| `started_at` | Beginn der Einheit, Unix-Sekunden (bis zum Jahr 2100). Fehlt er oder ist ungültig, setzt die Arena `jetzt − t`. |
| `t` | Sekunden seit Beginn der Einheit (ganzzahlig, höchstens 7 Tage) |
| `distance_m`, `speed_ms`, `stroke_rate`, `strokes`, `watts` | Zahlen. Jede andere Art (Text, Boolean, NaN) oder ein Wert außerhalb von 0 … 10 000 000 wird verworfen und nicht gespeichert. `distance_m` und `strokes` werden ganzzahlig. |

Die Arena vertraut der Uhr des Geräts nur für diese Sekunden seit Beginn. **Die Rennuhr
gehört dem Server**: Fortschritt im Rennen wird über die Ankunftszeit der Messwerte
eingeordnet, die Zielzeit zwischen den zwei Messwerten interpoliert, die die Linie
umschließen.

### `summary`

Beendet die Einheit; der ESP sendet es bei jedem Einheitenende. Hat die Arena nicht alle
Messwerte live bekommen (Verbindung war zwischendurch weg), liefert der ESP die Einheit
später zusätzlich per `backfill` komplett nach.

```json
{"type": "summary", "session": "20261111T184500", "started_at": 1762886700,
 "distance_m": 2000, "duration_s": 480, "strokes": 190, "avg_speed_ms": 4.17, "avg_spm": 23.7}
```

`duration_s` ist auf 7 Tage begrenzt, `avg_speed_ms` und `avg_spm` auf 0 … 1000. Nach dem
Schließen berechnet die Arena Bestleistungen und prüft Abzeichen.

### `backfill`

Eine komplette Einheit nachträglich, z. B. wenn das Gerät offline war.

```json
{"type": "backfill", "session": "20261110T071500", "started_at": 1762758900, "ended_at": 1762759380,
 "summary": {"distance_m": 2000, "duration_s": 480, "strokes": 190, "avg_speed_ms": 4.17, "avg_spm": 23.7},
 "samples": [{"t": 0, "distance_m": 0, "speed_ms": 0, "stroke_rate": 0, "strokes": 0, "watts": 0}, …]}
```

Höchstens **20 000** Messwerte pro Nachricht; mehr (oder eine fehlende/ungültige `session`)
wird mit `ack` und `stored: false` beantwortet. Eine `session`, die die Arena schon kennt,
wird **ergänzt, nicht ersetzt**: Messwerte für Sekunden, die schon gespeichert sind,
werden ignoriert, fehlende kommen dazu, die Zusammenfassung wird neu gesetzt. Ein
Backfill lässt sich also gefahrlos wiederholen.

### `sync`

Fragt, welche Einheiten die Arena schon hat. Antwort: `known`.

### `pong`

Antwort auf `ping`. Jede eingehende Nachricht setzt außerdem den Zeitpunkt „zuletzt gesehen“.

## Arena → Gerät

### `welcome`

```json
{"type": "welcome", "athlete": {"id": 3, "name": "jan", "display_name": "Jan", "color": "#2a78d6", …},
 "server_time": 1762886712.4, "known": ["20261110T071500", …]}
```

`athlete` enthält `id`, `name`, `display_name`, `color` und `is_admin`. `known` listet die
Geräte-IDs aller Einheiten, die die Arena für diesen Athleten gespeichert hat (die
neuesten 500). Eine ID steht dort auch dann, wenn die Einheit unvollständig ist, `known`
sagt also nur „kenne ich“, nicht „habe ich komplett“. Der ESP wertet die Liste nicht aus;
er führt selbst Buch, welche Einheiten die Arena per `ack` bestätigt hat, und schickt
nur die übrigen per `backfill`.

### `ack`

```json
{"type": "ack", "session": "20261110T071500", "stored": true}
```

Bestätigt ein `backfill`. Erst mit `stored: true` darf das Gerät die Einheit als
übertragen markieren.

### `known`

Antwort auf `sync`: `{"type": "known", "known": ["…"]}`.

### `cmd`

| `cmd` | Wirkung am Gerät |
|---|---|
| `reset` | Einheit schließen und den Monitor auf null setzen, **vor** dem Start eines Rennens |
| `end` | Einheit schließen, Anzeige lassen, **nach** dem Zieleinlauf |
| `race` | Renndaten für dieses Gerät (siehe unten); `race: null` heißt, es läuft kein Rennen |

Die `race`-Nachricht enthält nur den Ausschnitt dieses Rudergeräts, nicht das ganze Feld:

```json
{"type": "cmd", "cmd": "race", "race": {
  "state": "running", "name": "2 km Sonntag", "mode": "distance", "target": 2000,
  "elapsed": 61.4, "countdown_in": null, "place": 1, "progress": 255.0,
  "gap_m": 0.0, "finished": false, "time_s": null, "lanes": 3}}
```

`state` ist `countdown`, `running` oder `finished`; `mode` ist `distance`, `time` oder `free`.
Gesendet wird bei jeder Änderung, nie doppelt dasselbe.

### `ping`

Alle 20 Sekunden, damit der Tunnel die Verbindung nicht als leer verwirft. Das Gerät
antwortet mit `pong`.

## Schließcodes

| Code | Grund | Verhalten des ESP |
|---|---|---|
| 4401 | erste Nachricht war kein gültiges `hello` | wartet 20 Minuten |
| 4403 | Token unbekannt oder widerrufen | wartet 20 Minuten |
| 4429 | zu viele Fehlversuche dieser Adresse, gesperrt | wartet 20 Minuten |
| sonst | Verbindung weg | Neuaufbau mit Backoff 3 → 60 Sekunden |

Die Sperre für Fehlversuche (Standard: 10 in 15 Minuten) lässt sich im Admin-Bereich
ändern, siehe [Betrieb](betrieb.md#sperren).

## `/ws/live` (Browser)

Nicht für Geräte. Die Weboberfläche abonniert damit Live-Kacheln, Renntakt und neue
Einheiten; die Anmeldung erfolgt über das Cookie `arena_session`, ohne gültiges Cookie
schließt die Arena mit 4401. Das Format ist intern und kann sich ändern.

## Einen eigenen Client schreiben

1. Token erzeugen (*Konto → Tracker-Verbindung*).
2. Verbinden, `hello` senden, auf `welcome` warten.
3. Pro Sekunde `sample`; zum Ende `summary`.
4. Nach dem Verbinden Einheiten, die nicht in `known` stehen, per `backfill` nachliefern
   und `ack` abwarten.
5. `ping` mit `pong` beantworten, bei 4401/4403/4429 nicht sofort neu verbinden.
