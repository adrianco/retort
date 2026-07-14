"""
================================================================================
Script: demo.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
  A standalone demo that exercises the query engine directly (no MCP client
  required), printing answers to a spread of the spec's sample questions. Handy
  for a quick smoke test and to see the data layer in action.

USAGE
  python demo.py
================================================================================
"""

import json
import time

from brazilian_soccer_mcp import queries
from brazilian_soccer_mcp.data_loader import get_data


def show(title, obj):
    print(f"\n=== {title} ===")
    print(json.dumps(obj, ensure_ascii=False, indent=2)[:1400])


def main():
    t0 = time.time()
    get_data()
    print(f"Data loaded in {time.time() - t0:.2f}s")

    show("Who won the 2019 Brasileirão?",
         {k: queries.standings(2019)[k] for k in ("champion", "season", "teams")})

    show("Flamengo vs Fluminense head-to-head", queries.head_to_head(
        "Flamengo", "Fluminense", limit=2))

    show("Corinthians home record (2022 Brasileirão)", queries.team_record(
        "Corinthians", competition="Brasileirão", season=2022, venue="home"))

    show("Top Brazilian players", queries.find_players(
        nationality="Brazil", limit=5))

    show("Average goals per match (Brasileirão)", queries.competition_stats(
        competition="Brasileirão Série A"))

    show("Biggest wins in the Libertadores", queries.biggest_wins(
        competition="Libertadores", limit=5))

    show("Best home records in 2019", queries.best_records(
        venue="home", season=2019, competition="Brasileirão", limit=5))


if __name__ == "__main__":
    main()
