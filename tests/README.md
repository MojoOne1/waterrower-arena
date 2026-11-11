# Tests

Zwei Suiten, kein Framework: Jede druckt pro Prüfung eine Zeile und endet mit Exit-Code
ungleich 0, wenn etwas fehlschlug. `run_all.py` führt alle als eigene Prozesse aus und
fasst zusammen.

```bash
python -m pip install -r server/requirements.txt httpx
python tests/run_all.py
```

| Suite | Was sie abdeckt | Braucht |
|---|---|---|
| `smoke.py` | Die Arena im Prozess über den Testclient von FastAPI: Anmeldung und Sperren, Einladungen, Geräte-Token, eine normale Einheit über den Uplink, Bestleistungen, Rennen mit Countdown, Ziel und Geistern, die Befehle `reset`/`end` ans Gerät, Rechte, Healthcheck, Excel-Export, Backup, Auslieferung der Oberfläche | nichts außerhalb des Checkouts |
| `uplink_protocol.py` | Das [Uplink-Protokoll](../docs_de/protokoll.md) Nachricht für Nachricht: `hello`/`welcome`/`known`, Schließcodes 4401 und 4403, Live-Messwerte und `summary`, Prüfung und Verwerfen ungültiger Werte, `backfill` mit `ack` (auch wiederholt, zu groß, ohne ID), `sync`, `ping`/`pong` | nichts außerhalb des Checkouts |

Die Tests legen jeweils eine eigene temporäre Datenbank an und berühren `server/data` nicht. Sie
greifen nicht aufs Netz zu.

Bewusst **nicht** abgedeckt:

- **Ein echtes Rudergerät.** Das Protokoll wird mit selbst gebauten Nachrichten geprüft,
  die der Firmware nachempfunden sind (`firmware/src/uplink.c` im Repository
  [waterrower-esp](https://github.com/MojoOne1/waterrower-esp)). Dass der ESP wirklich
  so spricht, zeigt erst ein Test mit Hardware.
- **Das Docker-Image und den Tunnel.** `docker compose config` wird in der CI nicht
  ausgeführt, das Image-Bauen nur im Workflow `docker-publish.yml`.
- **Ein Rennen mit zwei echten Menschen.**

Früher gab es im Ursprungs-Repository zusätzlich `integration.py`, das den alten
Tracker-Client gegen einen echten Arena-Prozess laufen ließ. Dieser Client gehört zur
alten ESPHome-Variante und ist hier nicht mehr dabei; `uplink_protocol.py` ersetzt ihn
auf Protokollebene. Der CSV-Export und das Diagramm im Excel-Export sind nicht
eigens getestet.
