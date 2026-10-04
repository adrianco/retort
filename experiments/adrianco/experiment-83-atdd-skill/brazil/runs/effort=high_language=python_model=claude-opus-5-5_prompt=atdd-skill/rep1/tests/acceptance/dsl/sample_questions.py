"""The sample questions from the specification, and how an assistant would put each one to the system.

"simple" questions are lookups (answer within 2 seconds); "aggregate" ones calculate
across many matches (answer within 5 seconds).
"""

SAMPLE_QUESTIONS = {
    "Show me all Flamengo vs Fluminense matches":
        ("simple", lambda q: q.matches.search_between("Flamengo", "Fluminense")),
    "What matches did Palmeiras play in 2023?":
        ("simple", lambda q: q.matches.search(team="Palmeiras", season=2023)),
    "Find all Copa do Brasil finals":
        ("simple", lambda q: q.matches.search(competition="Copa do Brasil", stage="final")),
    "When did Flamengo last play Corinthians?":
        ("simple", lambda q: q.matches.search_between("Flamengo", "Corinthians")),
    "What is Corinthians' home record in 2022?":
        ("aggregate", lambda q: q.teams.request_record("Corinthians", season=2022, venue="home")),
    "Which team scored the most goals in Serie A 2023?":
        ("aggregate", lambda q: q.statistics.rank_teams_by("goals scored", season=2023, competition="Serie A")),
    "Compare Palmeiras and Santos head-to-head":
        ("aggregate", lambda q: q.rivalries.compare("Palmeiras", "Santos")),
    "Find all Brazilian players in the dataset":
        ("simple", lambda q: q.players.search(nationality="Brazilian")),
    "Who are the highest-rated players at Grêmio?":
        ("simple", lambda q: q.players.search(club="Grêmio")),
    "Show me all forwards from Santos":
        ("simple", lambda q: q.players.search(club="Santos", position="forward")),
    "Who is Gabriel Jesus?":
        ("simple", lambda q: q.players.look_up("Gabriel Jesus")),
    "Who won the 2019 Brasileirão?":
        ("aggregate", lambda q: q.competitions.request_standings(season=2019)),
    "Show the 2018 Copa Libertadores bracket":
        ("aggregate", lambda q: q.competitions.request_bracket("Copa Libertadores", season=2018)),
    "Which teams were relegated in 2020?":
        ("aggregate", lambda q: q.competitions.request_standings(season=2020)),
    "What's the average goals per match in the Brasileirão?":
        ("aggregate", lambda q: q.statistics.request_overview(competition="Brasileirão")),
    "Which team has the best away record?":
        ("aggregate", lambda q: q.statistics.rank_teams_by("win rate", venue="away")),
    "Which team has the best home record?":
        ("aggregate", lambda q: q.statistics.rank_teams_by("win rate", venue="home")),
    "Show me the biggest wins in the dataset":
        ("aggregate", lambda q: q.statistics.request_biggest_wins(limit=10)),
    "Compare the 2018 and 2019 seasons":
        ("aggregate", lambda q: q.statistics.compare_seasons(2018, 2019)),
    "Show me all derbies in 2023":
        ("aggregate", lambda q: q.rivalries.find_derbies(season=2023)),
    "What competitions has Palmeiras played in?":
        ("aggregate", lambda q: q.teams.request_overview("Palmeiras")),
    "Who are the top Brazilian players at Brazilian clubs?":
        ("aggregate", lambda q: q.players.summarise_brazilians_at_brazilian_clubs()),
    "How did Flamengo do in the Copa Libertadores?":
        ("aggregate", lambda q: q.teams.request_record("Flamengo", competition="Copa Libertadores")),
    "What happened in Serie B in 2022?":
        ("aggregate", lambda q: q.statistics.request_overview(competition="Série B", season=2022)),
}
