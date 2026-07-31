"""MCP tool catalogue: JSON schemas, dispatch and result envelopes.

Context
-------
This module is the contract between the transport
(:mod:`brazilian_soccer.server`) and the domain logic
(:mod:`brazilian_soccer.queries`).  It owns:

* the sixteen tool definitions, each with a description written for an LLM
  reader and a JSON Schema for its arguments;
* :func:`call_tool`, which validates arguments, runs the query, renders the
  text answer and returns an MCP ``CallToolResult`` payload;
* the error envelope -- user-fixable problems come back as ``isError`` results
  with an explanation the model can act on (suggested club names, available
  seasons), never as protocol-level failures.

Keeping this separate from the transport is what lets the tests exercise every
tool without speaking JSON-RPC.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Any, Callable

from . import queries
from .formatting import render
from .graph import KnowledgeGraph

__all__ = ["Tool", "TOOLS", "TOOLS_BY_NAME", "list_tools", "call_tool"]


@dataclass(frozen=True)
class Tool:
    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., dict[str, Any]]

    def to_mcp(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


_TEAM = {"type": "string",
         "description": "Club name in any spelling: 'Flamengo', 'Palmeiras-SP', "
                        "'Atletico-MG', 'EC Bahia', 'Sao Paulo'."}
_COMPETITION = {"type": "string",
                "description": "Competition: 'brasileirao'/'serie-a', 'serie-b', "
                               "'serie-c', 'copa-do-brasil' or 'libertadores'. "
                               "Omit for all competitions."}
_SEASON = {"type": "integer", "description": "Season year, e.g. 2019."}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 500,
          "description": "Maximum rows to return (default 25)."}


TOOLS: tuple[Tool, ...] = (
    Tool(
        name="find_matches",
        title="Find matches",
        description=(
            "Search fixtures by team, opponent, venue, competition, season, date "
            "range or knockout stage. Use this for questions like 'show me all "
            "Flamengo vs Fluminense matches', 'what matches did Palmeiras play in "
            "2023?' or 'find all Copa do Brasil finals' (set stage='Final')."
        ),
        input_schema=_schema({
            "team": _TEAM,
            "opponent": {**_TEAM, "description":
                         "Restrict to fixtures against this club."},
            "venue": {"type": "string", "enum": ["home", "away", "any"],
                      "description": "Whether `team` played at home, away or either "
                                     "(default 'any')."},
            "competition": _COMPETITION,
            "season": _SEASON,
            "date_from": {"type": "string",
                          "description": "Earliest date, YYYY-MM-DD or DD/MM/YYYY."},
            "date_to": {"type": "string",
                        "description": "Latest date, YYYY-MM-DD or DD/MM/YYYY."},
            "stage": {"type": "string",
                      "description": "Knockout stage or round substring, e.g. "
                                     "'Final', 'Semifinals', 'Group stage'."},
            "limit": _LIMIT,
            "newest_first": {"type": "boolean",
                             "description": "Sort newest first (default true)."},
        }),
        handler=queries.find_matches,
    ),
    Tool(
        name="head_to_head",
        title="Head to head",
        description=(
            "Complete head-to-head record between two clubs: every meeting, the "
            "win/draw/loss split, goals, home and away breakdowns and the derby "
            "name when the fixture is a classic (Fla-Flu, Gre-Nal, Derby "
            "Paulista...). Use for 'compare Palmeiras and Santos head-to-head' or "
            "'when did Flamengo last play Corinthians?'."
        ),
        input_schema=_schema({
            "team_a": _TEAM,
            "team_b": _TEAM,
            "competition": _COMPETITION,
            "season": _SEASON,
            "limit": _LIMIT,
        }, required=["team_a", "team_b"]),
        handler=queries.head_to_head,
    ),
    Tool(
        name="team_stats",
        title="Team statistics",
        description=(
            "Win/draw/loss record, goals for and against, win rate and points per "
            "game for one club, optionally narrowed to a season, a competition or "
            "home/away only. Use for \"what is Corinthians' home record in 2022?\"."
        ),
        input_schema=_schema({
            "team": _TEAM,
            "season": _SEASON,
            "season_from": {"type": "integer", "description": "First season to include."},
            "season_to": {"type": "integer", "description": "Last season to include."},
            "competition": _COMPETITION,
            "venue": {"type": "string", "enum": ["home", "away", "all"],
                      "description": "Restrict to home or away fixtures "
                                     "(default 'all')."},
        }, required=["team"]),
        handler=queries.team_stats,
    ),
    Tool(
        name="team_profile",
        title="Team profile",
        description=(
            "A club's neighbourhood in the knowledge graph: which competitions and "
            "seasons it appears in, its overall record, most frequent opponents and "
            "derbies, stadiums used, every spelling of its name found in the source "
            "files, and its FIFA 19 squad if there is one. Use for 'what "
            "competitions has Palmeiras played in?'."
        ),
        input_schema=_schema({"team": _TEAM}, required=["team"]),
        handler=queries.team_profile,
    ),
    Tool(
        name="standings",
        title="League standings",
        description=(
            "League table for a season computed from match results (3 points for a "
            "win, 1 for a draw; ties broken by wins, goal difference then goals "
            "scored). Reports the champion and the relegation places when the "
            "season is complete. Use for 'who won the 2019 Brasileirão?' or "
            "'which teams were relegated in 2020?'."
        ),
        input_schema=_schema({
            "season": _SEASON,
            "competition": _COMPETITION,
        }, required=["season"]),
        handler=queries.standings,
    ),
    Tool(
        name="team_rankings",
        title="Rank teams by a metric",
        description=(
            "Rank clubs by points, wins, win rate, goals scored, goals conceded or "
            "goal difference, optionally home-only or away-only and scoped to a "
            "competition and season. Use for 'which team has the best away "
            "record?' or 'which team scored the most goals in Serie A 2023?'."
        ),
        input_schema=_schema({
            "metric": {"type": "string",
                       "enum": ["points", "points_per_game", "wins", "win_rate",
                                "goals_for", "goals_against", "goal_difference",
                                "goals_for_per_game", "goals_against_per_game",
                                "matches"],
                       "description": "Metric to rank by (default 'points'). "
                                      "'goals_against' ranks ascending."},
            "competition": _COMPETITION,
            "season": _SEASON,
            "venue": {"type": "string", "enum": ["home", "away", "all"],
                      "description": "Use only home or only away fixtures."},
            "min_matches": {"type": "integer",
                            "description": "Ignore clubs with fewer fixtures "
                                           "(default 10)."},
            "limit": _LIMIT,
        }),
        handler=queries.team_rankings,
    ),
    Tool(
        name="competition_stats",
        title="Competition statistics",
        description=(
            "Aggregate statistics for a competition: goals per match, home/away/draw "
            "rates, most common scorelines, top scoring teams and a season-by-season "
            "breakdown. Use for \"what's the average goals per match in the "
            "Brasileirão?\"."
        ),
        input_schema=_schema({
            "competition": _COMPETITION,
            "season": _SEASON,
            "season_from": {"type": "integer", "description": "First season."},
            "season_to": {"type": "integer", "description": "Last season."},
        }),
        handler=queries.competition_stats,
    ),
    Tool(
        name="biggest_wins",
        title="Biggest wins",
        description=(
            "The largest winning margins in the data, optionally restricted to one "
            "competition, season or club. Use for 'show me the biggest wins in the "
            "dataset'."
        ),
        input_schema=_schema({
            "competition": _COMPETITION,
            "season": _SEASON,
            "team": {**_TEAM, "description": "Only wins by this club."},
            "limit": _LIMIT,
        }),
        handler=queries.biggest_wins,
    ),
    Tool(
        name="compare_seasons",
        title="Compare seasons",
        description=(
            "Side-by-side aggregates for several seasons of one competition -- "
            "matches, goals per match, home win rate, champion and top three, or a "
            "single club's record in each season. Use for 'compare the 2018 and "
            "2019 seasons'."
        ),
        input_schema=_schema({
            "seasons": {"type": "array", "items": {"type": "integer"},
                        "minItems": 1,
                        "description": "Season years to compare, e.g. [2018, 2019]."},
            "competition": _COMPETITION,
            "team": {**_TEAM, "description": "Optional club to focus on."},
        }, required=["seasons"]),
        handler=queries.compare_seasons,
    ),
    Tool(
        name="find_derbies",
        title="Find derbies",
        description=(
            "Fixtures between traditional rivals, using a curated table of classic "
            "Brazilian derbies (Fla-Flu, Clássico dos Milhões, Derby Paulista, "
            "Majestoso, Choque-Rei, Gre-Nal, Clássico Mineiro, Atletiba, Ba-Vi, "
            "Clássico-Rei and more). Use for 'show me all derbies in 2023'."
        ),
        input_schema=_schema({
            "season": _SEASON,
            "competition": _COMPETITION,
            "team": {**_TEAM, "description": "Only derbies involving this club."},
            "limit": _LIMIT,
        }),
        handler=queries.find_derbies,
    ),
    Tool(
        name="search_players",
        title="Search players",
        description=(
            "Search the FIFA 19 player database by name, nationality, club, "
            "position, rating range or age range. Use for 'find all Brazilian "
            "players in the dataset', 'who are the highest-rated players at "
            "Grêmio?' or 'show me all forwards from Santos'."
        ),
        input_schema=_schema({
            "name": {"type": "string", "description": "Full or partial player name."},
            "nationality": {"type": "string",
                            "description": "Country, e.g. 'Brazil'."},
            "club": {"type": "string", "description": "Club name in any spelling."},
            "position": {"type": "string",
                         "description": "FIFA position code (LW, CDM, GK...) or a "
                                        "group: GK, DEF, MID, FWD."},
            "min_overall": {"type": "integer",
                            "description": "Minimum FIFA overall rating."},
            "max_overall": {"type": "integer",
                            "description": "Maximum FIFA overall rating."},
            "min_age": {"type": "integer", "description": "Minimum age in years."},
            "max_age": {"type": "integer", "description": "Maximum age in years."},
            "brazilian_clubs_only": {
                "type": "boolean",
                "description": "Only players at clubs that also appear in the "
                               "Brazilian match datasets."},
            "sort_by": {"type": "string",
                        "enum": ["overall", "potential", "age", "name"],
                        "description": "Sort order (default 'overall')."},
            "limit": _LIMIT,
        }),
        handler=queries.search_players,
    ),
    Tool(
        name="player_profile",
        title="Player profile",
        description=(
            "Full FIFA 19 profile for one player: ratings, club, position, physical "
            "attributes, contract and best skill attributes. Use for 'who is "
            "Gabriel Barbosa?' or 'tell me about Neymar'."
        ),
        input_schema=_schema({
            "name": {"type": "string", "description": "Player name, full or partial."},
        }, required=["name"]),
        handler=queries.player_profile,
    ),
    Tool(
        name="club_squad",
        title="Club squad",
        description=(
            "The FIFA 19 squad registered to a club, best rated first, with squad "
            "size, average rating and average age. Use for 'which players play for "
            "Grêmio?'. Note that FIFA 19 only licensed 15 Brazilian clubs."
        ),
        input_schema=_schema({
            "club": {"type": "string", "description": "Club name in any spelling."},
            "min_overall": {"type": "integer",
                            "description": "Only players at or above this rating."},
            "limit": _LIMIT,
        }, required=["club"]),
        handler=queries.club_squad,
    ),
    Tool(
        name="brazilian_players_by_club",
        title="Brazilian players by club",
        description=(
            "Cross-file query joining the FIFA player table to the clubs in the "
            "match datasets: how many Brazilian players each club has, their "
            "average rating, and the top-rated Brazilians overall. Use for 'who "
            "are the top Brazilian players?'."
        ),
        input_schema=_schema({
            "min_players": {"type": "integer",
                            "description": "Only clubs with at least this many "
                                           "Brazilian players (default 1)."},
            "limit": _LIMIT,
        }),
        handler=queries.brazilian_players_by_club,
    ),
    Tool(
        name="resolve_team",
        title="Resolve a team name",
        description=(
            "Explain how a club name normalises: the canonical club it maps to, "
            "every spelling found in the source files, how many matches and seasons "
            "exist for it, and warnings about similarly named clubs (Botafogo-RJ vs "
            "Botafogo-PB, the three Atléticos). Call this first when a club name is "
            "ambiguous or a search returns nothing."
        ),
        input_schema=_schema({
            "name": {"type": "string", "description": "Club name to resolve."},
        }, required=["name"]),
        handler=queries.resolve_team,
    ),
    Tool(
        name="dataset_summary",
        title="Dataset summary",
        description=(
            "What data is loaded: the six source files and their row counts, how "
            "many duplicate fixtures were merged, the competitions and season "
            "ranges available, club and player counts. Call this to check coverage "
            "before claiming something is missing."
        ),
        input_schema=_schema({}),
        handler=queries.dataset_summary,
    ),
)

TOOLS_BY_NAME: dict[str, Tool] = {tool.name: tool for tool in TOOLS}


def list_tools() -> list[dict[str, Any]]:
    """The payload for an MCP ``tools/list`` response."""
    return [tool.to_mcp() for tool in TOOLS]


def _as_int(tool_name: str, key: str, value: Any) -> int:
    """Coerce *value* to an int, rejecting booleans and non-numeric text."""
    if isinstance(value, bool):
        raise queries.QueryError(
            f"{tool_name}.{key} must be a whole number, got {value!r}.")
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise queries.QueryError(
            f"{tool_name}.{key} must be a whole number, got {value!r}.") from None


def _validate(tool: Tool, arguments: dict[str, Any]) -> dict[str, Any]:
    """Reject unknown keys and coerce obvious string/number mix-ups.

    A full JSON Schema validator would be overkill here: the schemas only use
    scalar types, enums and one array, and LLM clients routinely send "2019"
    where 2019 is expected, so coercion is more useful than strictness.
    """
    schema = tool.input_schema
    properties: dict[str, Any] = schema["properties"]
    unknown = set(arguments) - set(properties)
    if unknown:
        raise queries.QueryError(
            f"Unknown argument(s) for {tool.name}: {', '.join(sorted(unknown))}. "
            f"Valid arguments: {', '.join(sorted(properties))}.")
    missing = [key for key in schema.get("required", []) if arguments.get(key) in (None, "")]
    if missing:
        raise queries.QueryError(
            f"{tool.name} requires: {', '.join(missing)}.")

    cleaned: dict[str, Any] = {}
    for key, value in arguments.items():
        if value is None:
            continue
        spec = properties[key]
        expected = spec.get("type")
        if expected == "string" and not isinstance(value, str):
            # Numbers are a plausible slip ("season" style input in a name
            # field); anything structured is a genuine mistake worth naming.
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                value = str(value)
            else:
                raise queries.QueryError(
                    f"{tool.name}.{key} must be text, got "
                    f"{type(value).__name__}: {value!r}.")
        elif expected == "integer":
            value = _as_int(tool.name, key, value)
        elif expected == "boolean" and isinstance(value, str):
            value = value.strip().lower() in {"true", "yes", "1"}
        elif expected == "array" and not isinstance(value, list):
            value = [value]
        if expected == "array" and spec.get("items", {}).get("type") == "integer":
            value = [_as_int(tool.name, key, item) for item in value]
        if "enum" in spec and value not in spec["enum"]:
            raise queries.QueryError(
                f"{tool.name}.{key} must be one of: {', '.join(map(str, spec['enum']))}.")
        cleaned[key] = value
    return cleaned


def call_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    graph: KnowledgeGraph | None = None,
) -> dict[str, Any]:
    """Run a tool and return an MCP ``CallToolResult``.

    The result always carries a ``content`` list with one text block; on
    success it also carries ``structuredContent`` with the raw query result.
    """
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        available = ", ".join(sorted(TOOLS_BY_NAME))
        return _error(f"Unknown tool {name!r}. Available tools: {available}.")

    try:
        cleaned = _validate(tool, dict(arguments or {}))
        result = tool.handler(graph=graph, **cleaned)
        text = render(name, result)
    except queries.QueryError as exc:
        return _error(str(exc))
    except (TypeError, ValueError) as exc:
        return _error(f"{name} could not run: {exc}")
    except Exception as exc:  # pragma: no cover - unexpected, but must not kill the server
        return _error(f"{name} failed unexpectedly: {exc}\n"
                      + "".join(traceback.format_exception_only(type(exc), exc)))

    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": result,
        "isError": False,
    }


def _error(message: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    }
