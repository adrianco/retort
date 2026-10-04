"""Protocol driver: talks MCP (JSON-RPC over stdio) to the real server."""
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MATCH_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2}): (.+?) (\d+)-(\d+) (.+?) \((.+?) (\d{4})(?:, .*)?\)$")
RANKED_LINE = re.compile(r"^\d+\. (.+?) - ")


def _fold(text):
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


class McpStdioDriver:
    def __init__(self):
        self.proc = None
        self.next_id = 0
        self.last_answer = None

    def start(self):
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join(ROOT, "server.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8",
        )
        init = self._rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                        "clientInfo": {"name": "acceptance", "version": "1"}})
        assert "serverInfo" in init, f"server did not initialise: {init}"
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools = {t["name"] for t in self._rpc("tools/list", {})["tools"]}
        assert tools, "server exposes no tools"

    def stop(self):
        if self.proc:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)

    def _send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _rpc(self, method, params):
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
        reply = json.loads(self.proc.stdout.readline())
        assert "error" not in reply, f"{method} failed: {reply['error']}"
        return reply["result"]

    def ask(self, tool, **arguments):
        arguments = {k: v for k, v in arguments.items() if v is not None}
        result = self._rpc("tools/call", {"name": tool, "arguments": arguments})
        assert not result.get("isError"), f"{tool} reported an error: {result}"
        self.last_answer = result["content"][0]["text"]
        return self.last_answer

    # --- assertions ------------------------------------------------------
    def _matches(self):
        return [m.groups() for m in map(MATCH_LINE.match, self.last_answer.splitlines()) if m]

    def confirm_matches_listed(self, exactly=None):
        matches = self._matches()
        assert matches, f"no matches listed in:\n{self.last_answer}"
        if exactly is not None:
            assert len(matches) == exactly, self.last_answer

    def confirm_every_match_involves(self, teams):
        self.confirm_matches_listed()
        for _, home, _, _, away, _, _ in self._matches():
            sides = _fold(home + " | " + away)
            for team in teams:
                assert _fold(team) in sides, f"{home} v {away} does not involve {team}"

    def confirm_every_match_has(self, season=None, competition=None):
        self.confirm_matches_listed()
        for m in self._matches():
            if season is not None:
                assert int(m[6]) == season, m
            if competition is not None:
                assert m[5] == competition, m

    def confirm_head_to_head(self):
        assert re.search(r"Head-to-head.*: .+ \d+ wins, .+ \d+ wins, \d+ draws", self.last_answer), self.last_answer

    def confirm_record(self, matches):
        found = re.search(r"Matches: (\d+)", self.last_answer)
        assert found and int(found.group(1)) == matches, self.last_answer

    def confirm_mentions(self, phrases):
        for p in phrases:
            assert p in self.last_answer, f"'{p}' not in:\n{self.last_answer}"

    def _ranked(self):
        return [m.group(1) for m in map(RANKED_LINE.match, self.last_answer.splitlines()) if m]

    def confirm_ranked_entries(self):
        assert self._ranked(), self.last_answer

    def confirm_first_ranked(self, name):
        ranked = self._ranked()
        assert ranked and ranked[0] == name, self.last_answer

    def confirm_champion(self, team, points):
        first = self.last_answer.splitlines()
        line = next(l for l in first if l.startswith("1. "))
        assert line.startswith(f"1. {team} - {points} pts") and "Champion" in line, line

    def confirm_relegated(self, count):
        assert self.last_answer.count("Relegated") == count, self.last_answer

    def confirm_answer_time(self, seconds, question, **criteria):
        tool = {"standings": "standings", "players": "search_players"}[question]
        start = time.monotonic()
        self.ask(tool, **criteria)
        assert time.monotonic() - start < seconds
