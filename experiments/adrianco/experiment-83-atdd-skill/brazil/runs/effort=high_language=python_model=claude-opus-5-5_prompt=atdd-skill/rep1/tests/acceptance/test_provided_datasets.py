"""The provided Kaggle datasets: every file is loaded, real questions get real answers, quickly.

These specs run against the real data in data/kaggle rather than synthetic data, because the
requirements are about that data: coverage of all six files and response times at full size.
"""
import pytest

from tests.acceptance.dsl.sample_questions import SAMPLE_QUESTIONS


def test_should_load_every_provided_dataset(provided):
    provided.assistant.request_dataset_summary()

    provided.assistant.confirm_datasets_loaded(
        "Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv", "fifa_data.csv")


def test_should_calculate_the_2019_brasileirao_champion(provided):
    provided.competitions.request_standings(season=2019)

    provided.competitions.confirm_champion("Flamengo", points=90, wins=28, draws=6, losses=4)


def test_should_identify_the_teams_relegated_in_2020(provided):
    provided.competitions.request_standings(season=2020)

    provided.competitions.confirm_relegated("Vasco", "Goiás", "Coritiba", "Botafogo")


def test_should_combine_player_and_match_data_for_a_club(provided):
    provided.teams.request_overview("Grêmio")

    provided.teams.confirm_has_results_and_squad()


@pytest.mark.parametrize("question", SAMPLE_QUESTIONS.keys())
def test_should_answer_sample_questions_promptly(provided, question):
    provided.assistant.ask_sample_question(question)

    provided.assistant.confirm_answered_promptly()


def test_should_have_at_least_twenty_sample_questions():
    assert len(SAMPLE_QUESTIONS) >= 20
