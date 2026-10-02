"""
Executable specification: the system answers questions from the six
provided Kaggle datasets, quickly enough to be used conversationally.

Layer 1 of the four-layer acceptance test model. Unlike the other specs,
which build synthetic data per test, these run against the real files in
data/kaggle, so the facts they confirm are real historical outcomes.
"""

import pytest


class ProvidedDatasetsSpec:
    def should_load_all_six_provided_files(self, real_data):
        real_data.dataset_overview()

        real_data.confirm_file_loaded("Brasileirao_Matches.csv", rows=4180)
        real_data.confirm_file_loaded("Brazilian_Cup_Matches.csv", rows=1337)
        real_data.confirm_file_loaded("Libertadores_Matches.csv", rows=1255)
        real_data.confirm_file_loaded("BR-Football-Dataset.csv", rows=10296)
        real_data.confirm_file_loaded("novo_campeonato_brasileiro.csv", rows=6886)
        real_data.confirm_file_loaded("fifa_data.csv", rows=18207)

    def should_name_flamengo_champion_of_the_2019_brasileirao(self, real_data):
        real_data.standings(season=2019)

        real_data.confirm_champion("Flamengo", points=90, wins=28, draws=6, losses=4)

    def should_identify_the_teams_relegated_in_2020(self, real_data):
        real_data.standings(season=2020)

        real_data.confirm_relegated("Vasco da Gama", "Goiás", "Coritiba", "Botafogo")

    def should_name_palmeiras_winner_of_the_2020_copa_do_brasil(self, real_data):
        real_data.finals(competition="Copa do Brasil", season=2020)

        real_data.confirm_final(season=2020, finalists=("Grêmio", "Palmeiras"), winner="Palmeiras")

    def should_rank_neymar_as_the_top_rated_brazilian_player(self, real_data):
        real_data.search_players(nationality="Brazil")

        real_data.confirm_players_start_with("Neymar Jr")

    def should_answer_a_simple_lookup_within_two_seconds(self, real_data):
        real_data.within_seconds(2).search_matches(team="Flamengo", opponent="Corinthians")

    def should_answer_an_aggregate_question_within_five_seconds(self, real_data):
        real_data.within_seconds(5).rank_teams(by="win rate", venue="home")


SAMPLE_QUESTIONS = [
    ("Show me all Flamengo vs Fluminense matches", lambda q: q.search_matches(team="Flamengo", opponent="Fluminense")),
    ("What matches did Palmeiras play in 2021?", lambda q: q.search_matches(team="Palmeiras", season=2021)),
    ("Find all Copa do Brasil finals", lambda q: q.finals(competition="Copa do Brasil")),
    ("What is Corinthians' home record in 2022?", lambda q: q.team_record(team="Corinthians", season=2022, venue="home")),
    ("Which team scored the most goals in Serie A 2023?",
     lambda q: q.rank_teams(by="goals scored", competition="Brasileirão", season=2023)),
    ("Compare Palmeiras and Santos head-to-head", lambda q: q.head_to_head("Palmeiras", "Santos")),
    ("Find all Brazilian players in the dataset", lambda q: q.search_players(nationality="Brazil")),
    ("Who are the highest-rated players at Grêmio?", lambda q: q.search_players(club="Grêmio")),
    ("Show me all forwards from Santos", lambda q: q.search_players(club="Santos", position="forward")),
    ("Who won the 2019 Brasileirão?", lambda q: q.standings(season=2019)),
    ("Show the 2018 Copa Libertadores bracket", lambda q: q.knockout_bracket(season=2018)),
    ("Which teams were relegated in 2020?", lambda q: q.standings(season=2020)),
    ("What's the average goals per match in the Brasileirão?",
     lambda q: q.competition_summary(competition="Brasileirão")),
    ("Which team has the best away record?", lambda q: q.rank_teams(by="win rate", venue="away")),
    ("Show me the biggest wins in the dataset", lambda q: q.biggest_wins()),
    ("When did Flamengo last play Corinthians?", lambda q: q.search_matches(team="Flamengo", opponent="Corinthians")),
    ("Who is Gabriel Jesus?", lambda q: q.player_profile(name="Gabriel Jesus")),
    ("Show me all derbies in 2022", lambda q: q.derbies(season=2022)),
    ("What competitions has Palmeiras played in?", lambda q: q.competitions_played(team="Palmeiras")),
    ("Which team has the best home record?", lambda q: q.rank_teams(by="win rate", venue="home")),
    ("Who are the top Brazilian players at Brazilian clubs?",
     lambda q: q.summarise_by_brazilian_club(nationality="Brazil")),
    ("Compare the 2018 and 2019 seasons", lambda q: q.compare_seasons(2018, 2019)),
    ("How did Grêmio do and who plays for them?", lambda q: q.team_profile(team="Grêmio")),
    ("What happened in Serie B in 2022?", lambda q: q.competition_summary(competition="Serie B", season=2022)),
]


@pytest.mark.parametrize("question, ask", SAMPLE_QUESTIONS, ids=[q for q, _ in SAMPLE_QUESTIONS])
def should_answer_sample_question(real_data, question, ask):
    ask(real_data)

    real_data.confirm_answered()
