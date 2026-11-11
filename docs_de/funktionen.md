# Rennen, Abzeichen und Bestleistungen

🇩🇪 Deutsch · [🇬🇧 English](../docs_en/features.md)

## Wie die Daten ankommen

Jedes Rudergerät öffnet **eine ausgehende WebSocket-Verbindung** zur Arena und meldet sich mit einem Geräte-Token an. Die Richtung ist wichtig: Niemand muss einen Port freigeben, einen Broker öffentlich machen oder ein Zertifikat besitzen, und es geht hinter jedem Heimrouter. Die Arena spricht kein MQTT.

Andere Wege wurden erwogen und verworfen: den ESP direkt auf einen zentralen Broker zeigen zu lassen, würde jedem den lokalen Broker kosten, und das Mosquitto jedes Haushalts zu verbinden hieße, dass jeder Freund eine Broker-Konfiguration bearbeiten muss.

Weil das Gerät sendet, weiß es auch, was es hat: Beim Verbinden antwortet die Arena mit den Einheiten, die sie schon kennt, und das Gerät schickt den Rest. Ein Wochenende ohne Internet kostet eine Verzögerung, keine Daten. Einzelheiten: [Protokoll](protokoll.md).

## Rennen

Drei Modi:

| Modus | Endet, wenn | Sieger |
|---|---|---|
| **Distanz** | alle das Ziel erreicht haben, oder zehn Minuten nach dem ersten im Ziel | schnellste Zeit |
| **Zeit** | die Uhr abläuft | meiste Meter |
| **Frei** | der Gastgeber es beendet | niemand, einfach zusammen rudern |

Ein Rennen wird in einer Lobby angelegt; die anderen treten bei und melden sich bereit. Startet der Gastgeber, schickt die Arena jedem Gerät ein Zurücksetzen, sodass jeder Monitor und jede Einheit bei null beginnt, und zählt zehn Sekunden herunter. Ab dem Startschuss zeigt die Ansicht eine Bahn je Ruderer mit Distanz, Split, Schlagfrequenz, Watt, dem Abstand in Metern *und* Sekunden und, im Distanzrennen, der voraussichtlichen Restzeit.

Solange die eigene Einheit läuft, sitzt unten in jedem Tab ein Streifen mit der Anzeige der S4 (Meter, Zeit, Split, Frequenz, Watt) samt den Knöpfen für die Einheit.

Es geht auch andersherum: Während eines Rennens zeigt der ESP an der Maschine den Countdown, dann deinen Platz und den Abstand. Der Rennzustand läuft über die ohnehin offene Verbindung, kostet also keinen Port, keine zweite Anmeldung und nichts Neues im Haus.

Das Überqueren der Linie beendet die Einheit nicht: Ob du fertig bist, entscheidest du, nicht das Rennen, und nach einem harten 2-km-Lauf rudern die meisten noch aus. Zwei Knöpfe schließen die Einheit auf Wunsch, auf beiden Bildschirmen dasselbe Paar:

- **Einheit beenden** schließt die Einheit und lässt die Anzeige stehen, damit die Zahlen beim Ausrudern lesbar bleiben.
- **Beenden & nullen** schließt sie und setzt den Monitor auf null, wenn das nächste Stück gleich losgeht.

Beides beendet nur die eigene Einheit. Sich selbst überlassen schließt die S4 die Einheit, sobald sie lange genug ruht; Beenden heißt nur, dass Zusammenfassung, Durchschnitte und eine Bestleistung jetzt statt später ankommen. `ARENA_END_AT_FINISH=1` überlässt die Entscheidung dem Rennen und beendet beim Zieleinlauf die Einheiten aller.

Eine Bahn muss kein lebender Mensch sein. Ein **Geist** nimmt jede aufgezeichnete Einheit als Gegner mit, abgespielt gegen die Rennuhr: gegen einen Freund, der nicht da ist, oder gegen die eigene Bestzeit.

**Zeitnahme:** Die Rennuhr gehört dem Server, und eine Bahn wird über die Ankunftszeit ihrer Messwerte darauf eingeordnet. Messwerte kommen einmal pro Sekunde, die Zielzeit wird also zwischen den beiden Werten interpoliert, die die Linie umschließen. Die Übertragungsverzögerung (Zehntelsekunden-Bruchteile, für alle ähnlich) ist die Genauigkeitsgrenze. Das ist ein Rennen unter Freunden, keine Zeitmessanlage.

Alles, was ein Rennen erzeugt, bleibt erhalten: Platzierungen, verknüpfte Einheiten und eine Kopf-an-Kopf-Bilanz, wer wen geschlagen hat.

## Abzeichen

Ein eigener Tab. Zu Beginn zwölf, vier davon verborgen; ein verborgenes ist eine Silhouette, die nichts darüber verrät, was es will, bis man hineinläuft. Das gilt je Betrachter, nicht je Arena: Wer eines findet, verdirbt es den anderen nicht.

| Name | Sichtbar | Bedingung |
|---|---|---|
| Erste Fahrt | ja | erste aufgezeichnete Einheit |
| Zehntausend / Hunderttausend | ja | 10 km / 100 km insgesamt |
| Halbe Stunde | ja | 30 Minuten am Stück |
| Unter 2:00 | ja | 500 m unter zwei Minuten |
| 2 km unter 8:00 | ja | beste 2 km unter acht Minuten |
| Erster Sieg / Dreimal in Folge | ja | ein Rennen gewonnen / drei in Folge |
| Frühaufsteher | verborgen | Einheit vor acht Uhr morgens begonnen |
| Nachtschicht | verborgen | Einheit nach neun Uhr abends begonnen |
| Wochenstreak | verborgen | sieben Tage in Folge |
| Fotofinish | verborgen | ein Rennen mit weniger als einer Sekunde Vorsprung gewonnen |

Jede Regel hat dieselbe Form, **eine Kennzahl, ein Vergleich, ein Schwellwert**, und das ist das ganze Vokabular. Dadurch kann ein Admin Abzeichen in der Arena ergänzen, ohne dass jemand Code schreibt. Der Preis ist real: Eine Bedingung, an die keiner gedacht hat, lässt sich nicht ausdrücken.

Geprüft wird auf dem Server, wenn eine Einheit endet und wenn ein Rennen endet, nie im Browser: Ein Abzeichen, das man sich selbst verleihen kann, ist nichts wert. Die Vergangenheit zählt: Ein neues Abzeichen bekommt, wer es schon verdient hat, und eine Arena mit nachgesendetem Jahr an Einheiten bekommt ihre Abzeichen beim nächsten Start.

## Bestleistungen und Vergleich

Bestleistungen werden mit einem gleitenden Fenster aus den Messwerten gelesen, die schnellsten 2 km *innerhalb* einer 6-km-Fahrt zählen also auch. Standardleistungen sind 500 m, 1, 2, 5 und 10 km nach Zeit und 5, 10, 20, 30 und 60 Minuten nach Distanz. Die Einheitenliste umfasst alle Athleten, und bis zu vier Einheiten, auch verschiedener Personen, lassen sich in einem Diagramm übereinanderlegen.

## Stand und Grenzen

- **Mehrspieler im echten Leben ist ungetestet.** Anmeldung, Uplink, Nachsenden, Rennen, Bestleistungen und Abzeichen funktionieren durchgehend und sind automatisch geprüft ([Tests](tests.md)). Noch nie passiert ist, wofür es gebaut wurde: zwei Menschen, zwei WaterRower, zwei Häuser, ein Rennen zur selben Zeit. Mit den Ecken eines ersten Ausflugs ist zu rechnen.
- Nur **ein Rennen gleichzeitig**. Ein Rennen, das beim Neustart des Servers noch offen ist, wird beim Start als abgebrochen markiert; es überlebt keinen Neustart.
- Noch nicht gebaut: die Arena-Ansichten im ESP selbst (Tabelle und eigene Abzeichen, nur lesend, über die ohnehin offene Verbindung).

## Versionierung

Eine Versionsnummer, in der Datei `VERSION` im Wurzelverzeichnis. Der Workflow baut bei jedem Push auf `main` das Image und stempelt es mit Version und kurzem Commit-Hash (`APP_VERSION`, `GIT_COMMIT`); die Tags sind `latest`, `<version>` und `sha-<commit>`. Beides erscheint in der Fußzeile der Oberfläche und unter `/api/version`.
