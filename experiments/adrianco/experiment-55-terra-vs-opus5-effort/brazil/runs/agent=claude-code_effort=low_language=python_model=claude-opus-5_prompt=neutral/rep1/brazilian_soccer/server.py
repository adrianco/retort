"""
Context
=======
Module: brazilian_soccer.server

The MCP surface.  Defines 16 tools over the knowledge graph and serves them on
stdio so any MCP client (Claude Desktop, Claude Code, the MCP inspector) can
drive them.

Design notes
------------
* Tool handlers are ordinary functions of (graph, arguments) that return
  (human_text, structured_data).  They live in the TOOLS registry and are
  dispatched by `dispatch()`, which is also what the test-suite calls -- so the
  tests exercise exactly the code path the MCP client uses, without needing a
  transport.
* Every tool answers with both a formatted text block (ready to quote) and the
  JSON behind it, so the LLM can either read the summary or do its own maths.
* The graph is loaded lazily on the first tool call and cached in a module-level
  singleton: server start-up stays instant, and the ~1s CSV parse is paid once.
* Errors (unknown team, unknown competition, bad date) come back as readable
  text with suggestions rather than tracebacks -- an LLM can recover from that.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from . import formatters as fmt
from .graph import KnowledgeGraph, TeamNotFound, load_default_graph

_GRAPH: KnowledgeGraph | None = None


def get_graph() -> KnowledgeGraph:
    """Return the process-wide graph, loading the CSVs on first use."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = load_default_graph()
    return _GRAPH


def set_graph(graph: KnowledgeGraph | None) -> None:
    """Inject a graph (used by tests to avoid reloading the CSVs per test)."""
    global _GRAPH
    _GRAPH = graph


# --------------------------------------------------------------------- schemas

_TEAM = {"type": "string", "description": "Club name; any spelling, e.g. 'Flamengo', 'Flamengo-RJ'"}
_COMP = {
    "type": "string",
    "description": "Competition: Brasileirao / Serie A / Serie B / Serie C / Copa do Brasil / Libertadores",
}
_SEASON = {"type": "integer", "description": "Season year, e.g. 2019"}


def _schema(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


# -------------------------------------------------------------------- handlers

def _search_matches(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    limit = args.get("limit", 20)
    all_hits = graph.find_matches(
        team=args.get("team"),
        opponent=args.get("opponent"),
        venue=args.get("venue", "any"),
        competition=args.get("competition"),
        season=args.get("season"),
        season_from=args.get("season_from"),
        season_to=args.get("season_to"),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        stage=args.get("stage"),
        limit=None,
    )
    shown = [m.to_dict() for m in all_hits[:limit]]
    header_bits = [b for b in [args.get("team"), args.get("opponent")] if b]
    header = " vs ".join(header_bits) if header_bits else "Matches"
    text = fmt.format_match_list(shown, header=f"{header} ({len(all_hits)} found):", total=len(all_hits))
    return text, {"total": len(all_hits), "returned": len(shown), "matches": shown}


def _head_to_head(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.head_to_head(
        args["team_a"], args["team_b"],
        competition=args.get("competition"),
        season=args.get("season"),
        limit=args.get("limit", 20),
    )
    return fmt.format_head_to_head(data), data


def _team_stats(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.team_stats(
        args["team"],
        competition=args.get("competition"),
        season=args.get("season"),
        venue=args.get("venue", "any"),
    )
    return fmt.format_team_stats(data), data


def _team_profile(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.team_profile(args["team"])
    text = "\n".join([
        f"{data['team']}: {data['total_matches']} matches in the datasets",
        f"- Competitions: {', '.join(data['competitions'])}",
        f"- Seasons: {min(data['seasons'])}-{max(data['seasons'])}" if data["seasons"] else "",
        fmt.format_record(data["record"], title="Overall record"),
        f"- FIFA squad entries: {data['squad_size_in_fifa_data']}",
    ])
    return text, data


def _standings(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.standings(args["competition"], args["season"], limit=args.get("limit"))
    return fmt.format_standings(data), data


def _competition_summary(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.competition_summary(args["competition"], args.get("season"))
    return fmt.format_statistics(data), data


def _bracket(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.bracket(args["competition"], args["season"])
    lines = [f"{data['competition']} {data['season']}:"]
    for stage in data["stages"]:
        lines.append(f"\n{stage['stage'].title()} ({len(stage['matches'])} matches):")
        lines += [f"- {fmt.format_match(m, with_competition=False)}" for m in stage["matches"][:20]]
    return "\n".join(lines), data


def _statistics(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.statistics(
        competition=args.get("competition"),
        season=args.get("season"),
        season_from=args.get("season_from"),
        season_to=args.get("season_to"),
    )
    return fmt.format_statistics(data), data


def _biggest_wins(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.biggest_wins(
        competition=args.get("competition"),
        season=args.get("season"),
        team=args.get("team"),
        limit=args.get("limit", 10),
    )
    return fmt.format_biggest_wins(data), data


def _leaderboard(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    metric = args.get("metric", "wins")
    data = graph.team_leaderboard(
        metric=metric,
        competition=args.get("competition"),
        season=args.get("season"),
        venue=args.get("venue", "any"),
        min_matches=args.get("min_matches", 1),
        limit=args.get("limit", 10),
    )
    return fmt.format_leaderboard(data, metric=metric), data


def _search_players(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.search_players(
        name=args.get("name"),
        nationality=args.get("nationality"),
        club=args.get("club"),
        position=args.get("position"),
        min_overall=args.get("min_overall"),
        max_overall=args.get("max_overall"),
        min_age=args.get("min_age"),
        max_age=args.get("max_age"),
        sort_by=args.get("sort_by", "overall"),
        limit=args.get("limit", 20),
    )
    return fmt.format_players(data, header="Players found"), data


def _player_profile(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.player_profile(args["name"])
    if not data["found"]:
        text = f"No player matching {args['name']!r} in the FIFA dataset."
        if data.get("suggestions"):
            text += "\nSimilar names: " + ", ".join(
                f"{p['name']} ({p['club'] or 'free agent'}, {p['overall']})"
                for p in data["suggestions"]
            )
        return text, data
    player = data["player"]
    text = "\n".join([
        f"{player['name']} - {player['nationality']}, age {player['age']}",
        f"- Club: {player['club'] or 'free agent'} | Position: {player['position']}"
        f" | Shirt: {player['jersey_number']}",
        f"- Overall: {player['overall']} (potential {player['potential']})",
        f"- Physical: {player['height']}, {player['weight']}, {player['preferred_foot']}-footed",
        f"- Value: {player['value']} | Wage: {player['wage']}",
    ])
    return text, data


def _brazilian_club_squads(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.players_by_brazilian_club(
        min_players=args.get("min_players", 1), limit=args.get("limit", 30)
    )
    lines = ["Brazilian clubs with players in the FIFA dataset:"]
    for row in data:
        lines.append(
            f"- {row['club']}: {row['players']} players "
            f"(avg rating: {row['average_overall']}, best: {row['best_player']} {row['best_overall']})"
        )
    return "\n".join(lines), data


def _list_teams(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.list_teams(query=args.get("query"), limit=args.get("limit", 50))
    lines = [f"- {r['team']} ({r['matches']} matches)" for r in data]
    return "\n".join(["Teams:"] + lines), data


def _find_derbies(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.find_derbies(
        season=args.get("season"),
        competition=args.get("competition"),
        limit=args.get("limit", 50),
    )
    lines = [f"- {fmt.format_match(m)} [{m['derby']}]" for m in data]
    header = f"Derbies ({len(data)} found):"
    return "\n".join([header] + lines) if lines else "No derbies found.", data


def _dataset_overview(graph: KnowledgeGraph, args: dict) -> tuple[str, Any]:
    data = graph.dataset_overview()
    lines = [
        f"Matches after de-duplication: {data['matches_after_deduplication']}",
        f"Seasons covered: {data['seasons'][0]}-{data['seasons'][1]}",
        f"Distinct teams: {data['distinct_teams']}",
        f"Players: {data['players']} ({data['brazilian_players']} Brazilian)",
        "Per competition:",
    ]
    for comp, info in data["competitions"].items():
        lines.append(f"- {comp}: {info['matches']} matches ({info['seasons'][0]}-{info['seasons'][1]})")
    lines.append("Rows read per file:")
    for filename, count in data["rows_read_per_file"].items():
        lines.append(f"- {filename}: {count}")
    return "\n".join(lines), data


Handler = Callable[[KnowledgeGraph, dict], "tuple[str, Any]"]

TOOLS: dict[str, dict] = {
    "search_matches": {
        "handler": _search_matches,
        "description": (
            "Find matches by team, opponent, competition, season, date range or knockout "
            "stage. Use for questions like 'what matches did Palmeiras play in 2023' or "
            "'find all Copa do Brasil finals'."
        ),
        "schema": _schema({
            "team": _TEAM,
            "opponent": {"type": "string", "description": "Second club, to restrict to meetings between the two"},
            "venue": {"type": "string", "enum": ["home", "away", "any"], "description": "Venue relative to 'team'"},
            "competition": _COMP,
            "season": _SEASON,
            "season_from": {"type": "integer"},
            "season_to": {"type": "integer"},
            "date_from": {"type": "string", "description": "YYYY-MM-DD or DD/MM/YYYY"},
            "date_to": {"type": "string", "description": "YYYY-MM-DD or DD/MM/YYYY"},
            "stage": {"type": "string", "description": "Knockout stage or round, e.g. 'final', 'semifinals'"},
            "limit": {"type": "integer", "default": 20},
        }),
    },
    "head_to_head": {
        "handler": _head_to_head,
        "description": "Complete head-to-head record between two clubs: wins, draws, goals and the match list.",
        "schema": _schema({
            "team_a": _TEAM, "team_b": _TEAM,
            "competition": _COMP, "season": _SEASON,
            "limit": {"type": "integer", "default": 20},
        }, ["team_a", "team_b"]),
    },
    "team_stats": {
        "handler": _team_stats,
        "description": (
            "Win/draw/loss record, goals for and against, split home vs away, optionally "
            "filtered to one competition and season. Answers 'what is Corinthians' home record in 2022'."
        ),
        "schema": _schema({
            "team": _TEAM, "competition": _COMP, "season": _SEASON,
            "venue": {"type": "string", "enum": ["home", "away", "any"]},
        }, ["team"]),
    },
    "team_profile": {
        "handler": _team_profile,
        "description": "Everything known about a club: competitions, seasons, overall record, main rivals and FIFA squad.",
        "schema": _schema({"team": _TEAM}, ["team"]),
    },
    "standings": {
        "handler": _standings,
        "description": (
            "League table for a competition and season, computed from match results "
            "(3 pts win / 1 pt draw). Answers 'who won the 2019 Brasileirao' and "
            "'which teams were relegated in 2020'."
        ),
        "schema": _schema({
            "competition": _COMP, "season": _SEASON,
            "limit": {"type": "integer", "description": "Return only the top N rows"},
        }, ["competition", "season"]),
    },
    "competition_summary": {
        "handler": _competition_summary,
        "description": "Overview of a competition (optionally one season): goals, home advantage, stages, top-scoring teams.",
        "schema": _schema({"competition": _COMP, "season": _SEASON}, ["competition"]),
    },
    "competition_bracket": {
        "handler": _bracket,
        "description": "Knockout bracket by stage for Copa Libertadores or Copa do Brasil in a given season.",
        "schema": _schema({"competition": _COMP, "season": _SEASON}, ["competition", "season"]),
    },
    "statistics": {
        "handler": _statistics,
        "description": (
            "Aggregate statistics over a slice of the match data: goals per match, home/away "
            "win rates, draw rate. Answers 'what is the average goals per match in the Brasileirao'."
        ),
        "schema": _schema({
            "competition": _COMP, "season": _SEASON,
            "season_from": {"type": "integer"}, "season_to": {"type": "integer"},
        }),
    },
    "biggest_wins": {
        "handler": _biggest_wins,
        "description": "Matches with the largest winning margin, optionally filtered by competition, season or team.",
        "schema": _schema({
            "competition": _COMP, "season": _SEASON, "team": _TEAM,
            "limit": {"type": "integer", "default": 10},
        }),
    },
    "team_leaderboard": {
        "handler": _leaderboard,
        "description": (
            "Rank all clubs by a metric (wins, win_rate, points, goals_for, goals_against, "
            "goal_difference, matches). Use venue='away' for 'which team has the best away record'."
        ),
        "schema": _schema({
            "metric": {
                "type": "string",
                "enum": ["wins", "win_rate", "points", "goals_for", "goals_against",
                         "goal_difference", "matches", "draws", "losses"],
                "default": "wins",
            },
            "competition": _COMP, "season": _SEASON,
            "venue": {"type": "string", "enum": ["home", "away", "any"]},
            "min_matches": {"type": "integer", "default": 1},
            "limit": {"type": "integer", "default": 10},
        }),
    },
    "search_players": {
        "handler": _search_players,
        "description": (
            "Search the FIFA player database by name, nationality, club, position, rating or age. "
            "Answers 'find all Brazilian players', 'highest-rated players at Flamengo', "
            "'all forwards from Sao Paulo FC'."
        ),
        "schema": _schema({
            "name": {"type": "string", "description": "Full or partial player name"},
            "nationality": {"type": "string", "description": "Country, e.g. 'Brazil'"},
            "club": {"type": "string", "description": "Club name, any spelling"},
            "position": {"type": "string", "description": "FIFA position code, e.g. ST, LW, GK, CB"},
            "min_overall": {"type": "integer"},
            "max_overall": {"type": "integer"},
            "min_age": {"type": "integer"},
            "max_age": {"type": "integer"},
            "sort_by": {"type": "string", "enum": ["overall", "potential", "age", "name"]},
            "limit": {"type": "integer", "default": 20},
        }),
    },
    "player_profile": {
        "handler": _player_profile,
        "description": "Full profile for one player by name, including whether their club appears in the match data.",
        "schema": _schema({"name": {"type": "string"}}, ["name"]),
    },
    "brazilian_club_squads": {
        "handler": _brazilian_club_squads,
        "description": "FIFA squad size and average rating for each club that also appears in the Brazilian match data.",
        "schema": _schema({
            "min_players": {"type": "integer", "default": 1},
            "limit": {"type": "integer", "default": 30},
        }),
    },
    "list_teams": {
        "handler": _list_teams,
        "description": "List clubs present in the match data, optionally filtered by a name fragment. Useful to resolve ambiguous names.",
        "schema": _schema({
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        }),
    },
    "find_derbies": {
        "handler": _find_derbies,
        "description": "Find matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, ...), optionally in one season.",
        "schema": _schema({
            "season": _SEASON, "competition": _COMP,
            "limit": {"type": "integer", "default": 50},
        }),
    },
    "dataset_overview": {
        "handler": _dataset_overview,
        "description": "What data is loaded: rows per file, competitions, season coverage, team and player counts.",
        "schema": _schema({}),
    },
}


def dispatch(name: str, arguments: dict | None = None, *, graph: KnowledgeGraph | None = None) -> dict:
    """Run one tool and return {'text': ..., 'data': ..., 'isError': bool}.

    This is the single entry point shared by the MCP transport and the tests.
    """
    arguments = dict(arguments or {})
    tool = TOOLS.get(name)
    if tool is None:
        return {
            "text": f"Unknown tool {name!r}. Available: {', '.join(sorted(TOOLS))}",
            "data": None,
            "isError": True,
        }
    active = graph if graph is not None else get_graph()
    try:
        text, data = tool["handler"](active, arguments)
    except TeamNotFound as exc:
        return {"text": str(exc), "data": None, "isError": True}
    except (ValueError, KeyError, LookupError) as exc:
        return {"text": f"{type(exc).__name__}: {exc}", "data": None, "isError": True}
    return {"text": text, "data": data, "isError": False}


# ------------------------------------------------------------------ MCP server

def tool_definitions():
    """The tool list as mcp Tool objects (also used by the discovery test)."""
    from mcp.types import Tool

    return [
        Tool(name=name, description=spec["description"], inputSchema=spec["schema"])
        for name, spec in TOOLS.items()
    ]


def render_result(result: dict) -> str:
    """The text an MCP client sees: the readable answer plus the JSON behind it."""
    payload = result["text"]
    if result["data"] is not None:
        payload += "\n\n---\nStructured data:\n" + json.dumps(
            result["data"], ensure_ascii=False, indent=2, default=str
        )
    return payload


def build_server():
    """Create the MCP Server with all tools registered (mcp >= 2.0 API)."""
    from mcp.server import Server
    from mcp.types import CallToolResult, ListToolsResult, TextContent

    async def on_list_tools(_context, _params=None) -> "ListToolsResult":
        return ListToolsResult(tools=tool_definitions())

    async def on_call_tool(_context, params) -> "CallToolResult":
        result = dispatch(params.name, params.arguments)
        return CallToolResult(
            content=[TextContent(type="text", text=render_result(result))],
            is_error=result["isError"],
        )

    return Server(
        "brazilian-soccer",
        version=__import__("brazilian_soccer").__version__,
        instructions=(
            "Knowledge graph over Brazilian soccer datasets: Brasileirão Série A/B/C, "
            "Copa do Brasil and Copa Libertadores matches (2003-2023) plus the FIFA "
            "player database. Call list_teams to resolve an ambiguous club name and "
            "dataset_overview to see what is covered."
        ),
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )


def main() -> None:
    """stdio entry point: `python -m brazilian_soccer.server`."""
    import asyncio

    async def _run() -> None:
        from mcp.server.stdio import stdio_server

        get_graph()  # pay the CSV parse before accepting requests
        server = build_server()
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
