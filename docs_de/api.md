# HTTP-API

🇩🇪 Deutsch · [🇬🇧 English](../docs_en/api.md)

Die Weboberfläche benutzt diese API; sie ist nicht als stabile öffentliche Schnittstelle
zugesagt. Alles läuft über JSON, die Anmeldung über das Cookie `arena_session`
(`HttpOnly`, `SameSite=Lax`).

**Rechte:** *offen* = ohne Anmeldung, *angemeldet* = jeder Athlet, *Admin* = nur Admins,
*eigen* = nur für den Athleten selbst oder einen Admin.

Fehler kommen als `{"detail": "…"}` mit dem passenden HTTP-Status (401 nicht angemeldet,
403 keine Berechtigung, 404 gibt es nicht, 409 Name vergeben, 429 gesperrt).

## Anmeldung und Konto

| Methode und Pfad | Rechte | Zweck |
|---|---|---|
| `GET /api/health` | offen | Lebenszeichen, liest die Datenbank (Container-Healthcheck) |
| `GET /api/version` | angemeldet | Version und Commit |
| `GET /api/me` | angemeldet (401 sonst) | eigenes Profil |
| `POST /api/login` | offen, mit Sperren | `{name, password}` |
| `POST /api/logout` | – | Sitzung beenden |
| `POST /api/invite` | offen, mit Sperren | `{code}`: für wen eine Einladung gilt (POST, damit Codes nicht in Zugriffsprotokollen landen) |
| `POST /api/join` | offen, mit Sperren | `{code, password}`: Einladung einlösen, Passwort setzen |
| `POST /api/password` | angemeldet | `{old_password, password}`: Passwort ändern |

## Athleten und Geräte-Token

| Methode und Pfad | Rechte | Zweck |
|---|---|---|
| `GET /api/athletes` | angemeldet | alle Athleten (ohne Hashes und Codes) |
| `POST /api/athletes` | Admin | `{name, display_name, is_admin}` → Athlet und Einladungscode |
| `PATCH /api/athletes/{id}` | eigen | Anzeigename, Farbe; Admin-Recht nur durch Admins, der letzte Admin bleibt Admin |
| `POST /api/athletes/{id}/invite` | Admin | neuer Einladungscode, **löscht das Passwort** (das ist das Zurücksetzen) |
| `DELETE /api/athletes/{id}` | Admin | Athlet löschen |
| `GET /api/athletes/{id}/tokens` | eigen | Token ohne Klartext (`id`, `label`, `created_at`, `last_seen_at`) |
| `POST /api/athletes/{id}/tokens` | eigen | `{label}` → neuer Token. Der Klartext erscheint **nur in dieser Antwort**. |
| `DELETE /api/athletes/{id}/tokens/{token_id}` | eigen | Token widerrufen |

## Einheiten, Live und Export

| Methode und Pfad | Rechte | Zweck |
|---|---|---|
| `GET /api/sessions` | angemeldet | Liste (Filter und Grenzen als Query-Parameter) |
| `GET /api/sessions/{id}` | angemeldet | Einheit mit allen Messwerten |
| `DELETE /api/sessions/{id}` | eigen | Einheit löschen |
| `GET /api/sessions/{id}/export.xlsx` | angemeldet | Excel: Zusammenfassung, Messwerte, zwei Diagramme |
| `GET /api/sessions/{id}/export.csv` | angemeldet | CSV |
| `GET /api/export.xlsx` | angemeldet | alle Einheiten in einer Tabelle plus Summen |
| `GET /api/live` | angemeldet | aktueller Stand aller Athleten |
| `POST /api/session/end` | angemeldet | meine Einheit am Gerät beenden (Befehl `end`) |
| `POST /api/session/reset` | angemeldet | meine Einheit schließen, Monitor auf null (Befehl `reset`) |
| `GET /api/records` | angemeldet | Bestleistungen je Athlet und Standarddistanz/-zeit |
| `GET /api/totals` | angemeldet | Summen |
| `GET /api/h2h` | angemeldet | wer wen in beendeten Rennen geschlagen hat |
| `GET /api/backup` | Admin | ganze Datenbank als konsistente SQLite-Datei |
| `POST /api/reindex` | Admin | Bestleistungen neu aus den Messwerten berechnen (z. B. nach einem Import) |

## Rennen

Es gibt höchstens ein aktives Rennen. Fehler der Rennmaschine kommen als 403 mit Text.
Beitreten dürfen nur Nicht-Admins. Starten und Beenden darf der Ersteller oder ein Admin,
eine fremde Bahn darf nur ihr Besitzer, der Ersteller oder ein Admin entfernen.

| Methode und Pfad | Rechte | Zweck |
|---|---|---|
| `GET /api/race` | angemeldet | aktives Rennen |
| `POST /api/race` | angemeldet | Rennen anlegen: `{name, mode, target, template_id}` mit Modus `distance`, `time` oder `free` |
| `POST /api/race/join`, `/leave`, `/ready` | angemeldet | beitreten, Bahn verlassen, bereit melden |
| `POST /api/race/ghost` | angemeldet | eine aufgezeichnete Einheit als Geist mitlaufen lassen |
| `POST /api/race/start` | Ersteller/Admin | Countdown und Start |
| `POST /api/race/finish`, `/abort` | Ersteller/Admin | werten oder abbrechen |
| `POST /api/race/clear` | angemeldet | beendetes Rennen aus der Live-Ansicht nehmen |
| `GET /api/races`, `GET /api/races/{id}` | angemeldet | Rennhistorie |
| `DELETE /api/races/{id}` | Admin | Rennen aus der Historie löschen |

## Abzeichen und Vorlagen

| Methode und Pfad | Rechte | Zweck |
|---|---|---|
| `GET /api/achievements` | angemeldet | Abzeichen (verborgene bleiben bis zum Erwerb eine Silhouette) |
| `GET /api/achievements/metrics` | Admin | Kennzahlen, aus denen sich ein Abzeichen bauen lässt |
| `POST /api/achievements` | Admin | Abzeichen anlegen |
| `DELETE /api/achievements/{id}` | Admin | Abzeichen samt allen Erwerben löschen |
| `GET /api/templates` | angemeldet | Rennvorlagen |
| `POST /api/templates`, `DELETE /api/templates/{id}` | Admin | Rennvorlagen verwalten |

## Sicherheit

| Methode und Pfad | Rechte | Zweck |
|---|---|---|
| `GET /api/security`, `POST /api/security` | Admin | Sperren lesen und ändern (Limit 0 = aus) |
| `POST /api/security/unblock` | Admin | Sperren aufheben |

## WebSockets

| Pfad | Wer | Beschreibung |
|---|---|---|
| `/ws/uplink` | Rudergeräte | [Protokoll](protokoll.md), Anmeldung per Geräte-Token |
| `/ws/live` | Browser | Live-Kacheln, Renntakt, neue Einheiten; Anmeldung per Cookie |
