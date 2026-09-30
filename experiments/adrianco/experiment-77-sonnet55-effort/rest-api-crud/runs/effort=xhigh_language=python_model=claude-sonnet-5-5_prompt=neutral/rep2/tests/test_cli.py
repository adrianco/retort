"""Smoke test of the documented run command: ``python -m bookapi``."""

import http.client
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

SRC = str(Path(__file__).resolve().parent.parent / "src")


def test_module_entry_point_serves_requests(tmp_path):
    env = {**os.environ, "PYTHONPATH": SRC}
    proc = subprocess.Popen(
        [sys.executable, "-m", "bookapi", "--port", "0", "--db", str(tmp_path / "cli.db")],
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        line = proc.stderr.readline()
        match = re.search(r"http://127\.0\.0\.1:(\d+)", line)
        assert match, f"unexpected startup output: {line!r}"

        conn = http.client.HTTPConnection("127.0.0.1", int(match.group(1)), timeout=5)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        assert resp.status == 200
        assert json.loads(resp.read()) == {"status": "ok"}
        conn.close()

        proc.send_signal(signal.SIGINT)
        assert proc.wait(timeout=10) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        proc.stderr.close()
    assert (tmp_path / "cli.db").exists()
