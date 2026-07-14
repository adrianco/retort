"""
Context
=======
Shared pytest fixtures and helpers for the Brazilian Soccer MCP acceptance
suite.

These helpers let each acceptance scenario exercise the System Under Test
*only* through the public MCP interface: a real MCP client session is connected
in-memory to a freshly built server, and tools are invoked by name with
arguments exactly as an external MCP client (e.g. an LLM) would.

Each scenario builds its own tiny, controlled dataset in a temporary directory
("a running but empty system" seeded with just the data that scenario needs),
so tests are atomic, independent and deterministic. No test reaches into server
internals.
"""

from __future__ import annotations

import contextlib
import csv
import json
from pathlib import Path

import pytest

from mcp.shared.memory import create_connected_server_and_client_session

from brazilian_soccer_mcp.server import create_server


# ---------------------------------------------------------------------------
# Dataset builder — writes CSVs in the real Kaggle schemas to a temp dir.
# ---------------------------------------------------------------------------
class DatasetBuilder:
    """Builds CSV files in the exact schemas of the provided Kaggle datasets."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _write(self, name: str, header: list[str], rows: list[list]):
        path = self.root / name
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(header)
            for row in rows:
                writer.writerow(row)

    def brasileirao(self, rows: list[dict]):
        header = [
            "datetime", "home_team", "home_team_state", "away_team",
            "away_team_state", "home_goal", "away_goal", "season", "round",
        ]
        self._write("Brasileirao_Matches.csv", header, [
            [r["datetime"], r["home_team"], r.get("home_state", ""),
             r["away_team"], r.get("away_state", ""), r["home_goal"],
             r["away_goal"], r["season"], r.get("round", "")]
            for r in rows
        ])

    def copa_do_brasil(self, rows: list[dict]):
        header = ["round", "datetime", "home_team", "away_team",
                  "home_goal", "away_goal", "season"]
        self._write("Brazilian_Cup_Matches.csv", header, [
            [r.get("round", ""), r["datetime"], r["home_team"], r["away_team"],
             r["home_goal"], r["away_goal"], r["season"]]
            for r in rows
        ])

    def libertadores(self, rows: list[dict]):
        header = ["datetime", "home_team", "away_team", "home_goal",
                  "away_goal", "season", "stage"]
        self._write("Libertadores_Matches.csv", header, [
            [r["datetime"], r["home_team"], r["away_team"], r["home_goal"],
             r["away_goal"], r["season"], r.get("stage", "")]
            for r in rows
        ])

    def br_football(self, rows: list[dict]):
        header = ["tournament", "home", "home_goal", "away_goal", "away",
                  "home_corner", "away_corner", "home_attack", "away_attack",
                  "home_shots", "away_shots", "time", "date", "ht_diff",
                  "at_diff", "ht_result", "at_result", "total_corners"]
        self._write("BR-Football-Dataset.csv", header, [
            [r["tournament"], r["home"], r["home_goal"], r["away_goal"],
             r["away"], "", "", "", "", "", "", r.get("time", ""), r["date"],
             "", "", "", "", ""]
            for r in rows
        ])

    def historical(self, rows: list[dict]):
        header = ["ID", "Data", "Ano", "Rodada", "Equipe_mandante",
                  "Equipe_visitante", "Gols_mandante", "Gols_visitante",
                  "Mandante_UF", "Visitante_UF", "Vencedor", "Arena", "OBS"]
        self._write("novo_campeonato_brasileiro.csv", header, [
            [r.get("id", ""), r["data"], r["ano"], r.get("rodada", ""),
             r["home_team"], r["away_team"], r["home_goal"], r["away_goal"],
             r.get("home_state", ""), r.get("away_state", ""),
             r.get("winner", ""), r.get("arena", ""), ""]
            for r in rows
        ])

    def fifa_players(self, rows: list[dict]):
        # The real file has a leading (BOM) unnamed index column; reproduce it.
        header = ["", "ID", "Name", "Age", "Nationality", "Overall",
                  "Potential", "Club", "Position", "Jersey Number"]
        self._write("fifa_data.csv", header, [
            [i, 1000 + i, r["name"], r.get("age", ""), r["nationality"],
             r["overall"], r.get("potential", r["overall"]), r.get("club", ""),
             r.get("position", ""), r.get("jersey", "")]
            for i, r in enumerate(rows)
        ])


@pytest.fixture
def dataset(tmp_path) -> DatasetBuilder:
    """A fresh, empty dataset directory unique to each test."""
    return DatasetBuilder(tmp_path / "data")


class SoccerClient:
    """An external MCP client for the test's dataset.

    Each operation opens a fresh in-memory MCP session, performs the handshake,
    issues one request and tears the session down — all within the calling
    test's own task. The server reads the dataset directory when the session is
    created, so a test seeds its CSVs first and then makes calls. The system is
    only ever touched through MCP tool calls.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    @contextlib.asynccontextmanager
    async def _session(self):
        server = create_server(str(self.data_dir))
        async with create_connected_server_and_client_session(server) as session:
            await session.initialize()
            yield session

    async def list_tools(self):
        async with self._session() as session:
            return await session.list_tools()

    async def call_tool(self, tool: str, arguments: dict):
        async with self._session() as session:
            return await session.call_tool(tool, arguments)


@pytest.fixture
def client(dataset) -> SoccerClient:
    """An MCP client bound to the test's own (initially empty) dataset."""
    return SoccerClient(dataset.root)


async def call(client: SoccerClient, tool: str, **arguments):
    """Invoke an MCP tool by name and return its structured result as a dict.

    This is the only way the acceptance tests touch the system: by name,
    through the MCP protocol, reading back the structured tool output.
    """
    result = await client.call_tool(tool, arguments)
    assert result.isError is False, _error_text(result)
    if result.structuredContent is not None:
        return result.structuredContent
    # Fall back to parsing text content as JSON.
    return json.loads(result.content[0].text)


async def call_expecting_error(client: SoccerClient, tool: str, **arguments):
    result = await client.call_tool(tool, arguments)
    assert result.isError is True, "expected the tool call to report an error"
    return _error_text(result)


def _error_text(result) -> str:
    parts = []
    for block in result.content:
        parts.append(getattr(block, "text", str(block)))
    return "\n".join(parts)
