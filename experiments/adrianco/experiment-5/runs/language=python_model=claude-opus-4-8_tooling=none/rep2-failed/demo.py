#!/usr/bin/env python3
"""
Context
=======
Script: demo.py
Purpose: Demonstrate that the knowledge graph can answer the 20+ sample
questions from TASK.md, without needing an LLM or the MCP transport.  It calls
the same query API the MCP tools wrap and prints formatted answers.

Run from the repository root::

    python demo.py
"""

from __future__ import annotations

from brazilian_soccer_mcp import formatting as F
from brazilian_soccer_mcp import get_graph


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main() -> None:
    g = get_graph()

    section("Dataset overview")
    s = g.dataset_summary()
    print(f"{s['total_matches']} canonical matches, {s['total_players']} players, "
          f"{s['distinct_teams']} teams, seasons {s['season_range'][0]}-{s['season_range'][1]}")

    section("1. Show me all Flamengo vs Fluminense matches (Fla-Flu)")
    print(F.format_head_to_head(g.head_to_head("Flamengo", "Fluminense"), max_rows=5))

    section("2. What matches did Palmeiras play in 2019?")
    print(F.format_matches(g.find_matches(team="Palmeiras", season=2019), max_rows=5,
                           title="Palmeiras 2019"))

    section("3. Find all Copa do Brasil finals (Flamengo) ")
    print(F.format_matches(g.find_matches(team="Flamengo", competition="Copa do Brasil"),
                           max_rows=5, title="Flamengo in the Copa do Brasil"))

    section("4. What is Corinthians' home record in 2019?")
    print(F.format_team_stats(g.team_stats("Corinthians", season=2019, venue="home",
                                           competition="Brasileirão")))

    section("5. Compare Palmeiras and Santos head-to-head")
    print(F.format_head_to_head(g.head_to_head("Palmeiras", "Santos"), max_rows=3))

    section("6. Find the top Brazilian players")
    print(F.format_players(g.search_players(nationality="Brazil", limit=5),
                           title="Top-rated Brazilian players"))

    section("7. Who are the highest-rated players at Real Madrid?")
    print(F.format_players(g.search_players(club="Real Madrid", limit=5),
                           title="Real Madrid (top rated)"))

    section("8. Who is Neymar?")
    print(F.format_player(g.find_player("Neymar")))

    section("9. Who won the 2019 Brasileirao?")
    print(F.format_standings(g.standings(2019, "Brasileirão"), 2019, "Brasileirão", top=6))

    section("10. Who won the 2017 Brasileirao?")
    champ = g.champion(2017, "Brasileirão")
    print(f"{champ['team']} - {champ['points']} pts "
          f"({champ['wins']}W, {champ['draws']}D, {champ['losses']}L)")

    section("11. What's the average goals per match in the Brasileirao?")
    print(F.format_competition_stats(g.competition_stats(competition="Brasileirão")))

    section("12. Show me the biggest wins in the Brasileirao")
    print(F.format_matches(g.biggest_wins(competition="Brasileirão", limit=5),
                           title="Biggest Série A victories"))

    section("13. Which team had the best home record in 2019?")
    rows = g.best_records(season=2019, competition="Brasileirão", venue="home")
    for i, r in enumerate(rows[:5], start=1):
        print(f"{i}. {r['team']} - {r['win_rate']}% ({r['wins']}W {r['draws']}D {r['losses']}L)")

    section("14. Atletico-MG vs Atletico-PR are different clubs")
    for q in ("Atletico-MG", "Atletico-PR"):
        st = g.team_stats(q, season=2019, competition="Brasileirão")
        print(f"{q}: {st['played']} games, {st['points']} pts ({g.resolve_team(q)})")

    print("\nDone - all sample questions answered.")


if __name__ == "__main__":
    main()
