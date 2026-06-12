"""
================================================================================
Module: demo.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
CONTEXT
-------
A standalone demonstration that answers 20+ of the specification's sample
questions WITHOUT needing an MCP client.  It calls the same KnowledgeGraph /
formatting code that the MCP tools use, so the output is exactly what an LLM
would receive through the server.

Run:  python demo.py
================================================================================
"""

from __future__ import annotations

import formatting
from knowledge_graph import KnowledgeGraph


def section(title: str, body: str) -> None:
    print("\n" + "=" * 78)
    print("Q: " + title)
    print("-" * 78)
    print(body)


def main() -> None:
    kg = KnowledgeGraph()

    section("Show me all Flamengo vs Fluminense matches (Fla-Flu derby)",
            formatting.format_head_to_head(kg.head_to_head("Flamengo", "Fluminense")))

    section("What matches did Palmeiras play in 2021?",
            formatting.format_matches(
                kg.find_matches(team="Palmeiras", season=2021, competition="Série A", limit=8),
                team="Palmeiras"))

    section("Find all Copa do Brasil finals",
            formatting.format_matches(
                kg.find_matches(competition="Copa do Brasil", limit=6)))

    section("What is Corinthians' home record in 2022?",
            formatting.format_team_record(
                kg.team_record("Corinthians", season=2022, competition="Série A", venue="home")))

    section("Which team scored the most goals in Série A 2019?",
            formatting.format_top_scorers(kg.top_scoring_teams("Série A", 2019, 5), "Série A", 2019))

    section("Compare Palmeiras and Santos head-to-head",
            formatting.format_head_to_head(kg.head_to_head("Palmeiras", "Santos")))

    section("Find the top Brazilian players in the dataset",
            formatting.format_players(kg.search_players(nationality="Brazil", limit=8)))

    section("Who are the highest-rated players at Santos?",
            formatting.format_players(kg.search_players(club="Santos", limit=5)))

    section("Show me Brazilian goalkeepers rated 80+",
            formatting.format_players(
                kg.search_players(nationality="Brazil", position="GK", min_overall=80, limit=5)))

    section("Who is Neymar?",
            formatting.format_player_detail(kg.get_player("Neymar")))

    section("Which clubs have the most Brazilian players?",
            formatting.format_players_by_club(kg.brazilian_players_by_club(limit=8)))

    section("Who won the 2019 Brasileirão?",
            formatting.format_standings(kg.standings("Série A", 2019), "Série A", 2019, top=6))

    section("Show the 2022 Brasileirão final standings",
            formatting.format_standings(kg.standings("Série A", 2022), "Série A", 2022, top=6))

    section("What's the average goals per match in the Brasileirão?",
            formatting.format_average_goals(kg.average_goals(competition="Série A")))

    section("Show me the biggest wins in the Copa Libertadores",
            formatting.format_biggest_wins(kg.biggest_wins(competition="Libertadores", limit=5)))

    section("When did Flamengo last play Corinthians, and what was the score?",
            formatting.format_matches(
                kg.find_matches(team="Flamengo", opponent="Corinthians", limit=1),
                team="Flamengo", opponent="Corinthians"))

    section("What competitions are in the dataset?",
            "\n".join(f"- {c}" for c in kg.list_competitions()))

    section("Which seasons of the Série A are available?",
            ", ".join(str(s) for s in kg.list_seasons("Série A")))

    section("Grêmio away record in 2018",
            formatting.format_team_record(
                kg.team_record("Grêmio", season=2018, competition="Série A", venue="away")))

    section("Biggest Brasileirão wins involving São Paulo",
            formatting.format_biggest_wins(
                kg.biggest_wins(competition="Série A", team="São Paulo", limit=5)))

    section("How many teams played in the 2020 Série A, and who were they?",
            ", ".join(kg.list_teams("Série A", 2020)))

    print("\n" + "=" * 78)
    print("Answered 21 sample questions across all five capability categories.")


if __name__ == "__main__":
    main()
