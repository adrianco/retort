"""
================================================================================
Module: demo
--------------------------------------------------------------------------------
Context:
    A standalone, dependency-free showcase that answers the sample questions
    from TASK.md directly against the KnowledgeGraph — no MCP client required.
    Handy for a quick manual smoke-test and for demonstrating that the server
    can answer 20+ natural-language-style questions.

Responsibility:
    Drive the KnowledgeGraph + formatting layer through a representative set of
    queries across all five capability categories and print the results.

Run:
    python demo.py
================================================================================
"""

from __future__ import annotations

from brazilian_soccer_mcp import KnowledgeGraph
from brazilian_soccer_mcp import formatting as fmt


def section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main() -> None:
    g = KnowledgeGraph().load()
    print(f"Loaded {len(g.matches):,} matches and {len(g.players):,} players "
          f"across {len(g.list_competitions())} competitions.")

    section("1. MATCH QUERIES")
    print("Q: Show me all Flamengo vs Fluminense matches (most recent 5)")
    print(fmt.format_matches(
        g.find_matches(team="Flamengo", opponent="Fluminense", limit=5),
        header="Flamengo vs Fluminense (Fla-Flu derby):"))
    print("\nQ: What matches did Palmeiras play in the 2020 Libertadores?")
    print(fmt.format_matches(
        g.find_matches(team="Palmeiras", competition="Libertadores", season=2020, limit=5),
        header="Palmeiras — Libertadores 2020:"))
    print("\nQ: When did Flamengo last play Corinthians, and what was the score?")
    last = g.find_matches(team="Flamengo", opponent="Corinthians", limit=1)
    print(last[0].summary() if last else "No match found.")

    section("2. TEAM QUERIES")
    print("Q: What is Corinthians' home record in the 2022 Brasileirão?")
    print(fmt.format_team_record(
        g.team_record("Corinthians", season=2022, competition="Brasileirão", venue="home")))
    print("\nQ: Compare Palmeiras and Santos head-to-head")
    print(fmt.format_head_to_head(g.head_to_head("Palmeiras", "Santos"), limit=3))
    print("\nQ: What competitions has Grêmio played in?")
    print("Grêmio:", ", ".join(g.team_competitions("Grêmio")))

    section("3. PLAYER QUERIES")
    print("Q: Who are the top Brazilian players?")
    print(fmt.format_players(
        g.search_players(nationality="Brazil", limit=5),
        header="Top-rated Brazilian players:"))
    print("\nQ: Who is Neymar?")
    p = g.get_player("Neymar")
    print(p.summary() if p else "Not found.")
    print("\nQ: Brazilian players grouped by club")
    print(fmt.format_club_summary(g.players_by_club_summary("Brazil"), "Brazil", limit=5))

    section("4. COMPETITION QUERIES")
    print("Q: Who won the 2019 Brasileirão?")
    c = g.champion("Brasileirão", 2019)
    print(f"{c['team']} — {c['points']} pts "
          f"({c['wins']}W {c['draws']}D {c['losses']}L)")
    print("\nQ: Show the 2019 Brasileirão final standings (top 6)")
    print(fmt.format_standings(g.standings("Brasileirão", 2019),
                               "Brasileirão Série A", 2019, limit=6))

    section("5. STATISTICAL ANALYSIS")
    print("Q: What's the average goals per match in the Brasileirão?")
    print(fmt.format_stats(g.average_goals("Brasileirão")))
    print("\nQ: Show me the biggest wins in the dataset")
    print(fmt.format_matches(g.biggest_wins(limit=5), header="Biggest victories:"))
    print("\nQ: Which team had the best away record in the 2019 Brasileirão?")
    print(fmt.format_best_record(
        g.best_record(venue="away", competition="Brasileirão", season=2019, min_matches=10, limit=5),
        "Best away record — Brasileirão 2019:"))


if __name__ == "__main__":
    main()
