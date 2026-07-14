"""
================================================================================
Context
================================================================================
Module:   demo.py
Project:  Brazilian Soccer MCP Server
Purpose:  A tiny command-line demonstration / smoke test that answers a handful
          of the spec's sample questions without needing an MCP client.  Useful
          for eyeballing output and for verifying the data layer end-to-end.

Run:      python demo.py
Dependencies: server (tool functions), standard library only at runtime.
================================================================================
"""

from __future__ import annotations

import server


def main() -> None:
    server.get_graph()  # warm the cache once

    blocks = [
        ("Who won the 2019 Brasileirão?",
         server.tool_season_champion("brasileirao", 2019)),
        ("2019 Brasileirão — top of the table",
         server.tool_standings("brasileirao", 2019, limit=5)),
        ("Flamengo vs Fluminense (Fla-Flu derby)",
         server.tool_head_to_head("Flamengo", "Fluminense")),
        ("Corinthians home record (2022 Brasileirão)",
         server.tool_team_record("Corinthians", 2022, "brasileirao", "home")),
        ("Top-rated Brazilian players",
         server.tool_top_players(nationality="Brazil", limit=5)),
        ("Biggest victories in the dataset",
         server.tool_biggest_wins(limit=5)),
        ("Average goals per match (Brasileirão)",
         server.tool_average_goals("brasileirao")),
    ]

    for question, answer in blocks:
        print("=" * 70)
        print(f"Q: {question}")
        print("-" * 70)
        print(answer)
        print()


if __name__ == "__main__":
    main()
