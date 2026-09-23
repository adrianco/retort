"""Tests for ``python -m books_api`` run as a real child process."""

import contextlib
import json
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="relies on POSIX signals")


@contextlib.contextmanager
def running_server(*args):
    """Start the CLI; yield the process and a queue of its stderr lines."""
    process = subprocess.Popen(
        [sys.executable, "-m", "books_api", "--host", "127.0.0.1", *args],
        cwd=PROJECT_ROOT,
        stderr=subprocess.PIPE,
        text=True,
    )
    lines: queue.Queue = queue.Queue()
    reader = threading.Thread(target=lambda: [lines.put(line) for line in process.stderr], daemon=True)
    reader.start()
    try:
        yield process, lines
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        reader.join(timeout=5)
        process.stderr.close()


def wait_for_line(lines, pattern, timeout=10):
    seen = []
    while True:
        try:
            line = lines.get(timeout=timeout)
        except queue.Empty:
            pytest.fail(f"timed out waiting for {pattern!r}; output so far: {seen}")
        seen.append(line)
        match = re.search(pattern, line)
        if match:
            return match


def test_serves_requests_and_stops_cleanly_on_sigterm(tmp_path):
    db_path = tmp_path / "data" / "books.db"
    with running_server("--port", "0", "--db", str(db_path)) as (process, lines):
        port = int(wait_for_line(lines, r"Serving on http://127\.0\.0\.1:(\d+)").group(1))
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as response:
            assert response.status == 200
            assert json.load(response) == {"status": "ok", "database": "ok"}

        process.send_signal(signal.SIGTERM)
        wait_for_line(lines, "Shutting down")
        assert process.wait(timeout=10) == 0
    assert db_path.exists()


def test_exits_with_error_when_port_is_taken(tmp_path):
    with socket.socket() as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen()
        port = blocker.getsockname()[1]
        with running_server("--port", str(port), "--db", str(tmp_path / "books.db")) as (process, lines):
            wait_for_line(lines, rf"Cannot listen on 127\.0\.0\.1:{port}")
            assert process.wait(timeout=10) == 1


def test_exits_with_error_when_database_cannot_be_opened(tmp_path):
    not_a_file = tmp_path / "a-directory"
    not_a_file.mkdir()
    with running_server("--port", "0", "--db", str(not_a_file)) as (process, lines):
        wait_for_line(lines, "Cannot open database")
        assert process.wait(timeout=10) == 1
