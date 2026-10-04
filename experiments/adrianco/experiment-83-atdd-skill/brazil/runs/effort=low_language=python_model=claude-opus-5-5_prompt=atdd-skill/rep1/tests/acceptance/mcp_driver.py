"""Protocol driver: the only test layer that knows the system is an MCP server.

Calls tools over the MCP protocol (in-memory transport) and makes the
assertions on the text answers.
"""
import re
import time

import anyio
from mcp import Client

from server import mcp as soccer_server


class McpProtocolDriver:
    def __init__(self):
        self.last_answer = None
        self.elapsed = None

    def ask(self, tool, **arguments):
        arguments = {k: v for k, v in arguments.items() if v is not None}

        async def call():
            async with Client(soccer_server) as client:
                return await client.call_tool(tool, arguments)

        start = time.perf_counter()
        result = anyio.run(call)
        self.elapsed = time.perf_counter() - start
        text = "\n".join(c.text for c in result.content if getattr(c, "text", None))
        assert not result.is_error, f"Tool {tool} failed: {text}"
        self.last_answer = text

    def _fail(self, message):
        raise AssertionError(f"{message}\n--- answer ---\n{self.last_answer}")

    def confirm_answer_equals(self, expected):
        if self.last_answer != expected:
            self._fail(f"Expected same answer as before:\n{expected}")

    def confirm_answer_mentions(self, *phrases):
        lower = self.last_answer.lower()
        missing = [p for p in phrases if p.lower() not in lower]
        if missing:
            self._fail(f"Answer did not mention {missing}")

    def confirm_match_listed(self, date, home, home_goals, away, away_goals):
        expected = f"{date}: {home} {home_goals}-{away_goals} {away}"
        if expected not in self.last_answer:
            self._fail(f"Expected match '{expected}'")

    def confirm_match_count(self, count):
        m = re.search(r"Found (\d+) match", self.last_answer)
        if not m or int(m.group(1)) != count:
            self._fail(f"Expected {count} matches")

    def confirm_record(self, matches):
        m = re.search(r"Matches: (\d+)", self.last_answer)
        if not m or int(m.group(1)) != matches:
            self._fail(f"Expected record over {matches} matches")

    def confirm_champion(self, team, points):
        m = re.search(r"^1\. (.+?) - (\d+) pts", self.last_answer, re.M)
        if not m or m.group(1) != team or (points is not None and int(m.group(2)) != points):
            self._fail(f"Expected champion {team} ({points} pts)")

    def confirm_first_player(self, name):
        m = re.search(r"^1\. (.+?) - Overall", self.last_answer, re.M)
        if not m or m.group(1) != name:
            self._fail(f"Expected first player {name}")

    def confirm_every_player_has_position(self, position):
        positions = re.findall(r"Position: (\w+)", self.last_answer)
        if not positions or any(p != position for p in positions):
            self._fail(f"Expected only {position} players")

    def confirm_answer_line_count_at_least(self, n):
        if len(re.findall(r"^\d+\. ", self.last_answer, re.M)) < n:
            self._fail(f"Expected at least {n} ranked lines")

    def confirm_answered_within(self, seconds):
        if self.elapsed > seconds:
            self._fail(f"Took {self.elapsed:.2f}s, limit {seconds}s")
