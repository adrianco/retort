#!/usr/bin/env python3
"""
================================================================================
demo.py - Answer the specification's sample questions end-to-end
================================================================================

CONTEXT
-------
Exercises the query engine / MCP tool layer against the >20 sample questions
listed in the specification, printing each question and the formatted answer.
Run with ``python demo.py`` as a quick, dependency-light acceptance check that
all five capability areas work against the real bundled data.
================================================================================
"""

from brazilian_soccer_mcp import server as s


def ask(question: str, answer: str) -> None:
    print("=" * 78)
    print("Q:", question)
    print("-" * 78)
    print(answer)
    print()


def main() -> None:
    ask("Overview of loaded data", s.data_summary())

    # 1. Match queries
    ask("Show me all Flamengo vs Fluminense matches",
        s.find_matches(team="Flamengo", opponent="Fluminense", limit=8))
    ask("What matches did Palmeiras play in 2019?",
        s.find_matches(team="Palmeiras", season=2019, limit=6))
    ask("When did Flamengo last play Corinthians?",
        s.last_match("Flamengo", "Corinthians"))

    # 2. Team queries
    ask("What is Corinthians' home record in 2019?",
        s.team_record("Corinthians", season=2019, scope="home"))
    ask("Compare Palmeiras and Santos head-to-head",
        s.head_to_head("Palmeiras", "Santos"))
    ask("What competitions has Palmeiras played in?",
        s.competitions_for_team("Palmeiras"))

    # 3. Player queries
    ask("Who are the top Brazilian players?",
        s.search_players(nationality="Brazil", limit=5))
    ask("Who is Gabriel Barbosa?", s.get_player("Gabriel Barbosa"))
    ask("Which goalkeepers are the best Brazilians?",
        s.search_players(nationality="Brazil", position="GK", limit=5))
    ask("Brazilian players by club", s.brazilian_clubs_summary(top=8))

    # 4. Competition queries
    ask("Who won the 2019 Brasileirão?", s.competition_winner(2019))
    ask("Show the 2019 Brasileirão final standings", s.standings(2019))
    ask("Which teams were relegated in 2019?", s.relegated_teams(2019))

    # 5. Statistical analysis
    ask("What's the average goals per match in the Brasileirão?",
        s.league_statistics("serie_a"))
    ask("Show me the biggest wins in Série A", s.biggest_wins("serie_a", limit=5))
    ask("Which team had the best home record in 2019?",
        s.best_record("serie_a", season=2019, scope="home"))
    ask("Which team scored the most goals in 2019 Série A?",
        s.top_scoring_team("serie_a", season=2019))


if __name__ == "__main__":
    main()
