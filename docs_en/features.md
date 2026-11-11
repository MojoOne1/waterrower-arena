# Races, badges and records

[🇩🇪 Deutsch](../docs_de/funktionen.md) · 🇬🇧 English

## How the data gets there

Each rowing device opens **one outbound WebSocket** to the arena and authenticates with a device token. That direction matters: nobody has to forward a port, expose a broker or own a certificate, and it works from behind any consumer router. The arena speaks no MQTT at all.

Other ways were considered and rejected: pointing the ESP straight at a central broker would cost everyone their local broker, and bridging each household's Mosquitto would mean every friend has to edit a broker config.

Because the device is the one sending, it also knows what it has: on connect the arena replies with the workouts it already holds, and the device sends the rest. A weekend with the internet down costs a delay, not the data. Details: [protocol](protocol.md).

## Racing

Three modes:

| Mode | Ends when | Winner |
|---|---|---|
| **Distance** | everybody has covered the target, or ten minutes after the first finisher | fastest time |
| **Time** | the clock runs out | most metres |
| **Free** | the host ends it | nobody, just row together |

A race is created in a lobby; the others join and say they are ready. When the host starts it, the arena sends every participant's device a reset, so each monitor and each workout starts from zero, and then counts down ten seconds. From the gun the view shows one lane per rower with distance, split, stroke rate, watts, the gap in metres *and* in seconds, and in a distance race the projected time still to go.

While your own workout is running, a strip of the S4's own readout (metres, time, split, rate, watts) sits docked at the bottom of whichever tab you are on, with the workout buttons on it.

It goes the other way too: while a race is on, the ESP at the machine shows the countdown, then your place and the gap. The race state rides the uplink that is already open, so it costs no port, no second login and nothing new at the house.

Crossing the line does not end your workout: whether you are done is your call, not the race's, and after a hard 2 km most people row it out for a while. Two buttons close it when you say so, the same pair on both screens:

- **End session** closes the workout and leaves the display alone, so the numbers can still be read while you row out.
- **End & zero** closes it and sets the monitor back to zero, for when the next piece starts straight away.

Either only ever ends your own workout. Left alone, the S4 closes the workout itself once it has been idle long enough; ending it just means the summary, averages and any personal best land now rather than then. `ARENA_END_AT_FINISH=1` hands that decision to the race instead and closes everybody's workout at the finish.

A lane does not have to be a live person. **Ghost** adds any recorded workout as an opponent, replayed against the race clock: row against a friend who is not at home, or against your own best.

**Timing:** the race clock is the server's, and a lane is placed on it by the arrival time of its samples. Samples come once a second, so a finish time is interpolated between the two that straddle the line. Transport latency (tens of milliseconds, much the same for everyone) is the accuracy limit. This is a race between friends, not a timing gate.

Everything a race produces is kept: the placings, the linked workouts and a head-to-head tally of who has beaten whom.

## Badges

A tab of its own. Twelve to start with, four of them hidden; a hidden one is a silhouette that says nothing about what it wants until you walk into it. That is per viewer, not per arena: the first person to find one does not spoil it for the others. The names in the app are German:

| Name | Visible | Condition |
|---|---|---|
| Erste Fahrt | yes | first recorded workout |
| Zehntausend / Hunderttausend | yes | 10 km / 100 km in total |
| Halbe Stunde | yes | 30 minutes without stopping |
| Unter 2:00 | yes | 500 m under two minutes |
| 2 km unter 8:00 | yes | best 2 km under eight minutes |
| Erster Sieg / Dreimal in Folge | yes | one race won / three in a row |
| Frühaufsteher | hidden | a workout started before eight in the morning |
| Nachtschicht | hidden | a workout started after nine in the evening |
| Wochenstreak | hidden | seven days in a row |
| Fotofinish | hidden | a race won by under a second |

Every rule has the same shape, **a metric, a comparison, a threshold**, and that is the whole vocabulary, which is what lets an admin add badges in the arena without anybody writing code. The cost is real: a condition nobody anticipated cannot be expressed.

Badges are checked on the server when a workout closes and when a race ends, never in the browser: a badge you can award yourself is not worth having. History counts: a new badge is handed to whoever already qualifies, and an arena that backfilled a year of workouts gets its badges on the next start.

## Records and comparison

Personal bests are scanned out of the samples with a rolling window, so the fastest 2 km *inside* a 6 km row counts too. Standard efforts are 500 m, 1 km, 2 km, 5 km and 10 km for time, and 5, 10, 20, 30 and 60 minutes for distance. The workout list spans every athlete, and up to four workouts, from different people, can be overlaid on one chart.

## Status and limits

- **Real-world multiplayer is untested.** Sign-in, uplink, backfill, races, records and badges work end to end and are covered by automated checks ([tests](tests.md)). What has not happened yet is what it was built for: two people, two WaterRowers, two houses, one race at the same moment. Expect the rough edges of a first outing.
- Only **one race at a time**. A race that is still open when the server restarts is marked aborted at startup; it does not survive a restart.
- Not built yet: the arena's own views inside the ESP (standings and your own badges, read-only, over the uplink that is already open).

## Versioning

One version number, kept in the `VERSION` file in the repository root. The workflow builds the image on every push to `main` and stamps it with the version and the short commit hash (`APP_VERSION`, `GIT_COMMIT`); the tags are `latest`, `<version>` and `sha-<commit>`. Both show in the web UI's footer and at `/api/version`.
