"""Starts the server the way a user would, via ``python -m bookapi``."""

import json
import re
import signal
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_cli_serves_requests_and_shuts_down_cleanly_on_interrupt(tmp_path):
    db_path = tmp_path / "books.db"
    process = subprocess.Popen(
        [sys.executable, "-m", "bookapi", "--port", "0", "--db", str(db_path)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        banner = process.stdout.readline()
        match = re.search(r"http://127\.0\.0\.1:(\d+)", banner)
        assert match, f"unexpected startup output: {banner!r}"
        base = f"http://127.0.0.1:{match.group(1)}"

        with urllib.request.urlopen(f"{base}/health", timeout=5) as response:
            assert json.loads(response.read()) == {"status": "ok"}

        assert db_path.exists()
    finally:
        process.send_signal(signal.SIGINT)
        returncode = process.wait(timeout=10)
        process.stdout.close()
        process.stderr.close()

    assert returncode == 0
