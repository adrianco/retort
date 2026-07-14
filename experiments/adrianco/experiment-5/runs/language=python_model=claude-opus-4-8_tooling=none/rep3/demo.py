#!/usr/bin/env python3
# =============================================================================
# Context
# -----------------------------------------------------------------------------
# Project : Brazilian Soccer MCP Server
# Module  : demo (standalone script)
# Purpose : Demonstrate the server's query capabilities without an MCP client by
#           calling the same tool functions the server exposes and printing the
#           answers to >20 of the spec's sample questions. Handy for manual
#           verification and as living documentation of what the server can do.
# Usage   : python demo.py
# =============================================================================

from soccer_mcp import server


def section(question: str, answer: str) -> None:
    print(f"\nQ: {question}\n{'-' * 60}\n{answer}")


def main() -> None:
    print("Brazilian Soccer MCP Server - sample questions\n" + "=" * 60)
    section("What competitions and data are available?",
            server.list_competitions())
    section("Show me all Flamengo vs Fluminense matches",
            server.find_matches(team="Flamengo", opponent="Fluminense", limit=8))
    section("Head-to-head: Palmeiras vs Santos",
            server.head_to_head("Palmeiras", "Santos"))
    section("What matches did Palmeiras play in 2019?",
            server.find_matches(team="Palmeiras", season=2019, limit=6))
    section("Corinthians' home record in 2019 Brasileirão",
            server.team_stats("Corinthians", season=2019,
                              competition="Brasileirão", venue="home"))
    section("Who won the 2019 Brasileirão?",
            server.league_champion("Brasileirão", 2019))
    section("2019 Brasileirão final standings (top of table)",
            server.standings("Brasileirão", 2019))
    section("Which team scored the most goals in 2019 Brasileirão?",
            server.top_scoring_teams(competition="Brasileirão", season=2019, limit=5))
    section("Who are the top Brazilian players?",
            server.find_players(nationality="Brazil", sort_by="overall", limit=5))
    section("Find forwards (ST) with overall >= 88",
            server.find_players(position="ST", min_overall=88, limit=5))
    section("Players at Santos (FIFA data)",
            server.find_players(club="Santos", limit=5))
    section("Brazilian players by club",
            server.player_club_summary(nationality="Brazil", limit=8))
    section("Average goals per match in the Brasileirão",
            server.statistics(competition="Brasileirão"))
    section("Biggest wins in the Brasileirão",
            server.biggest_wins(competition="Brasileirão", limit=5))
    section("Copa do Brasil 2019 statistics",
            server.statistics(competition="Copa do Brasil", season=2019))
    section("Libertadores finals in the data",
            server.find_matches(competition="Libertadores", limit=6))


if __name__ == "__main__":
    main()
