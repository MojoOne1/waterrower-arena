"""The uplink protocol as docs_en/protocol.md describes it, message by message.

In-process through FastAPI's test client, like smoke.py. This is what a rowing
computer (the ESP firmware, or anything else) relies on: hello/welcome, live
samples, summary, backfill with its ack, sync, ping, what is refused and what
is dropped. The messages are written out by hand, shaped like the ones the
firmware builds in firmware/src/uplink.c.
"""
import os
import sys
import tempfile
import time

TMP = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(TMP, "arena.db")
os.environ["ARENA_ADMIN_PASSWORD"] = "Supersecret1!"
os.environ["ARENA_SECURE_COOKIES"] = "0"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server", "app"))

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402
import main  # noqa: E402

ok = 0
fail = 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {extra}")


def closes_with(ws, code):
    """True when the server closes the socket with this code."""
    try:
        ws.receive_json()
    except WebSocketDisconnect as e:
        return e.code == code
    return False


def barrier(ws):
    """Everything sent before this has been handled once `known` comes back."""
    ws.send_json({"type": "sync"})
    msg = ws.receive_json()
    while msg.get("type") != "known":      # a ping may arrive first
        msg = ws.receive_json()
    return msg["known"]


def sample(sid, started, t, **over):
    m = {"type": "sample", "session": sid, "started_at": started, "t": t,
         "distance_m": t * 4, "speed_ms": 4.2, "stroke_rate": 24, "strokes": t * 2, "watts": 140}
    m.update(over)
    return m


NOW = int(time.time())

with TestClient(main.app) as c:
    c.post("/api/login", json={"name": "admin", "password": "Supersecret1!"})
    r = c.post("/api/athletes", json={"name": "anna", "display_name": "Anna"})
    athlete_id = r.json()["athlete"]["id"]
    anna = TestClient(main.app)
    anna.post("/api/join", json={"code": r.json()["invite_code"], "password": "Annaspassword1!"})
    token = anna.post(f"/api/athletes/{athlete_id}/tokens", json={"label": "esp"}).json()["token"]
    db = main.db

    print("\n-- hello")
    with c.websocket_connect("/ws/uplink") as ws:
        ws.send_json({"type": "sample", "session": "x"})
        check("anything but hello first is refused with 4401", closes_with(ws, 4401))
    with c.websocket_connect("/ws/uplink") as ws:
        ws.send_json({"type": "hello", "token": "wrong", "agent": "t"})
        check("an unknown token is refused with 4403", closes_with(ws, 4403))
    with c.websocket_connect("/ws/uplink") as ws:
        ws.send_json({"type": "hello", "token": token, "agent": "waterrower-esp/3.0.0-esp"})
        w = ws.receive_json()
        check("welcome carries the athlete", w["type"] == "welcome"
              and w["athlete"]["name"] == "anna" and w["athlete"]["display_name"] == "Anna", w)
        check("welcome carries the server time", abs(w["server_time"] - time.time()) < 5, w)
        check("a new athlete has nothing known yet", w["known"] == [], w)
        live = anna.get("/api/live").json()
        check("the athlete shows as online",
              any(x["athlete_id"] == athlete_id and x["online"] for x in live["athletes"]), live)

    print("\n-- live samples and summary")
    start = NOW - 600
    with c.websocket_connect("/ws/uplink") as ws:
        ws.send_json({"type": "hello", "token": token, "agent": "t"})
        ws.receive_json()
        for t in range(0, 5):
            ws.send_json(sample("live-1", start, t))
        known = barrier(ws)
        check("a streamed session becomes known", "live-1" in known, known)
        sid = db.session_id_for(athlete_id, "live-1", start)
        check("its samples are stored", len(db.samples(sid)) == 5, len(db.samples(sid)))
        ws.send_json({"type": "summary", "session": "live-1", "started_at": start,
                      "distance_m": 20, "duration_s": 4, "strokes": 8,
                      "avg_speed_ms": 4.2, "avg_spm": 24.0})
        barrier(ws)
        s = db.session(sid)
        check("the summary closes it", s["ended_at"] is not None and s["distance_m"] == 20, s)

    print("\n-- values are checked, not trusted")
    with c.websocket_connect("/ws/uplink") as ws:
        ws.send_json({"type": "hello", "token": token, "agent": "t"})
        ws.receive_json()
        ws.send_json(sample("dirty-1", start, 0, distance_m="lots", watts=True, speed_ms=-5,
                            stroke_rate=1e12, strokes=7))
        ws.send_json({"type": "sample", "session": "", "t": 1, "distance_m": 1})
        ws.send_json({"type": "sample", "session": "x" * 65, "t": 1, "distance_m": 1})
        ws.send_json({"type": "sample", "session": "bell\x07", "t": 1, "distance_m": 1})
        ws.send_json({"type": "nonsense", "whatever": 1})
        ws.send_json([1, 2, 3])
        known = barrier(ws)
        check("a well-formed id is kept", "dirty-1" in known, known)
        check("empty, too long and unprintable ids are dropped",
              not any(k in known for k in ("", "x" * 65, "bell\x07")), known)
        row = db.samples(db.session_id_for(athlete_id, "dirty-1", start))[0]
        check("text and booleans are not stored as numbers",
              row["distance_m"] is None and row["watts"] is None, row)
        check("out of range numbers are not stored",
              row["speed_ms"] is None and row["stroke_rate"] is None, row)
        check("good fields next to bad ones survive", row["strokes"] == 7, row)
        check("the socket survives all of it", barrier(ws) is not None)

    print("\n-- backfill and ack")
    rows = [{"t": t, "distance_m": t * 4, "speed_ms": 4.0, "stroke_rate": 22,
             "strokes": t * 2, "watts": 130} for t in range(0, 60)]
    msg = {"type": "backfill", "session": "old-1", "started_at": NOW - 86400,
           "ended_at": NOW - 86400 + 59,
           "summary": {"distance_m": 236, "duration_s": 59, "strokes": 118,
                       "avg_speed_ms": 4.0, "avg_spm": 22.0},
           "samples": rows}
    with c.websocket_connect("/ws/uplink") as ws:
        ws.send_json({"type": "hello", "token": token, "agent": "t"})
        w = ws.receive_json()
        check("known lists what the arena holds", "live-1" in w["known"], w["known"])
        ws.send_json(msg)
        a = ws.receive_json()
        while a.get("type") == "ping":
            a = ws.receive_json()
        check("a backfill is acknowledged", a == {"type": "ack", "session": "old-1", "stored": True}, a)
        sid = db.session_id_for(athlete_id, "old-1", 0)
        s = db.session(sid)
        check("all rows landed", len(db.samples(sid)) == 60)
        check("and the session is closed with its summary",
              s["ended_at"] is not None and s["distance_m"] == 236 and s["duration_s"] == 59, s)

        ws.send_json(msg)
        a = ws.receive_json()
        check("repeating a backfill is acknowledged again", a["stored"] is True, a)
        check("and adds nothing", len(db.samples(sid)) == 60)
        check("nor a second session",
              sum(1 for k in barrier(ws) if k == "old-1") == 1)

        ws.send_json({**msg, "session": "huge", "samples": [{"t": i} for i in range(20001)]})
        a = ws.receive_json()
        check("over 20 000 rows is refused", a == {"type": "ack", "session": "huge", "stored": False}, a)
        ws.send_json({**msg, "session": "", })
        a = ws.receive_json()
        check("a backfill without a session id is refused", a["stored"] is False, a)
        ws.send_json({**msg, "session": "odd", "samples": "not a list"})
        a = ws.receive_json()
        check("samples that are not a list are refused", a["stored"] is False, a)

    print("\n-- sync and ping")
    with c.websocket_connect("/ws/uplink") as ws:
        ws.send_json({"type": "hello", "token": token, "agent": "t"})
        ws.receive_json()
        ws.send_json({"type": "ping"})
        msg = ws.receive_json()
        while msg.get("type") == "ping":
            msg = ws.receive_json()
        check("ping is answered with pong", msg == {"type": "pong"}, msg)
        known = barrier(ws)
        check("sync lists every session the arena has",
              {"live-1", "old-1", "dirty-1"} <= set(known), known)

    print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
