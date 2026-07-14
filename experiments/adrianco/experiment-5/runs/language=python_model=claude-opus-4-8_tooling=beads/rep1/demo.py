"""
================================================================================
Module: demo.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Context
-------
A self-contained demonstration that exercises the MCP tools the way an LLM
client would (via ``MCPServer.call_tool``) to answer 20+ of the natural-language
sample questions from the specification. Useful as a smoke test and as a live
showcase of the server's capabilities without needing an MCP client.

Run:  python demo.py
================================================================================
"""

from __future__ import annotations

from mcp_server import MCPServer

# (natural-language question, tool name, arguments)
SAMPLES = [
    ("Show me all Flamengo vs Fluminense matches",
     "find_matches", {"team": "Flamengo", "opponent": "Fluminense", "limit": 5}),
    ("What matches did Palmeiras play in 2023?",
     "find_matches", {"team": "Palmeiras", "season": 2023, "limit": 5}),
    ("When did Flamengo last play Corinthians, and what was the score?",
     "find_matches", {"team": "Flamengo", "opponent": "Corinthians", "limit": 1}),
    ("Find all Copa do Brasil matches for Flamengo",
     "find_matches", {"team": "Flamengo", "competition": "Copa do Brasil", "limit": 5}),
    ("What is Corinthians' home record in 2022?",
     "team_record", {"team": "Corinthians", "season": 2022,
                     "competition": "Brasileirao", "venue": "home"}),
    ("Compare Palmeiras and Santos head-to-head",
     "head_to_head", {"team_a": "Palmeiras", "team_b": "Santos"}),
    ("Compare Flamengo and Fluminense (full comparison)",
     "compare_teams", {"team_a": "Flamengo", "team_b": "Fluminense", "season": 2023}),
    ("Who won the 2019 Brasileirão?",
     "standings", {"competition": "Brasileirao", "season": 2019}),
    ("Show the 2022 Brasileirão final standings",
     "standings", {"competition": "Brasileirao", "season": 2022}),
    ("Show the 2018 Copa Libertadores results",
     "find_matches", {"competition": "Libertadores", "season": 2018, "limit": 5}),
    ("What's the average goals per match in the 2019 Brasileirão?",
     "average_goals", {"competition": "Brasileirao", "season": 2019}),
    ("What are the overall statistics across all data?",
     "average_goals", {}),
    ("Show me the biggest wins in the 2019 Brasileirão",
     "biggest_wins", {"competition": "Brasileirao", "season": 2019, "limit": 5}),
    ("Which team has the best home record in 2019?",
     "best_record", {"venue": "home", "competition": "Brasileirao",
                     "season": 2019, "limit": 5}),
    ("Which team has the best away record in 2019?",
     "best_record", {"venue": "away", "competition": "Brasileirao",
                     "season": 2019, "limit": 5}),
    ("Who is Neymar?",
     "find_players", {"name": "Neymar"}),
    ("Who are the top Brazilian players?",
     "find_players", {"nationality": "Brazil", "limit": 10}),
    ("Show me Brazilian goalkeepers",
     "find_players", {"nationality": "Brazil", "position": "GK", "limit": 5}),
    ("Which players play for Grêmio?",
     "find_players", {"club": "Gremio", "limit": 5}),
    ("Find the highest-rated players in the world",
     "find_players", {"min_overall": 90, "limit": 5}),
    ("What competitions are available?",
     "list_competitions", {}),
    ("What seasons of the Brasileirão are covered?",
     "list_seasons", {"competition": "Brasileirao"}),
]


def main():
    server = MCPServer()
    print(f"Loaded {len(server.graph.ds.matches):,} matches and "
          f"{len(server.graph.ds.players):,} players.\n")
    for i, (question, tool, args) in enumerate(SAMPLES, 1):
        print("=" * 78)
        print(f"Q{i}. {question}")
        print(f"    -> tool {tool}({args})")
        print("-" * 78)
        print(server.call_tool(tool, args))
        print()


if __name__ == "__main__":
    main()
