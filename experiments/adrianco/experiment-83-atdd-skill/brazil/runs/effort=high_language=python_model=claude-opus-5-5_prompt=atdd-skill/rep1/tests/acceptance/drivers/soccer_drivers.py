"""Protocol drivers that put fans' questions to the Brazilian soccer MCP server.

This is the only layer that knows the server's tool names, argument names and the shape of
its answers. Every confirm_* method passes or fails with a message in domain language.
"""


def describe(match):
    return f"{match['home']} {match['home_goals']}-{match['away_goals']} {match['away']}"


class QueryDriver:
    def __init__(self, session):
        self._session = session
        self._answer = None

    def _ask(self, tool, **arguments):
        self._answer = self._session.connection().call_tool(tool, arguments)
        return self._answer

    def _data(self):
        assert self._answer is not None, "No question has been asked yet"
        assert not self._answer.is_error, f"The question was not answered: {self._answer.text}"
        return self._answer.data


class MatchesDriver(QueryDriver):
    def search_matches(self, **criteria):
        self._ask("search_matches", limit=500, **criteria)

    def _found(self):
        return [describe(match) for match in self._data()["matches"]]

    def confirm_matches_found(self, expected):
        found = self._found()
        assert sorted(found) == sorted(expected), f"Expected to find {expected} but found {found}"

    def confirm_match_count(self, count):
        total = self._data()["total"]
        assert total == count, f"Expected {count} matches but found {total}: {self._found()}"

    def confirm_most_recent_match(self, result, date):
        matches = self._data()["matches"]
        assert matches, "No matches were found"
        latest = matches[0]
        assert (describe(latest), latest["date"]) == (result, date), \
            f"Expected the most recent match to be {result} on {date} but it was {describe(latest)} on {latest['date']}"

    def confirm_match_statistics(self, corners=None, shots=None):
        statistics = self._data()["matches"][0].get("statistics") or {}
        if corners:
            found = f"{statistics.get('home_corners')}-{statistics.get('away_corners')}"
            assert found == corners, f"Expected corners {corners} but found {found}"
        if shots:
            found = f"{statistics.get('home_shots')}-{statistics.get('away_shots')}"
            assert found == shots, f"Expected shots {shots} but found {found}"


class TeamsDriver(QueryDriver):
    def request_record(self, **criteria):
        self._ask("team_record", **criteria)

    def confirm_record(self, **expected):
        record = self._data()
        found = {key: record[key] for key in expected}
        assert found == expected, f"Expected record {expected} but found {found}"

    def confirm_win_rate(self, win_rate):
        found = f"{self._data()['win_rate']:.1f}%"
        assert found == win_rate, f"Expected a win rate of {win_rate} but found {found}"

    def request_overview(self, team):
        self._ask("team_overview", team=team)

    def confirm_competitions(self, expected):
        found = [entry["competition"] for entry in self._data()["competitions"]]
        assert sorted(found) == sorted(expected), f"Expected competitions {expected} but found {found}"

    def confirm_squad_includes(self, expected):
        found = [player["name"] for player in self._data()["squad"]["players"]]
        missing = [name for name in expected if name not in found]
        assert not missing, f"Expected the squad to include {missing} but it was {found}"

    def confirm_has_results_and_squad(self):
        overview = self._data()
        assert overview["record"]["matches"] > 0, f"No results were found for {overview['team']}"
        assert overview["squad"]["players"], f"No squad was found for {overview['team']}"


class RivalriesDriver(QueryDriver):
    def compare(self, team, other_team, competition=None):
        self._ask("head_to_head", team=team, opponent=other_team, competition=competition)

    def _sides(self):
        data = self._data()
        return {side["name"]: side for side in (data["team"], data["opponent"])}

    def confirm_head_to_head(self, wins_by_team, draws):
        sides = self._sides()
        found = {name: side["wins"] for name, side in sides.items()}
        assert found == wins_by_team, f"Expected wins {wins_by_team} but found {found}"
        assert self._data()["draws"] == draws, f"Expected {draws} draws but found {self._data()['draws']}"

    def confirm_goals(self, goals_by_team):
        found = {name: side["goals"] for name, side in self._sides().items()}
        assert found == goals_by_team, f"Expected goals {goals_by_team} but found {found}"

    def confirm_derby_name(self, name):
        found = self._data().get("derby")
        assert found == name, f"Expected this to be known as the {name} derby, but it was called {found}"

    def find_derbies(self, season=None, competition=None):
        self._ask("find_derbies", season=season, competition=competition, limit=500)

    def confirm_derbies(self, expected):
        found = [describe(match) for match in self._data()["matches"]]
        assert sorted(found) == sorted(expected), f"Expected derbies {expected} but found {found}"


class PlayersDriver(QueryDriver):
    def look_up(self, name):
        self._ask("get_player", name=name)

    def confirm_profile(self, expected):
        player = self._data()["player"]
        found = {key: player.get(key) for key in expected}
        assert found == expected, f"Expected a player matching {expected} but found {found}"

    def confirm_not_found_but_suggested(self, names):
        assert self._answer.is_error, f"Expected no player to be found, but found {self._answer.data.get('player')}"
        missing = [name for name in names if name not in self._answer.text]
        assert not missing, f"Expected {missing} to be suggested, but the answer was: {self._answer.text}"

    def search(self, **criteria):
        self._ask("search_players", limit=100, **criteria)

    def confirm_players_found(self, expected, in_order):
        found = [player["name"] for player in self._data()["players"]]
        if in_order:
            assert found == expected, f"Expected players in this order {expected} but found {found}"
        else:
            assert sorted(found) == sorted(expected), f"Expected players {expected} but found {found}"

    def summarise_club_squads(self, **criteria):
        self._ask("club_squads", **criteria)

    def confirm_club_summary(self, expected):
        found = {club["club"]: (club["players"], round(club["average_overall"]))
                 for club in self._data()["clubs"]}
        assert found == expected, f"Expected clubs (players, average rating) {expected} but found {found}"


class CompetitionsDriver(QueryDriver):
    def request_standings(self, **criteria):
        self._ask("standings", **criteria)

    def _table(self):
        return self._data()["table"]

    def confirm_champion(self, team, points, wins=None, draws=None, losses=None):
        champion = self._table()[0]
        expected = {"team": team, "points": points, "wins": wins, "draws": draws, "losses": losses}
        expected = {key: value for key, value in expected.items() if value is not None}
        found = {key: champion[key] for key in expected}
        assert found == expected, f"Expected the champion to be {expected} but found {found}"
        assert champion.get("status") == "champion", f"{team} topped the table but was not marked champion"

    def confirm_table_order(self, expected):
        found = [row["team"] for row in self._table()]
        assert found == expected, f"Expected the table to read {expected} but it read {found}"

    def confirm_relegated(self, expected):
        found = self._data()["relegated"]
        assert sorted(found) == sorted(expected), f"Expected {expected} to be relegated but it was {found}"

    def request_bracket(self, **criteria):
        self._ask("knockout_bracket", **criteria)

    def confirm_tie(self, stage, winner, aggregate):
        stages = {entry["stage"]: entry["ties"] for entry in self._data()["stages"]}
        assert stage in stages, f"There was no {stage} in the bracket, only {list(stages)}"
        for tie in stages[stage]:
            if tie["winner"] == winner:
                ours, theirs = ((tie["team_goals"], tie["opponent_goals"]) if tie["team"] == winner
                                else (tie["opponent_goals"], tie["team_goals"]))
                found = f"{ours}-{theirs}"
                assert found == aggregate, f"Expected {winner} to win {aggregate} on aggregate but it was {found}"
                return
        raise AssertionError(f"{winner} did not win a tie in the {stage}: {stages[stage]}")


MEASURES = {"win rate": "win_rate", "goals scored": "goals_scored", "goals conceded": "goals_conceded",
            "points": "points", "wins": "wins", "goal difference": "goal_difference"}


class StatisticsDriver(QueryDriver):
    def request_overview(self, **criteria):
        self._ask("competition_stats", **criteria)

    def confirm_average_goals_per_match(self, average):
        found = f"{self._data()['average_goals']:.2f}"
        assert found == average, f"Expected {average} goals per match but found {found}"

    def confirm_home_win_rate(self, rate):
        found = f"{self._data()['home_win_rate']:.1f}%"
        assert found == rate, f"Expected a home win rate of {rate} but found {found}"

    def request_biggest_wins(self, **criteria):
        self._ask("biggest_wins", **criteria)

    def confirm_biggest_wins(self, expected):
        found = [describe(match) for match in self._data()["matches"]]
        assert found == expected, f"Expected the biggest wins to be {expected} but found {found}"

    def rank_teams(self, measure, **criteria):
        self._ask("rank_teams", metric=MEASURES[measure], **criteria)

    def confirm_leader(self, team):
        rankings = self._data()["rankings"]
        assert rankings, "No teams were ranked"
        assert rankings[0]["team"] == team, f"Expected {team} to lead but the ranking was {rankings[:3]}"

    def compare_seasons(self, seasons, competition=None):
        self._ask("compare_seasons", seasons=seasons, competition=competition)

    def confirm_season_averages(self, expected):
        found = {entry["season"]: f"{entry['average_goals']:.2f}" for entry in self._data()["seasons"]}
        assert found == expected, f"Expected season averages {expected} but found {found}"


CAPABILITIES = {
    "matches": ["search_matches"],
    "teams": ["team_record", "team_overview", "head_to_head"],
    "players": ["search_players", "get_player", "club_squads"],
    "competitions": ["standings", "knockout_bracket"],
    "statistics": ["competition_stats", "biggest_wins", "rank_teams", "compare_seasons"],
}


class AssistantDriver(QueryDriver):
    def discover_capabilities(self):
        self._tools = {tool["name"]: tool for tool in self._session.connection().list_tools()}

    def confirm_can_answer(self, categories):
        for category in categories:
            for tool in CAPABILITIES[category]:
                assert tool in self._tools, f"An assistant cannot ask about {category}: '{tool}' is not offered"
                described = self._tools[tool]
                assert described.get("description"), f"'{tool}' does not explain what it answers"
                assert described.get("inputSchema", {}).get("type") == "object", \
                    f"'{tool}' does not describe the details it needs"

    def ask_for_matches_between(self, team, opponent):
        self._ask("search_matches", team=team, opponent=opponent)

    def ask_for_derbies(self, season=None, limit=None):
        self._ask("find_derbies", season=season, limit=limit)

    def ask_for_record_of(self, team):
        self._ask("team_record", team=team)

    def confirm_answer_contains(self, expected):
        assert self._answer is not None, "No question has been asked yet"
        assert expected in self._answer.text, f"Expected the answer to include '{expected}' but it was:\n{self._answer.text}"

    def request_dataset_summary(self):
        self._ask("dataset_summary")

    def confirm_datasets_loaded(self, expected):
        loaded = {entry["file"]: entry["records"] for entry in self._data()["datasets"]}
        missing = [name for name in expected if loaded.get(name, 0) == 0]
        assert not missing, f"These datasets were not loaded: {missing} (loaded: {loaded})"

    def confirm_last_answer_within(self, seconds):
        answer = self._session.connection().last_answer
        assert answer is not None, "No question has been asked yet"
        assert not answer.is_error, f"The question was not answered: {answer.text}"
        assert answer.text.strip() and not answer.text.startswith("No "), f"The answer was empty: {answer.text}"
        assert answer.seconds < seconds, f"The answer took {answer.seconds:.2f}s, more than {seconds}s"
