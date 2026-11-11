"""Run every suite and report once.

Each suite is its own process, so a crash in one cannot take the others
with it. There is only one for now; the loop is kept so a second suite can
be added by naming it here.
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SUITES = ["smoke.py", "uplink_protocol.py", "security.py"]

results = []
for name in SUITES:
    print(f"{chr(10)}=== {name} {'=' * (60 - len(name))}")
    proc = subprocess.run([sys.executable, str(HERE / name)])
    results.append((name, proc.returncode))

print(f"{chr(10)}{'=' * 66}")
for name, code in results:
    print(f"  {'PASS' if code == 0 else 'FAIL'}  {name}")
sys.exit(1 if any(code for _, code in results) else 0)
