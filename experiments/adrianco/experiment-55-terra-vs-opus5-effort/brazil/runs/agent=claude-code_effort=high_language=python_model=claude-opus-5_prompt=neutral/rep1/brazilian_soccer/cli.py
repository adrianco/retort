"""Command line client -- the same tools, without an MCP host.

Context
-------
Useful for exploring the data, for demos, and as a fast way to check that a
tool behaves before wiring the server into an LLM client::

    python -m brazilian_soccer.cli tools
    python -m brazilian_soccer.cli call standings season=2019
    python -m brazilian_soccer.cli call head_to_head team_a=Flamengo team_b=Fluminense
    python -m brazilian_soccer.cli demo

``demo`` runs the twenty-plus sample questions from the specification and
prints the answers, which is the quickest way to see the whole surface area.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from .graph import load_graph
from .tools import TOOLS, TOOLS_BY_NAME, call_tool

__all__ = ["main", "DEMO_QUESTIONS"]


#: (question, tool, arguments) triples covering every required capability.
DEMO_QUESTIONS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    # --- match queries ---------------------------------------------------
    ("Show me all Flamengo vs Fluminense matches",
     "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense", "limit": 5}),
    ("What matches did Palmeiras play in 2023?",
     "find_matches", {"team": "Palmeiras", "season": 2023, "limit": 5}),
    ("Find all Copa do Brasil finals",
     "find_matches", {"competition": "copa-do-brasil", "stage": "Final", "limit": 10}),
    ("When did Flamengo last play Corinthians, and what was the score?",
     "head_to_head", {"team_a": "Flamengo", "team_b": "Corinthians", "limit": 1}),
    ("Which Libertadores finals are in the data?",
     "find_matches", {"competition": "libertadores", "stage": "Final", "limit": 8}),
    # --- team queries ----------------------------------------------------
    ("What is Corinthians' home record in 2022?",
     "team_stats", {"team": "Corinthians", "season": 2022,
                    "competition": "brasileirao", "venue": "home"}),
    ("Which team scored the most goals in Serie A 2023?",
     "team_rankings", {"metric": "goals_for", "competition": "serie-a",
                       "season": 2023, "limit": 5}),
    ("Compare Palmeiras and Santos head-to-head",
     "head_to_head", {"team_a": "Palmeiras", "team_b": "Santos", "limit": 5}),
    ("What competitions has Palmeiras played in?",
     "team_profile", {"team": "Palmeiras"}),
    ("Which team has the best home record in the Brasileirão?",
     "team_rankings", {"metric": "win_rate", "competition": "serie-a",
                       "venue": "home", "min_matches": 100, "limit": 5}),
    ("Which team has the best away record?",
     "team_rankings", {"metric": "points_per_game", "competition": "serie-a",
                       "venue": "away", "min_matches": 100, "limit": 5}),
    # --- player queries --------------------------------------------------
    ("Find all Brazilian players in the dataset",
     "search_players", {"nationality": "Brazil", "limit": 5}),
    ("Who are the highest-rated players at Grêmio?",
     "club_squad", {"club": "Grêmio", "limit": 5}),
    ("Show me all forwards from Santos",
     "search_players", {"club": "Santos", "position": "FWD", "limit": 5}),
    ("Who is Gabriel Jesus?", "player_profile", {"name": "Gabriel Jesus"}),
    ("Who are the top Brazilian players and where do they play?",
     "brazilian_players_by_club", {"limit": 6}),
    ("Which players play for Flamengo?", "club_squad", {"club": "Flamengo"}),
    # --- competition queries ---------------------------------------------
    ("Who won the 2019 Brasileirão?", "standings", {"season": 2019}),
    ("Which teams were relegated in 2020?", "standings", {"season": 2020}),
    ("Show the 2018 Copa Libertadores knockout stages",
     "find_matches", {"competition": "libertadores", "season": 2018,
                      "stage": "final", "limit": 5}),
    # --- statistical analysis --------------------------------------------
    ("What's the average goals per match in the Brasileirão?",
     "competition_stats", {"competition": "brasileirao"}),
    ("Show me the biggest wins in the dataset",
     "biggest_wins", {"limit": 5}),
    ("Compare the 2018 and 2019 seasons",
     "compare_seasons", {"seasons": [2018, 2019], "competition": "serie-a"}),
    ("Show me all derbies in 2023", "find_derbies", {"season": 2023, "limit": 8}),
    ("How is 'Atletico-PR' normalised?", "resolve_team", {"name": "Atletico-PR"}),
    ("What data is loaded?", "dataset_summary", {}),
)


def _parse_value(raw: str) -> Any:
    """Turn ``key=value`` text into a Python value (JSON first, then string)."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse_args(pairs: list[str]) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"Arguments must be key=value, got {pair!r}")
        key, _, value = pair.partition("=")
        arguments[key] = _parse_value(value)
    return arguments


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brazilian-soccer",
        description="Query the Brazilian football knowledge graph from the shell.")
    parser.add_argument("--data-dir", default=None, help="Kaggle CSV directory.")
    parser.add_argument("--json", action="store_true",
                        help="Print the structured result instead of prose.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("tools", help="List the available tools.")
    subparsers.add_parser("summary", help="Describe the loaded datasets.")
    subparsers.add_parser("demo", help="Answer the specification's sample questions.")

    call = subparsers.add_parser("call", help="Call one tool.")
    call.add_argument("tool", help="Tool name.")
    call.add_argument("arguments", nargs="*", help="key=value pairs.")

    args = parser.parse_args(argv)
    graph = load_graph(args.data_dir)

    if args.command == "tools":
        for tool in TOOLS:
            print(f"{tool.name}\n    {tool.description}\n")
        return 0

    if args.command == "summary":
        result = call_tool("dataset_summary", {}, graph=graph)
        print(_render(result, args.json))
        return 0

    if args.command == "demo":
        failures = 0
        for index, (question, tool, arguments) in enumerate(DEMO_QUESTIONS, start=1):
            started = time.perf_counter()
            result = call_tool(tool, arguments, graph=graph)
            elapsed = time.perf_counter() - started
            marker = "!!" if result.get("isError") else "  "
            failures += bool(result.get("isError"))
            print("=" * 78)
            print(f"{marker} Q{index}. {question}")
            print(f"   [{tool}({', '.join(f'{k}={v!r}' for k, v in arguments.items())})"
                  f" in {elapsed * 1000:.0f} ms]")
            print("-" * 78)
            print(result["content"][0]["text"])
            print()
        print("=" * 78)
        print(f"{len(DEMO_QUESTIONS)} questions answered, {failures} error(s).")
        return 1 if failures else 0

    if args.command == "call":
        if args.tool not in TOOLS_BY_NAME:
            print(f"Unknown tool {args.tool!r}. Available: "
                  + ", ".join(sorted(TOOLS_BY_NAME)), file=sys.stderr)
            return 2
        result = call_tool(args.tool, _parse_args(args.arguments), graph=graph)
        print(_render(result, args.json))
        return 1 if result.get("isError") else 0

    return 0  # pragma: no cover


def _render(result: dict[str, Any], as_json: bool) -> str:
    if as_json:
        payload = result.get("structuredContent", result)
        return json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    return result["content"][0]["text"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
