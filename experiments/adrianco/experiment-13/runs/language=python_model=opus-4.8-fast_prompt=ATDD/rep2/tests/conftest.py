"""Acceptance-test harness for the Brazilian Soccer MCP server.

Tests interact with the system the way a real client would: by starting the MCP
server over an in-memory transport and calling its tools through a genuine
``ClientSession`` (the MCP protocol). There is no back-door access to the
server's internals.

Each test builds its own isolated dataset on a temporary directory ("a running
but empty system" seeded only with the rows that scenario needs), so tests
share no data and can run in any order.
"""

from __future__ import annotations

import csv
import json
import os
from contextlib import asynccontextmanager

import pytest

from mcp.shared.memory import create_connected_server_and_client_session

from brazilian_soccer_mcp import create_server


# Column layouts of the real CSV files, so fixtures exercise the same parsing
# code path as the production datasets.
_HEADERS = {
    "Brasileirao_Matches.csv": [
        "datetime", "home_team", "home_team_state", "away_team",
        "away_team_state", "home_goal", "away_goal", "season", "round",
    ],
    "Brazilian_Cup_Matches.csv": [
        "round", "datetime", "home_team", "away_team",
        "home_goal", "away_goal", "season",
    ],
    "Libertadores_Matches.csv": [
        "datetime", "home_team", "away_team",
        "home_goal", "away_goal", "season", "stage",
    ],
    "novo_campeonato_brasileiro.csv": [
        "ID", "Data", "Ano", "Rodada", "Equipe_mandante", "Equipe_visitante",
        "Gols_mandante", "Gols_visitante", "Mandante_UF", "Visitante_UF",
        "Vencedor", "Arena", "OBS",
    ],
    "BR-Football-Dataset.csv": [
        "tournament", "home", "home_goal", "away_goal", "away",
        "home_corner", "away_corner", "home_attack", "away_attack",
        "home_shots", "away_shots", "time", "date", "ht_diff", "at_diff",
        "ht_result", "at_result", "total_corners",
    ],
    "fifa_data.csv": [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club",
        "Position", "Jersey Number", "Height", "Weight",
    ],
}


class SoccerSystem:
    """A builder for an isolated soccer dataset and its running MCP server."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self._rows: dict[str, list[dict]] = {}

    # -- seeding helpers (the "Given" of each scenario) ------------------ #
    def add_brasileirao_match(
        self, home, away, home_goal, away_goal, season,
        round=1, date=None, home_state="SP", away_state="SP",
    ):
        self._rows.setdefault("Brasileirao_Matches.csv", []).append({
            "datetime": date or f"{season}-05-01 16:00:00",
            "home_team": home, "home_team_state": home_state,
            "away_team": away, "away_team_state": away_state,
            "home_goal": home_goal, "away_goal": away_goal,
            "season": season, "round": round,
        })

    def add_historical_match(
        self, home, away, home_goal, away_goal, season,
        round=1, date=None, arena="Stadium",
    ):
        self._rows.setdefault("novo_campeonato_brasileiro.csv", []).append({
            "ID": f"{season}.01.{len(self._rows.get('novo_campeonato_brasileiro.csv', [])) + 1:04d}",
            "Data": date or f"01/05/{season}",
            "Ano": season, "Rodada": round,
            "Equipe_mandante": home, "Equipe_visitante": away,
            "Gols_mandante": home_goal, "Gols_visitante": away_goal,
            "Mandante_UF": "SP", "Visitante_UF": "RJ",
            "Vencedor": "Mandante", "Arena": arena, "OBS": "",
        })

    def add_cup_match(
        self, home, away, home_goal, away_goal, season, round="Final", date=None,
    ):
        self._rows.setdefault("Brazilian_Cup_Matches.csv", []).append({
            "round": round, "datetime": date or f"{season}-06-01 21:00:00",
            "home_team": home, "away_team": away,
            "home_goal": home_goal, "away_goal": away_goal, "season": season,
        })

    def add_libertadores_match(
        self, home, away, home_goal, away_goal, season,
        stage="group stage", date=None,
    ):
        self._rows.setdefault("Libertadores_Matches.csv", []).append({
            "datetime": date or f"{season}-04-01 20:00:00",
            "home_team": home, "away_team": away,
            "home_goal": home_goal, "away_goal": away_goal,
            "season": season, "stage": stage,
        })

    def add_extended_match(
        self, tournament, home, away, home_goal, away_goal, date,
        home_shots=0, away_shots=0,
    ):
        self._rows.setdefault("BR-Football-Dataset.csv", []).append({
            "tournament": tournament, "home": home, "away": away,
            "home_goal": home_goal, "away_goal": away_goal,
            "home_corner": 0, "away_corner": 0,
            "home_attack": 0, "away_attack": 0,
            "home_shots": home_shots, "away_shots": away_shots,
            "time": "20:00:00", "date": date, "ht_diff": 0, "at_diff": 0,
            "ht_result": "DRAW", "at_result": "DRAW", "total_corners": 0,
        })

    def add_player(
        self, name, nationality, overall, club, position,
        potential=None, age=25, jersey=10, height="5'9", weight="160lbs",
        player_id=None,
    ):
        rows = self._rows.setdefault("fifa_data.csv", [])
        self._rows["fifa_data.csv"].append({
            "ID": player_id if player_id is not None else 1000 + len(rows),
            "Name": name, "Age": age, "Nationality": nationality,
            "Overall": overall, "Potential": potential or overall,
            "Club": club, "Position": position, "Jersey Number": jersey,
            "Height": height, "Weight": weight,
        })

    # -- run the system -------------------------------------------------- #
    def _write_files(self):
        for filename, rows in self._rows.items():
            path = os.path.join(self.data_dir, filename)
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=_HEADERS[filename])
                writer.writeheader()
                writer.writerows(rows)

    @asynccontextmanager
    async def running(self):
        self._write_files()
        server = create_server(self.data_dir)
        async with create_connected_server_and_client_session(server) as session:
            yield ToolClient(session)


class ToolClient:
    """Thin wrapper that calls an MCP tool and returns its structured result."""

    def __init__(self, session):
        self._session = session

    async def call(self, tool_name: str, **arguments):
        result = await self._session.call_tool(tool_name, arguments)
        assert not result.isError, f"tool {tool_name} errored: {result.content}"
        if result.structuredContent is not None:
            return result.structuredContent
        # A client parses the tool's JSON text output.
        text = "".join(
            block.text for block in result.content
            if getattr(block, "type", None) == "text"
        )
        return json.loads(text)

    async def tools(self):
        listed = await self._session.list_tools()
        return {t.name for t in listed.tools}


@pytest.fixture
def soccer_system(tmp_path):
    """A fresh, empty soccer system seeded only by the test that uses it."""
    return SoccerSystem(str(tmp_path))
