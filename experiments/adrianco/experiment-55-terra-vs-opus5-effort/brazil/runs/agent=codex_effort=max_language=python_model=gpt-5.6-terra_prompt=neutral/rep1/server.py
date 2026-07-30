"""A dependency-free stdio MCP server for the Brazilian soccer datasets.

Run with ``python3 server.py`` and configure it as an MCP stdio server.  The
implementation speaks JSON-RPC 2.0 using the MCP tools lifecycle, so it does not
depend on a particular FastMCP or Pydantic version.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from io import TextIOBase
from pathlib import Path
from typing import Any, Callable, Mapping

from soccer_data import (
    BRASILEIRAO,
    COPA_DO_BRASIL,
    LIBERTADORES,
    SoccerRepository,
    display_team_name,
    normalize_competition_name,
    normalize_text,
)

SERVER_NAME = "brazilian-soccer-mcp"
SERVER_VERSION = "1.0.0"
DEFAULT_PROTOCOL_VERSION = "2025-03-26"


def _string(description: str, *, required: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "string", "description": description}
    if required:
        result["minLength"] = 1
    return result


def _integer(description: str, *, minimum: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "integer", "description": description}
    if minimum is not None:
        result["minimum"] = minimum
    return result


def _boolean(description: str) -> dict[str, Any]:
    return {"type": "boolean", "description": description}


def _schema(
    properties: Mapping[str, Mapping[str, Any]], *required: str
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "object",
        "properties": dict(properties),
        "additionalProperties": False,
    }
    if required:
        result["required"] = list(required)
    return result


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """A serialisable MCP tool plus its repository-backed handler."""

    name: str
    description: str
    input_schema: Mapping[str, Any]
    handler: Callable[..., dict[str, Any]]

    def to_mcp_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": dict(self.input_schema),
        }


class BrazilianSoccerMCPServer:
    """MCP tool registry and JSON-RPC dispatcher.

    The public ``call_tool`` method is deliberately useful without a subprocess,
    which makes the server straightforward to test and integrate in-process.
    """

    def __init__(self, repository: SoccerRepository | None = None):
        self.repository = repository or SoccerRepository.from_default_data()
        self._tools = self._build_tools()

    def _build_tools(self) -> dict[str, ToolDefinition]:
        match_filter_properties = {
            "team": _string("A team appearing home or away; accents and state suffixes are normalized."),
            "opponent": _string("A second team appearing in the same match."),
            "home_team": _string("Restrict to this home team."),
            "away_team": _string("Restrict to this away team."),
            "competition": _string("Competition, e.g. Brasileirão, Copa do Brasil, or Libertadores."),
            "season": _integer("Season year, such as 2023.", minimum=1800),
            "date_from": _string("Inclusive start date in ISO (YYYY-MM-DD) or Brazilian (DD/MM/YYYY) format."),
            "date_to": _string("Inclusive end date in ISO (YYYY-MM-DD) or Brazilian (DD/MM/YYYY) format."),
            "round": _string("Round number or label."),
            "stage": _string("Tournament stage, for example group stage or final."),
            "source": _string("Optional source filename fragment; omit to search all match datasets."),
            "limit": _integer("Maximum rows returned (1-1000).", minimum=1),
            "offset": _integer("Rows to skip for pagination.", minimum=0),
            "descending": _boolean("Sort newest first when true (the default)."),
        }
        tools = [
            ToolDefinition(
                "dataset_summary",
                "Describe the bundled CSV coverage, source row counts, and available competitions.",
                _schema({}),
                lambda: self.repository.dataset_summary(),
            ),
            ToolDefinition(
                "search_matches",
                "Find source match rows by team, opponent, date range, competition, season, round, or stage. Raw searches preserve each dataset source.",
                _schema(match_filter_properties),
                self.repository.search_matches,
            ),
            ToolDefinition(
                "latest_match",
                "Find the most recent completed match for a team, optionally against a particular opponent.",
                _schema(
                    {
                        "team": _string("Team to look up.", required=True),
                        "opponent": _string("Optional opposing team."),
                        "competition": _string("Optional competition filter."),
                        "source": _string("Optional source filename fragment."),
                    },
                    "team",
                ),
                self.repository.latest_match,
            ),
            ToolDefinition(
                "team_statistics",
                "Calculate a team's completed-match record: wins, draws, losses, goals, points, and win rate.",
                _schema(
                    {
                        "team": _string("Team to analyse.", required=True),
                        "season": _integer("Optional season year.", minimum=1800),
                        "competition": _string("Optional competition filter."),
                        "venue": _string("all (default), home, or away."),
                        "source": _string("Optional source filename fragment."),
                    },
                    "team",
                ),
                self.repository.team_statistics,
            ),
            ToolDefinition(
                "compare_teams",
                "Calculate a head-to-head record and list recent meetings between two teams.",
                _schema(
                    {
                        "team_a": _string("First team.", required=True),
                        "team_b": _string("Second team.", required=True),
                        "competition": _string("Optional competition filter."),
                        "season": _integer("Optional season year.", minimum=1800),
                        "source": _string("Optional source filename fragment."),
                        "recent_limit": _integer("Recent matches to include (1-1000).", minimum=1),
                    },
                    "team_a",
                    "team_b",
                ),
                self.repository.compare_teams,
            ),
            ToolDefinition(
                "standings",
                "Calculate final or in-progress standings from completed match scores, using one authoritative source per competition/season to avoid duplicate rows.",
                _schema(
                    {
                        "season": _integer("Season year.", minimum=1800),
                        "competition": _string("Competition; defaults to Brasileirão Série A."),
                        "source": _string("Optional exact source preference."),
                        "limit": _integer("Number of ranked teams to return.", minimum=1),
                    },
                    "season",
                ),
                self.repository.standings,
            ),
            ToolDefinition(
                "competition_statistics",
                "Calculate goals per match plus home-win, away-win, and draw rates.",
                _schema(
                    {
                        "competition": _string("Optional competition filter."),
                        "season": _integer("Optional season year.", minimum=1800),
                        "source": _string("Optional source filename fragment."),
                    }
                ),
                self.repository.competition_statistics,
            ),
            ToolDefinition(
                "best_team_records",
                "Rank teams by completed-match points for all, home, or away fixtures.",
                _schema(
                    {
                        "venue": _string("all, home, or away; defaults to away."),
                        "competition": _string("Optional competition filter."),
                        "season": _integer("Optional season year.", minimum=1800),
                        "source": _string("Optional source filename fragment."),
                        "limit": _integer("Number of teams to return.", minimum=1),
                    }
                ),
                self.repository.best_team_records,
            ),
            ToolDefinition(
                "biggest_wins",
                "List the largest completed winning margins in the selected dataset slice.",
                _schema(
                    {
                        "competition": _string("Optional competition filter."),
                        "season": _integer("Optional season year.", minimum=1800),
                        "source": _string("Optional source filename fragment."),
                        "limit": _integer("Number of matches to return.", minimum=1),
                    }
                ),
                self.repository.biggest_wins,
            ),
            ToolDefinition(
                "team_competitions",
                "Show every competition, season, and source in which a team appears.",
                _schema(
                    {
                        "team": _string("Team to inspect.", required=True),
                        "source": _string("Optional source filename fragment."),
                    },
                    "team",
                ),
                self.repository.team_competitions,
            ),
            ToolDefinition(
                "derbies",
                "Find traditional Brazilian derby fixtures, including Fla-Flu, Grenal, Ba-Vi, and major São Paulo classics.",
                _schema(
                    {
                        "season": _integer("Optional season year.", minimum=1800),
                        "competition": _string("Optional competition filter."),
                        "source": _string("Optional source filename fragment."),
                        "limit": _integer("Number of matches to return.", minimum=1),
                    }
                ),
                self.repository.derbies,
            ),
            ToolDefinition(
                "competition_bracket",
                "Group a cup competition's season fixtures by supplied stage or round, useful for a Libertadores or Copa do Brasil bracket view.",
                _schema(
                    {
                        "season": _integer("Season year.", minimum=1800),
                        "competition": _string("Cup competition; defaults to Copa Libertadores."),
                        "source": _string("Optional source filename fragment."),
                    },
                    "season",
                ),
                self.repository.competition_bracket,
            ),
            ToolDefinition(
                "find_finals",
                "Find final fixtures. Libertadores uses its explicit stage label; complete Copa do Brasil seasons use their final numbered round.",
                _schema(
                    {
                        "competition": _string("Competition to inspect.", required=True),
                        "season": _integer("Optional season year.", minimum=1800),
                        "source": _string("Optional source filename fragment."),
                        "limit": _integer("Number of matches to return.", minimum=1),
                    },
                    "competition",
                ),
                self.repository.finals,
            ),
            ToolDefinition(
                "relegated_teams",
                "Return the bottom teams from calculated standings; defaults to the bottom four of Brasileirão Série A.",
                _schema(
                    {
                        "season": _integer("Season year.", minimum=1800),
                        "competition": _string("Competition; defaults to Brasileirão Série A."),
                        "count": _integer("Number of bottom-ranked teams; defaults to 4.", minimum=1),
                        "source": _string("Optional source filename fragment."),
                    },
                    "season",
                ),
                self.repository.relegated_teams,
            ),
            ToolDefinition(
                "top_scoring_teams",
                "Rank teams by total goals scored in calculated competition standings. Player-level scorers are not present in the supplied match data.",
                _schema(
                    {
                        "season": _integer("Season year.", minimum=1800),
                        "competition": _string("Competition; defaults to Brasileirão Série A."),
                        "source": _string("Optional source filename fragment."),
                        "limit": _integer("Number of teams to return.", minimum=1),
                    },
                    "season",
                ),
                self.repository.top_scoring_teams,
            ),
            ToolDefinition(
                "team_profile",
                "Cross-reference a team's match record and competition history with FIFA players at a matching club.",
                _schema(
                    {
                        "team": _string("Team to profile.", required=True),
                        "season": _integer("Optional season year.", minimum=1800),
                        "competition": _string("Optional competition filter for match statistics."),
                        "player_limit": _integer("Maximum matching FIFA players to include.", minimum=1),
                    },
                    "team",
                ),
                self.repository.team_profile,
            ),
            ToolDefinition(
                "compare_seasons",
                "Compare two seasons' aggregate statistics and calculated champion for a competition.",
                _schema(
                    {
                        "first_season": _integer("First season year.", minimum=1800),
                        "second_season": _integer("Second season year.", minimum=1800),
                        "competition": _string("Competition; defaults to Brasileirão Série A."),
                        "source": _string("Optional source filename fragment."),
                    },
                    "first_season",
                    "second_season",
                ),
                self.repository.compare_seasons,
            ),
            ToolDefinition(
                "search_players",
                "Search FIFA players by name, nationality, club, position or rating. Position accepts roles such as forwards and midfielders.",
                _schema(
                    {
                        "name": _string("Full or partial player name."),
                        "nationality": _string("Nationality, for example Brazil."),
                        "club": _string("Full or partial club name."),
                        "position": _string("Position code (ST, GK, etc.) or group such as forwards."),
                        "min_overall": _integer("Minimum FIFA overall rating.", minimum=0),
                        "max_overall": _integer("Maximum FIFA overall rating.", minimum=0),
                        "limit": _integer("Maximum rows returned (1-1000).", minimum=1),
                        "offset": _integer("Rows to skip for pagination.", minimum=0),
                        "include_attributes": _boolean("Include individual skill ratings; defaults to true."),
                    }
                ),
                self.repository.search_players,
            ),
            ToolDefinition(
                "top_players",
                "Return the highest-rated players, optionally filtered by nationality, club, or position.",
                _schema(
                    {
                        "nationality": _string("Optional nationality filter."),
                        "club": _string("Optional club filter."),
                        "position": _string("Optional position or position-group filter."),
                        "limit": _integer("Number of players to return.", minimum=1),
                    }
                ),
                self.repository.top_players,
            ),
            ToolDefinition(
                "ask_brazilian_soccer",
                "Answer a supported natural-language soccer question by routing it to the appropriate data tool. For complex questions, use the specialised tools directly.",
                _schema({"question": _string("Natural-language question.", required=True)}, "question"),
                self.ask_brazilian_soccer,
            ),
        ]
        return {tool.name: tool for tool in tools}

    def list_tools(self) -> list[dict[str, Any]]:
        return [self._tools[name].to_mcp_dict() for name in sorted(self._tools)]

    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Call a tool directly and return structured data.

        Validation errors are raised here for normal Python callers; the MCP
        request handler below converts them to an MCP tool error result.
        """

        try:
            tool = self._tools[name]
        except KeyError as exc:
            raise ValueError(f"Unknown tool: {name}") from exc
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            raise ValueError("Tool arguments must be an object")
        return tool.handler(**dict(arguments))

    def ask_brazilian_soccer(self, question: str) -> dict[str, Any]:
        """Route common natural-language questions to a structured tool call."""

        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        cleaned = question.strip().rstrip("?.! ")
        normalized = normalize_text(cleaned)
        year = _find_year(cleaned)
        competition = _competition_in_question(normalized)

        last_match = re.search(
            r"(?:when\s+did\s+)?(?P<team>.+?)\s+last\s+(?:play|played)\s+(?P<opponent>.+)$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if last_match:
            team = last_match.group("team").removeprefix("When did ").strip()
            opponent = last_match.group("opponent").strip()
            data = self.repository.latest_match(team, opponent=opponent, competition=competition)
            return _natural_response(question, "latest_match", data, _latest_match_summary(data))

        if ("who won" in normalized or "champion" in normalized) and year and competition:
            data = self.repository.standings(year, competition=competition, limit=1)
            champion = data["champion"] or "No completed standings are available"
            return _natural_response(question, "standings", data, f"{champion} leads the calculated {data['competition']} table for {year}.")

        mentioned_years = [int(value) for value in re.findall(r"\b(?:19\d{2}|20\d{2})\b", cleaned)]
        if "compare" in normalized and "season" in normalized and len(mentioned_years) >= 2:
            data = self.repository.compare_seasons(
                mentioned_years[0],
                mentioned_years[1],
                competition=competition or BRASILEIRAO,
            )
            return _natural_response(
                question,
                "compare_seasons",
                data,
                f"Compared {mentioned_years[0]} and {mentioned_years[1]} {data['competition']} data.",
            )

        if "standing" in normalized and year:
            data = self.repository.standings(year, competition=competition or BRASILEIRAO)
            return _natural_response(question, "standings", data, _standings_summary(data))

        if "derby" in normalized:
            data = self.repository.derbies(season=year, competition=competition)
            return _natural_response(question, "derbies", data, f"Found {data['total']} derby matches in the selected data.")

        if "relegat" in normalized and year:
            data = self.repository.relegated_teams(
                year, competition=competition or BRASILEIRAO
            )
            names = ", ".join(row["team"] for row in data["relegated_teams"])
            return _natural_response(question, "relegated_teams", data, f"The bottom teams are: {names}.")

        if ("most goals" in normalized or "scored the most" in normalized) and year:
            data = self.repository.top_scoring_teams(
                year, competition=competition or BRASILEIRAO, limit=1
            )
            leader = data["teams"][0] if data["teams"] else None
            summary = (
                f"{leader['team']} scored the most goals ({leader['goals_for']})."
                if leader
                else "No completed standings are available."
            )
            return _natural_response(question, "top_scoring_teams", data, summary)

        if "bracket" in normalized and year:
            data = self.repository.competition_bracket(
                year, competition=competition or LIBERTADORES
            )
            return _natural_response(question, "competition_bracket", data, f"Found {len(data['stages'])} stages in the bracket data.")

        if "final" in normalized and competition:
            data = self.repository.finals(competition=competition, season=year)
            return _natural_response(question, "find_finals", data, f"Found {data['total']} final fixtures in the selected data.")

        if "biggest win" in normalized or "largest win" in normalized or "biggest vict" in normalized:
            data = self.repository.biggest_wins(competition=competition, season=year)
            return _natural_response(question, "biggest_wins", data, _biggest_wins_summary(data))

        if "average goals" in normalized or "goals per match" in normalized:
            data = self.repository.competition_statistics(competition=competition, season=year)
            return _natural_response(
                question,
                "competition_statistics",
                data,
                f"The average is {data['goals_per_match']} goals per completed match.",
            )

        if "best away record" in normalized or "best home record" in normalized:
            venue = "away" if "away" in normalized else "home"
            data = self.repository.best_team_records(
                venue=venue, competition=competition, season=year, limit=1
            )
            leader = data["rankings"][0]["team"] if data["rankings"] else "No team"
            return _natural_response(question, "best_team_records", data, f"{leader} has the best {venue} record in this data slice.")

        player_club = re.search(
            r"(?:which|what|show(?:\s+me)?)\s+players?\s+(?:play|plays)\s+for\s+(.+)$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if player_club:
            club = player_club.group(1).strip()
            data = self.repository.search_players(club=club, limit=50)
            return _natural_response(question, "search_players", data, f"Found {data['total']} players at clubs matching {club}.")

        rating_club = re.search(
            r"(?:highest|top)[ -]?rated\s+players?\s+(?:at|for)\s+(.+)$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if rating_club:
            club = rating_club.group(1).strip()
            data = self.repository.top_players(club=club)
            return _natural_response(question, "top_players", data, f"Found {data['total']} players at clubs matching {club}.")

        if "top brazilian players" in normalized or "top brazil players" in normalized:
            data = self.repository.top_players(nationality="Brazil")
            return _natural_response(question, "top_players", data, "Top-rated Brazilian players are listed by FIFA overall rating.")

        player_role = re.search(
            r"(?:show(?:\s+me)?|find)\s+(?:all\s+)?(?P<position>forwards?|midfielders?|defenders?|goalkeepers?)\s+from\s+(?P<club>.+)$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if player_role:
            position = player_role.group("position")
            club = player_role.group("club").strip()
            data = self.repository.search_players(club=club, position=position, limit=50)
            return _natural_response(question, "search_players", data, f"Found {data['total']} {position} at clubs matching {club}.")

        if normalized.startswith("who is "):
            name = re.sub(r"^who is\s+", "", cleaned, flags=re.IGNORECASE)
            data = self.repository.search_players(name=name, limit=10)
            return _natural_response(question, "search_players", data, f"Found {data['total']} player matches for {name}.")

        home_record = re.search(
            r"(?:what is|show)?\s*(?P<team>.+?)[’']?s?\s+(?P<venue>home|away)\s+record(?:\s+in\s+(?P<year>\d{4}))?",
            cleaned,
            flags=re.IGNORECASE,
        )
        if home_record:
            team = home_record.group("team").strip()
            venue = home_record.group("venue").casefold()
            record_year = int(home_record.group("year")) if home_record.group("year") else year
            data = self.repository.team_statistics(
                team, season=record_year, competition=competition, venue=venue
            )
            return _natural_response(question, "team_statistics", data, _team_record_summary(data))

        competition_query = re.search(
            r"what competitions has\s+(?P<team>.+?)\s+played\s+in$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if competition_query:
            team = competition_query.group("team").strip()
            data = self.repository.team_competitions(team)
            return _natural_response(question, "team_competitions", data, f"Found {len(data['competitions'])} competitions for {data['team']}.")

        versus = re.search(
            r"(?:compare\s+)?(?P<a>.+?)\s+(?:vs\.?|versus|and)\s+(?P<b>.+?)(?:\s+head\s+to\s+head)?$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if "head to head" in normalized and versus:
            data = self.repository.compare_teams(
                versus.group("a").strip(),
                versus.group("b").strip(),
                competition=competition,
                season=year,
            )
            return _natural_response(question, "compare_teams", data, _head_to_head_summary(data))

        matchup = re.search(
            r"(?:show(?:\s+me)?|find)?\s*(?:all\s+)?(?P<a>.+?)\s+(?:vs\.?|versus)\s+(?P<b>.+?)\s+matches$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if matchup:
            team_a = matchup.group("a").strip()
            team_b = matchup.group("b").strip()
            data = self.repository.search_matches(
                team=team_a, opponent=team_b, competition=competition, season=year
            )
            return _natural_response(question, "search_matches", data, f"Found {data['total']} matching source rows for {team_a} and {team_b}.")

        team_matches = re.search(
            r"(?:what|which|show(?:\s+me)?)\s+matches\s+did\s+(?P<team>.+?)\s+(?:play|played)(?:\s+in\s+(?P<year>\d{4}))?$",
            cleaned,
            flags=re.IGNORECASE,
        )
        if team_matches:
            team = team_matches.group("team").strip()
            match_year = int(team_matches.group("year")) if team_matches.group("year") else year
            data = self.repository.search_matches(team=team, season=match_year, competition=competition)
            return _natural_response(question, "search_matches", data, f"Found {data['total']} matching source rows for {team}.")

        return _natural_response(
            question,
            None,
            {"available_tools": [tool["name"] for tool in self.list_tools()]},
            "I could not route that question reliably. Use a specialised tool with structured filters.",
        )

    def handle_request(self, request: Mapping[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC/MCP message, returning no response for notifications."""

        request_id = request.get("id")
        is_notification = "id" not in request
        method = request.get("method")
        if not isinstance(method, str):
            return None if is_notification else _rpc_error(request_id, -32600, "Invalid Request")

        try:
            if method == "initialize":
                params = request.get("params") or {}
                protocol_version = params.get("protocolVersion", DEFAULT_PROTOCOL_VERSION)
                result = {
                    "protocolVersion": protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "instructions": "Query bundled Brazilian soccer matches and FIFA player data using the available tools.",
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                params = request.get("params") or {}
                if not isinstance(params, Mapping) or not isinstance(params.get("name"), str):
                    raise ValueError("tools/call requires a string name")
                data = self.call_tool(params["name"], params.get("arguments") or {})
                result = _mcp_tool_success(data)
            elif method.startswith("notifications/"):
                return None
            else:
                return None if is_notification else _rpc_error(request_id, -32601, f"Method not found: {method}")
        except (ValueError, TypeError) as exc:
            if method == "tools/call":
                result = _mcp_tool_error(str(exc))
            else:
                return None if is_notification else _rpc_error(request_id, -32602, str(exc))
        except Exception as exc:  # keep the stdio protocol alive after a failed request
            if method == "tools/call":
                result = _mcp_tool_error(f"Unexpected server error: {exc}")
            else:
                return None if is_notification else _rpc_error(request_id, -32603, "Internal error")
        return None if is_notification else {"jsonrpc": "2.0", "id": request_id, "result": result}

    def run(self, input_stream: TextIOBase = sys.stdin, output_stream: TextIOBase = sys.stdout) -> None:
        """Serve newline-delimited MCP JSON-RPC requests until stdin closes."""

        for raw_line in input_stream:
            line = raw_line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                if not isinstance(request, Mapping):
                    raise ValueError("JSON-RPC request must be an object")
            except (json.JSONDecodeError, ValueError) as exc:
                response = _rpc_error(None, -32700, f"Parse error: {exc}")
            else:
                response = self.handle_request(request)
            if response is not None:
                output_stream.write(json.dumps(response, ensure_ascii=False, default=_json_default) + "\n")
                output_stream.flush()


def _find_year(question: str) -> int | None:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", question)
    return int(match.group(1)) if match else None


def _competition_in_question(normalized_question: str) -> str | None:
    if "libertadores" in normalized_question:
        return LIBERTADORES
    if "copa do brasil" in normalized_question or "brazilian cup" in normalized_question:
        return COPA_DO_BRASIL
    if "brasileirao" in normalized_question or "serie a" in normalized_question:
        return BRASILEIRAO
    return None


def _natural_response(question: str, route: str | None, data: dict[str, Any], answer: str) -> dict[str, Any]:
    return {"question": question, "route": route, "answer": answer, "data": data}


def _latest_match_summary(data: Mapping[str, Any]) -> str:
    match = data.get("match")
    if not match:
        return "No completed matching fixture was found."
    return f"{match['date']}: {match['home_team']} {match['score']} {match['away_team']} ({match['competition']})."


def _standings_summary(data: Mapping[str, Any]) -> str:
    champion = data.get("champion")
    if not champion:
        return "No completed matches are available for those standings."
    return f"{champion} leads the calculated {data['competition']} standings for {data['season']}."


def _team_record_summary(data: Mapping[str, Any]) -> str:
    return (
        f"{data['team']}: {data['matches']} matches, {data['wins']} wins, "
        f"{data['draws']} draws, {data['losses']} losses; "
        f"{data['goals_for']}-{data['goals_against']} goals."
    )


def _head_to_head_summary(data: Mapping[str, Any]) -> str:
    return (
        f"{data['team_a']} have {data['team_a_record']['wins']} wins, "
        f"{data['team_b']} have {data['team_b_record']['wins']}, and there are "
        f"{data['draws']} draws across {data['matches']} completed meetings."
    )


def _biggest_wins_summary(data: Mapping[str, Any]) -> str:
    victories = data.get("victories") or []
    if not victories:
        return "No completed matches were found."
    first = victories[0]
    return f"Largest margin: {first['winner']} won {first['score']} on {first['date']}."


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _mcp_tool_success(data: Mapping[str, Any]) -> dict[str, Any]:
    text = json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": dict(data),
        "isError": False,
    }


def _mcp_tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


_default_server: BrazilianSoccerMCPServer | None = None


def get_server() -> BrazilianSoccerMCPServer:
    """Return a lazily-created default server for embedding or interactive use."""

    global _default_server
    if _default_server is None:
        _default_server = BrazilianSoccerMCPServer()
    return _default_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Brazilian soccer MCP stdio server")
    parser.add_argument("--data-dir", type=Path, help="Directory containing the six CSV files")
    parser.add_argument(
        "--summary", action="store_true", help="Print dataset metadata and exit instead of serving MCP"
    )
    args = parser.parse_args(argv)
    server = BrazilianSoccerMCPServer(
        SoccerRepository(args.data_dir) if args.data_dir else SoccerRepository.from_default_data()
    )
    if args.summary:
        print(json.dumps(server.repository.dataset_summary(), ensure_ascii=False, indent=2))
        return 0
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BrazilianSoccerMCPServer",
    "SERVER_NAME",
    "SERVER_VERSION",
    "ToolDefinition",
    "get_server",
    "main",
]
