"""The fixes from the security audit, each pinned by a test."""
import io
import os
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(TMP, "arena.db")
os.environ["ARENA_ADMIN_PASSWORD"] = "Supersecret1!"
os.environ["ARENA_SECURE_COOKIES"] = "0"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "server", "app"))

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
import auth  # noqa: E402
import main  # noqa: E402
import xlsx_export  # noqa: E402

ok = fail = 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {extra}")


def closed(ws_ctx, first=None):
    """True when the server closes the socket instead of answering."""
    try:
        with ws_ctx as ws:
            if first is not None:
                ws.send_json(first)
            ws.receive_json()
        return False
    except Exception:
        return True


print("\n-- caller address")
H = lambda **kw: {k.replace("_", "-"): v for k, v in kw.items()}  # noqa: E731
check("an untrusted peer is taken at its socket address",
      auth.peer_address("203.0.113.9", H(x_forwarded_for="10.9.9.9", cf_connecting_ip="1.1.1.1"))
      == "203.0.113.9")
check("behind a trusted proxy CF-Connecting-IP wins",
      auth.peer_address("172.18.0.3", H(x_forwarded_for="6.6.6.6, 198.51.100.7",
                                         cf_connecting_ip="198.51.100.7")) == "198.51.100.7")
check("without it the last X-Forwarded-For entry counts, not the first",
      auth.peer_address("172.18.0.3", H(x_forwarded_for="6.6.6.6, 198.51.100.7")) == "198.51.100.7")
check("a trusted peer without headers is itself",
      auth.peer_address("127.0.0.1", H()) == "127.0.0.1")

print("\n-- excel")
session = {"display_name": '=HYPERLINK("https://evil.example","x")', "remote_id": "=1+1",
           "started_at": 1762886700, "ended_at": 1762887180, "distance_m": 2000,
           "duration_s": 480, "strokes": 190, "avg_speed_ms": 4.1, "avg_spm": 24}
for label, data in (("session export", xlsx_export.build_session(session, [
        {"t": 0, "distance_m": 0, "speed_ms": 0, "stroke_rate": 0, "strokes": 0, "watts": 0},
        {"t": 1, "distance_m": 4, "speed_ms": 4, "stroke_rate": 24, "strokes": 1, "watts": 150}])),
        ("overview export", xlsx_export.build_overview([session], []))):
    wb = load_workbook(io.BytesIO(data))
    cells = [c for ws in wb.worksheets for row in ws.iter_rows() for c in row
             if isinstance(c.value, str) and c.value.startswith("=")]
    check(f"{label}: names that look like formulas stay text",
          cells and all(c.data_type == "s" for c in cells), [(c.coordinate, c.data_type) for c in cells])

with TestClient(main.app) as c:
    c.post("/api/login", json={"name": "admin", "password": "Supersecret1!"})
    jan = c.post("/api/athletes", json={"name": "jan", "display_name": "Jan"}).json()
    cj = TestClient(main.app)
    cj.post("/api/join", json={"code": jan["invite_code"], "password": "Rudern-2026!"})
    jan_id = jan["athlete"]["id"]

    print("\n-- request bodies")
    big = b'{"name":"a","password":"b","x":"' + b"A" * (2 << 20) + b'"}'
    r = c.post("/api/login", content=big, headers={"content-type": "application/json"})
    check("announced oversize body refused", r.status_code == 413, r.status_code)
    r = c.post("/api/login", content=iter([big[i:i + 65536] for i in range(0, len(big), 65536)]),
               headers={"content-type": "application/json"})
    check("chunked oversize body refused too", r.status_code == 413, r.status_code)
    r = c.post("/api/login", json={"name": "admin", "password": "Supersecret1!"})
    check("normal bodies still pass", r.status_code == 200, r.status_code)

    print("\n-- input checks")
    r = cj.patch(f"/api/athletes/{jan_id}", json={"display_name": "Jan", "color": "red;x:url(a)"})
    check("a colour that is not #rrggbb is refused", r.status_code == 422, r.status_code)
    r = cj.patch(f"/api/athletes/{jan_id}", json={"display_name": "Jan", "color": "#11aa22"})
    check("a proper colour is taken", r.status_code == 200 and r.json()["color"] == "#11aa22", r.text)
    r = cj.patch(f"/api/athletes/{jan_id}", json={"display_name": "Hacker", "is_admin": True})
    check("refused self-promotion", r.status_code == 403, r.status_code)
    check("and it changed nothing", cj.get("/api/me").json()["display_name"] == "Jan")
    check("negative limit refused", cj.get("/api/sessions?limit=-1").status_code == 422)
    check("absurd day range refused", cj.get("/api/totals?days=99999999999").status_code == 422)
    r = TestClient(main.app).get("/api/invite/whatever")
    check("invitation codes are no longer taken in the path", r.status_code in (404, 405), r.status_code)

    print("\n-- revoking closes what is open")
    tok = cj.post(f"/api/athletes/{jan_id}/tokens", json={"label": "esp"}).json()["token"]
    tid = cj.get(f"/api/athletes/{jan_id}/tokens").json()[0]["id"]
    with c.websocket_connect("/ws/uplink") as up:
        up.send_json({"type": "hello", "token": tok, "agent": "t"})
        check("device signed in", up.receive_json()["type"] == "welcome")
        cj.delete(f"/api/athletes/{jan_id}/tokens/{tid}")
        try:
            while True:
                if up.receive_json().get("type") not in ("ping",):
                    break
            still_open = True
        except Exception:
            still_open = False
        check("revoking the token drops the open uplink", not still_open)
    check("the athlete shows offline", not main.hub.uplinks.get(jan_id))

    lc = TestClient(main.app)
    lc.post("/api/login", json={"name": "jan", "password": "Rudern-2026!"})
    with lc.websocket_connect("/ws/live") as live:
        check("live feed open", live.receive_json()["type"] == "hello")
        lc.post("/api/logout")
        try:
            while live.receive_json():
                pass
            still_open = True
        except Exception:
            still_open = False
        check("signing out closes the live feed", not still_open)

    print("\n-- live feed origin")
    cj.post("/api/login", json={"name": "jan", "password": "Rudern-2026!"})
    check("a foreign page cannot open the live feed",
          closed(cj.websocket_connect("/ws/live", headers={"origin": "https://evil.example"})))
    with cj.websocket_connect("/ws/live", headers={"origin": "http://testserver"}) as live:
        check("the arena's own page can", live.receive_json()["type"] == "hello")

    print("\n-- uplink hello")
    check("a token that is not text is refused",
          closed(c.websocket_connect("/ws/uplink"), {"type": "hello", "token": ["x"]}))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
