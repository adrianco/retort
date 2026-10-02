"""
Protocol driver (layer 3): translates DSL questions into MCP tool calls on
the running Brazilian Soccer MCP server, and checks the answers.

This is the only layer that knows the system is an MCP server, which tools
it offers and the shape of their results. Every method passes or fails:
questions fail if the server reports a problem it shouldn't, confirmations
fail with a message in domain language.
"""

import contextlib
import time
import unicodedata

from .mcp_client import McpClient

COMPETITIONS = {
    "brasileirão": "Brasileirão Série A",
    "libertadores": "Copa Libertadores",
    "copa do brasil": "Copa do Brasil",
}


class McpSoccerDriver:
    def __init__(self, data_dir, before_first_question=lambda: None):
        self._data_dir = data_dir
        self._before_first_question = before_first_question
        self._client = None
        self._answer = None
        self._is_error = False
        self._text = ""

    # -- questions ---------------------------------------------------------

    def search_matches(self, **criteria):
        self._ask("find_matches", criteria)

    def team_record(self, **criteria):
        self._ask("team_record", criteria)

    def head_to_head(self, team, other_team, competition=None):
        self._ask("head_to_head", {"team_a": team, "team_b": other_team, "competition": competition})

    def competitions_played(self, team):
        self._ask("team_competitions", {"team": team})

    def standings(self, season, competition):
        self._ask("standings", {"season": season, "competition": competition})

    def finals(self, competition, season):
        self._ask("cup_finals", {"competition": competition, "season": season})

    def knockout_bracket(self, season, competition):
        self._ask("knockout_bracket", {"season": season, "competition": competition})

    def derbies(self, season):
        self._ask("find_derbies", {"season": season})

    def competition_summary(self, competition, season):
        self._ask("competition_stats", {"competition": competition, "season": season})

    def biggest_wins(self, competition, season):
        self._ask("biggest_wins", {"competition": competition, "season": season})

    def rank_teams(self, metric, venue, competition, season):
        self._ask("rank_teams", {"metric": metric, "venue": venue, "competition": competition, "season": season})

    def compare_seasons(self, season, other_season, competition):
        self._ask("compare_seasons", {"seasons": [season, other_season], "competition": competition})

    def player_profile(self, name):
        self._ask("player_profile", {"name": name})

    def search_players(self, **criteria):
        self._ask("search_players", criteria)

    def brazilian_club_summary(self, nationality):
        self._ask("brazilian_club_players", {"nationality": nationality})

    def team_profile(self, team):
        self._ask("team_profile", {"team": team})

    def dataset_overview(self):
        self._ask("dataset_info", {})

    @contextlib.contextmanager
    def time_limit(self, seconds):
        self._connect()
        started = time.perf_counter()
        yield
        elapsed = time.perf_counter() - started
        assert elapsed < seconds, f"Answer took {elapsed:.2f}s, more than the {seconds}s allowed"

    # -- confirmations -----------------------------------------------------

    def confirm_answered(self):
        self._confirm_no_error()
        assert self._text.strip(), "The answer was empty"
        assert self._answer, "The answer carried no data"

    def confirm_match_count(self, count):
        self._confirm_no_error()
        assert self._answer["total"] == count, \
            f"Expected {count} matches, found {self._answer['total']}:\n{self._text}"

    def confirm_all_matches_in(self, competition):
        for match in self._answer["matches"]:
            assert match["competition"] == competition, f"{_describe(match)} is not a {competition} match"

    def confirm_first_match(self, **expected):
        self._confirm_no_error()
        assert self._answer["matches"], "No matches were found"
        match = self._answer["matches"][0]
        actual = {
            "date": match["date"],
            "home": match["home"],
            "away": match["away"],
            "score": f"{match['home_goals']}-{match['away_goals']}",
        }
        stats = match.get("stats") or {}
        if "home_corners" in stats:
            actual["corners"] = f"{stats['home_corners']}-{stats['away_corners']}"
        if "home_shots" in stats:
            actual["shots"] = f"{stats['home_shots']}-{stats['away_shots']}"
        for key, value in expected.items():
            assert _same(actual.get(key), value), \
                f"Expected first match {key} to be {value}, but it was {actual.get(key)} ({_describe(match)})"

    def confirm_record(self, **expected):
        self._confirm_no_error()
        for key, value in expected.items():
            actual = self._answer[key]
            if key == "win_rate":
                actual = f"{actual:.1f}%"
            assert actual == value, f"Expected {key} {value}, got {actual}:\n{self._text}"

    def confirm_head_to_head(self, matches, first_team_wins, second_team_wins, draws):
        self._confirm_no_error()
        actual = (self._answer["matches"], self._answer["team_a_wins"], self._answer["team_b_wins"],
                  self._answer["draws"])
        assert actual == (matches, first_team_wins, second_team_wins, draws), \
            f"Expected (matches, wins, other wins, draws) {(matches, first_team_wins, second_team_wins, draws)}, " \
            f"got {actual}:\n{self._text}"

    def confirm_competitions(self, competitions):
        self._confirm_no_error()
        actual = {c["competition"] for c in self._answer["competitions"]}
        assert actual == set(competitions), f"Expected competitions {set(competitions)}, got {actual}"

    def confirm_team_not_recognised(self, team):
        assert self._is_error, f"Expected '{team}' not to be recognised, but got an answer:\n{self._text}"
        assert self._answer.get("error") == "unknown_team", f"Unexpected error: {self._text}"
        assert team in self._text, f"The explanation did not mention '{team}': {self._text}"

    def confirm_player_profile(self, **expected):
        self._confirm_no_error()
        player = self._answer["player"]
        for key, value in expected.items():
            assert _same(player[key], value), f"Expected {key} {value}, got {player[key]}"

    def confirm_player_count(self, count):
        self._confirm_no_error()
        assert self._answer["total"] == count, \
            f"Expected {count} players, found {self._answer['total']}:\n{self._text}"

    def confirm_players_in_order(self, names):
        self._confirm_no_error()
        actual = [p["name"] for p in self._answer["players"]][:len(names)]
        assert actual == list(names), f"Expected players {list(names)} first, got {actual}"

    def confirm_club_summary(self, club, players, average_overall):
        self._confirm_no_error()
        entry = self._find(self._answer["clubs"], "club", club)
        assert entry["players"] == players, f"Expected {players} players at {club}, got {entry['players']}"
        assert round(entry["average_overall"]) == average_overall, \
            f"Expected average rating {average_overall} at {club}, got {entry['average_overall']}"

    def confirm_club_not_in_summary(self, club):
        clubs = [entry["club"] for entry in self._answer["clubs"]]
        assert not any(_same(c, club) for c in clubs), f"{club} should not be listed as a Brazilian club"

    def confirm_team_profile(self, wins, squad_includes):
        self._confirm_no_error()
        assert self._answer["record"]["wins"] == wins, \
            f"Expected {wins} wins, got {self._answer['record']['wins']}"
        squad = [p["name"] for p in self._answer["squad"]]
        assert squad_includes in squad, f"Expected {squad_includes} in the squad, got {squad}"

    def confirm_champion(self, team, **expected):
        self._confirm_no_error()
        leader = self._answer["table"][0]
        assert _same(leader["team"], team), f"Expected {team} to be champion, but it was {leader['team']}"
        for key, value in expected.items():
            assert leader[key] == value, f"Expected champion's {key} to be {value}, got {leader[key]}"

    def confirm_table_order(self, teams):
        self._confirm_no_error()
        actual = [row["team"] for row in self._answer["table"]]
        assert _same_names(actual, teams), f"Expected table order {list(teams)}, got {actual}"

    def confirm_relegated(self, teams):
        self._confirm_no_error()
        actual = self._answer["relegated"]
        assert len(actual) == len(teams) and all(any(_same(a, t) for a in actual) for t in teams), \
            f"Expected {list(teams)} to be relegated, got {actual}"

    def confirm_final(self, season, finalists, winner):
        self._confirm_no_error()
        final = self._find(self._answer["finals"], "season", season)
        assert _same_set(final["finalists"], finalists), \
            f"Expected finalists {finalists} in {season}, got {final['finalists']}"
        assert _same(final["winner"], winner), f"Expected {winner} to win the {season} final, got {final['winner']}"

    def confirm_final_undecided(self, season):
        self._confirm_no_error()
        final = self._find(self._answer["finals"], "season", season)
        assert final["winner"] is None, \
            f"Expected the {season} final to be level with no winner in the data, but {final['winner']} won it " \
            f"({final['decided_by']})"

    def confirm_tie(self, stage, teams, winner):
        self._confirm_no_error()
        stage_entry = self._find(self._answer["stages"], "stage", stage)
        ties = [tie for tie in stage_entry["ties"] if _same_set(tie["teams"], teams)]
        assert ties, f"No {stage} tie between {teams}; ties were {[t['teams'] for t in stage_entry['ties']]}"
        assert _same(ties[0]["winner"], winner), f"Expected {winner} to win the {stage} tie, got {ties[0]['winner']}"

    def confirm_derbies(self, derby_names):
        self._confirm_no_error()
        actual = sorted(m["derby"] for m in self._answer["matches"])
        assert actual == sorted(derby_names), f"Expected derbies {sorted(derby_names)}, got {actual}"

    def confirm_summary(self, **expected):
        self._confirm_no_error()
        for key, value in expected.items():
            actual = self._answer[key]
            if key.endswith("_rate"):
                actual = f"{actual:.1f}%"
            assert actual == value, f"Expected {key} {value}, got {actual}:\n{self._text}"

    def confirm_ranking(self, teams):
        self._confirm_no_error()
        if "ranking" in self._answer:
            actual = [entry["team"] for entry in self._answer["ranking"]][:len(teams)]
        else:
            actual = [match["winner"] for match in self._answer["matches"]][:len(teams)]
        assert _same_names(actual, teams), f"Expected ranking to start {list(teams)}, got {actual}"

    def confirm_season_average_goals(self, season, average_goals):
        self._confirm_no_error()
        entry = self._find(self._answer["seasons"], "season", season)
        assert entry["average_goals"] == average_goals, \
            f"Expected {average_goals} goals per match in {season}, got {entry['average_goals']}"

    def confirm_file_loaded(self, file_name, rows):
        self._confirm_no_error()
        entry = self._find(self._answer["files"], "file", file_name)
        assert entry["loaded"], f"{file_name} was not loaded"
        assert entry["rows"] == rows, f"Expected {rows} rows from {file_name}, got {entry['rows']}"

    # -- plumbing ----------------------------------------------------------

    def close(self):
        if self._client:
            self._client.close()

    def _connect(self):
        if self._client is None:
            self._before_first_question()
            self._client = McpClient(self._data_dir)

    def _ask(self, tool, arguments):
        self._connect()
        if "competition" in arguments and arguments["competition"]:
            arguments["competition"] = COMPETITIONS.get(arguments["competition"].lower(), arguments["competition"])
        result = self._client.call_tool(tool, arguments)
        self._is_error = bool(result.get("isError"))
        self._answer = result.get("structuredContent") or {}
        self._text = "\n".join(c["text"] for c in result.get("content", []) if c.get("type") == "text")

    def _confirm_no_error(self):
        assert not self._is_error, f"The server could not answer: {self._text}"

    @staticmethod
    def _find(entries, key, value):
        for entry in entries:
            if _same(entry[key], value):
                return entry
        raise AssertionError(f"Nothing with {key} {value!r} in {[e[key] for e in entries]}")


def _fold(name):
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return " ".join(text.replace("-", " ").split())


def _same(actual, expected):
    """Names match ignoring accents and case; "Vasco" names "Vasco da Gama"."""
    if isinstance(expected, (int, float)) or isinstance(actual, (int, float)):
        return actual == expected
    a, e = _fold(actual), _fold(expected)
    return a == e or a.startswith(e + " ") or e.startswith(a + " ")


def _same_names(actual, expected):
    return len(actual) >= len(expected) and all(_same(a, e) for a, e in zip(actual, expected))


def _same_set(actual, expected):
    return len(actual) == len(expected) and all(any(_same(a, e) for a in actual) for e in expected)


def _describe(match):
    return f"{match['date']}: {match['home']} {match['home_goals']}-{match['away_goals']} {match['away']}"
