"""DSL for the questions people ask about Brazilian soccer, decomposed by domain area.

Each area asks its question (When) and then confirms the answer (Then). Confirmations are
named confirm_* and delegate to the protocol driver, which is where the checking happens.
"""


class Matches:
    def __init__(self, driver):
        self._driver = driver

    def search(self, *, team=None, opponent=None, venue="any", competition=None, season=None,
               date_from=None, date_to=None, stage=None):
        self._driver.search_matches(team=team, opponent=opponent, venue=venue, competition=competition,
                                    season=season, date_from=date_from, date_to=date_to, stage=stage)

    def search_between(self, team, opponent, **criteria):
        self.search(team=team, opponent=opponent, **criteria)

    def confirm_found(self, *results):
        self._driver.confirm_matches_found(list(results))

    def confirm_match_count(self, count):
        self._driver.confirm_match_count(count)

    def confirm_most_recent(self, result, *, date):
        self._driver.confirm_most_recent_match(result, date)

    def confirm_statistics(self, *, corners=None, shots=None):
        self._driver.confirm_match_statistics(corners=corners, shots=shots)


class Teams:
    def __init__(self, driver):
        self._driver = driver

    def request_record(self, team, *, season=None, venue="any", competition=None):
        self._driver.request_record(team=team, season=season, venue=venue, competition=competition)

    def confirm_record(self, *, matches, wins, draws, losses, goals_for, goals_against):
        self._driver.confirm_record(matches=matches, wins=wins, draws=draws, losses=losses,
                                    goals_for=goals_for, goals_against=goals_against)

    def confirm_win_rate(self, win_rate):
        self._driver.confirm_win_rate(win_rate)

    def request_overview(self, team):
        self._driver.request_overview(team)

    def confirm_competitions(self, *competitions):
        self._driver.confirm_competitions(list(competitions))

    def confirm_squad_includes(self, *players):
        self._driver.confirm_squad_includes(list(players))

    def confirm_has_results_and_squad(self):
        self._driver.confirm_has_results_and_squad()


class Rivalries:
    def __init__(self, driver):
        self._driver = driver

    def compare(self, team, other_team, *, competition=None):
        self._driver.compare(team, other_team, competition=competition)

    def confirm_head_to_head(self, *, draws, **wins_by_team):
        self._driver.confirm_head_to_head(wins_by_team, draws)

    def confirm_goals(self, **goals_by_team):
        self._driver.confirm_goals(goals_by_team)

    def confirm_derby_name(self, name):
        self._driver.confirm_derby_name(name)

    def find_derbies(self, *, season=None, competition=None):
        self._driver.find_derbies(season=season, competition=competition)

    def confirm_derbies(self, *results):
        self._driver.confirm_derbies(list(results))


class Players:
    def __init__(self, driver):
        self._driver = driver

    def look_up(self, name):
        self._driver.look_up(name)

    def confirm_profile(self, **expected):
        self._driver.confirm_profile(expected)

    def search(self, *, name=None, nationality=None, club=None, position=None, min_overall=None):
        self._driver.search(name=name, nationality=nationality, club=club, position=position,
                            min_overall=min_overall)

    def confirm_found(self, *names):
        self._driver.confirm_players_found(list(names), in_order=False)

    def confirm_not_found_but_suggested(self, *names):
        self._driver.confirm_not_found_but_suggested(list(names))

    def confirm_found_in_order(self, *names):
        self._driver.confirm_players_found(list(names), in_order=True)

    def summarise_brazilians_at_brazilian_clubs(self):
        self._driver.summarise_club_squads(nationality="Brazil", brazilian_clubs_only=True)

    def confirm_club_summary(self, **players_and_average_by_club):
        self._driver.confirm_club_summary(players_and_average_by_club)


class Competitions:
    def __init__(self, driver):
        self._driver = driver

    def request_standings(self, *, season, competition="Brasileirão"):
        self._driver.request_standings(season=season, competition=competition)

    def confirm_champion(self, team, *, points, wins=None, draws=None, losses=None):
        self._driver.confirm_champion(team, points=points, wins=wins, draws=draws, losses=losses)

    def confirm_table_order(self, *teams):
        self._driver.confirm_table_order(list(teams))

    def confirm_relegated(self, *teams):
        self._driver.confirm_relegated(list(teams))

    def request_bracket(self, competition, *, season):
        self._driver.request_bracket(competition=competition, season=season)

    def confirm_tie(self, stage, *, winner, aggregate):
        self._driver.confirm_tie(stage, winner=winner, aggregate=aggregate)


class Statistics:
    def __init__(self, driver):
        self._driver = driver

    def request_overview(self, *, competition=None, season=None):
        self._driver.request_overview(competition=competition, season=season)

    def confirm_average_goals_per_match(self, average):
        self._driver.confirm_average_goals_per_match(average)

    def confirm_home_win_rate(self, rate):
        self._driver.confirm_home_win_rate(rate)

    def request_biggest_wins(self, *, limit=10, competition=None, season=None, team=None):
        self._driver.request_biggest_wins(limit=limit, competition=competition, season=season, team=team)

    def confirm_biggest_wins(self, *results):
        self._driver.confirm_biggest_wins(list(results))

    def rank_teams_by(self, measure, *, venue="any", season=None, competition=None):
        self._driver.rank_teams(measure=measure, venue=venue, season=season, competition=competition)

    def confirm_leader(self, team):
        self._driver.confirm_leader(team)

    def compare_seasons(self, *seasons, competition="Brasileirão"):
        self._driver.compare_seasons(list(seasons), competition=competition)

    def confirm_season_averages(self, averages_by_season):
        self._driver.confirm_season_averages(averages_by_season)


class Assistant:
    """The AI assistant connected to the system, asking on a fan's behalf."""

    def __init__(self, driver, areas=None):
        self._driver = driver
        self._areas = areas

    def discover_capabilities(self):
        self._driver.discover_capabilities()

    def confirm_can_answer(self, *categories):
        self._driver.confirm_can_answer(list(categories))

    def ask_for_matches_between(self, team, opponent):
        self._driver.ask_for_matches_between(team, opponent)

    def ask_for_derbies(self, *, season=None, at_most=None):
        self._driver.ask_for_derbies(season=season, limit=at_most)

    def ask_for_record_of(self, team):
        self._driver.ask_for_record_of(team)

    def confirm_answer_reads(self, line):
        self._driver.confirm_answer_contains(line)

    def confirm_answer_explains(self, explanation):
        self._driver.confirm_answer_contains(explanation)

    def request_dataset_summary(self):
        self._driver.request_dataset_summary()

    def confirm_datasets_loaded(self, *datasets):
        self._driver.confirm_datasets_loaded(list(datasets))

    def ask_sample_question(self, question):
        from tests.acceptance.dsl.sample_questions import SAMPLE_QUESTIONS
        kind, ask = SAMPLE_QUESTIONS[question]
        self._expected_limit = {"simple": 2.0, "aggregate": 5.0}[kind]
        ask(self._areas)

    def confirm_answered_promptly(self):
        self._driver.confirm_last_answer_within(self._expected_limit)
