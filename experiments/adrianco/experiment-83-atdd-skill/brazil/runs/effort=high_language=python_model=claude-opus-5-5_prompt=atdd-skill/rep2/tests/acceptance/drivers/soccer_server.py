"""
Protocol driver (layer 3): asking the Brazilian Soccer MCP server questions.

This is the only layer of the test infrastructure that knows how the system
works: that it is an MCP server, which tools it exposes, what their arguments
are called and the shape of their structured results. The DSL calls it at the
same level of abstraction as the specs ("confirm the head-to-head between
Palmeiras and Santos"); it turns that into tools/call requests and asserts on
the answers. Every confirm_ method passes or fails with a message in football
language.

The server is started lazily on the first question, so the DSL can finish
describing the datasets first.
"""
import time
import unicodedata

from .mcp_client import McpStdioClient, soccer_server_command, soccer_server_environment


class Answer:
    def __init__(self, text, data):
        self.text = text
        self.data = data

    def __repr__(self):
        return self.text


class SoccerServerDriver:
    def __init__(self, data_dir, before_start=None):
        self._data_dir = data_dir
        self._before_start = before_start
        self._client = None

    def stop(self):
        if self._client:
            self._client.close()

    # --- matches --------------------------------------------------------------------------------------------------

    def find_matches(self, **criteria):
        return self._ask("find_matches", {**criteria, "limit": 500})

    def confirm_meetings(self, team, opponent, count=None, listed=None, from_competitions=None, at_least=None):
        answer = self.find_matches(team=team, opponent=opponent)
        found = answer.data["total"]
        if count is not None:
            assert found == count, f"Expected {count} meetings of {team} and {opponent}, found {found}:\n{answer}"
        if at_least is not None:
            assert found >= at_least, f"Expected at least {at_least} meetings of {team} and {opponent}, found {found}"
        if listed:
            _confirm_lines_in_order(answer.text, listed)
        for competition in from_competitions or []:
            assert any(m["competition"] == competition for m in answer.data["matches"]), \
                f"Expected meetings of {team} and {opponent} in {competition}:\n{answer}"

    def confirm_matches_found(self, criteria, count):
        answer = self.find_matches(**criteria)
        found = answer.data["total"]
        assert found == count, f"Expected {count} matches for {_describe(criteria)}, found {found}:\n{answer}"

    def confirm_match_statistics(self, team, opponent, statistics):
        answer = self.find_matches(team=team, opponent=opponent)
        assert answer.data["matches"], f"No match found between {team} and {opponent}"
        recorded = answer.data["matches"][0].get("statistics") or {}
        for name, score in statistics.items():
            expected = [int(n) for n in score.split("-")]
            assert recorded.get(name) == expected, \
                f"Expected {name} {score} in {team} vs {opponent}, but the statistics were {recorded}:\n{answer}"

    def head_to_head(self, team, opponent):
        return self._ask("head_to_head", {"team": team, "opponent": opponent})

    def confirm_last_meeting(self, team, opponent, meeting):
        answer = self.head_to_head(team, opponent)
        last = answer.data["last_meeting"]
        assert last and last["summary"].startswith(meeting), \
            f"Expected the last meeting of {team} and {opponent} to be {meeting!r}, got {last and last['summary']!r}"
        assert meeting in answer.text, f"The answer should mention the last meeting {meeting!r}:\n{answer}"

    def confirm_head_to_head(self, team, opponent, wins, draws):
        answer = self.head_to_head(team, opponent)
        actual = (answer.data["wins"], answer.data["opponent_wins"]), answer.data["draws"]
        assert actual == (tuple(wins), draws), \
            f"Expected {team} {wins[0]} wins, {opponent} {wins[1]} wins, {draws} draws; got {actual}:\n{answer}"

    # --- teams ----------------------------------------------------------------------------------------------------

    def team_record(self, team, season=None, competition=None, venue="all"):
        return self._ask("team_record", {"team": team, "season": season, "competition": competition, "venue": venue})

    def confirm_team_record(self, team, criteria, expected):
        answer = self.team_record(team, **criteria)
        for name, value in expected.items():
            actual = answer.data[name]
            if name == "win_rate":
                actual = f"{actual:.1f}%"
            assert actual == value, f"Expected {team} {name.replace('_', ' ')} {value}, got {actual}:\n{answer}"
        if "win_rate" in expected:
            assert expected["win_rate"] in answer.text, f"The answer should state the win rate:\n{answer}"

    def confirm_unknown_team(self, team, suggesting):
        result = self._connection().call_tool("team_record", {"team": team})
        text = "\n".join(block.get("text", "") for block in result.get("content", []))
        assert result.get("isError"), f"Expected {team} to be unknown, but got an answer:\n{text}"
        assert team in text and "No team" in text, f"The error should explain {team} is unknown: {text}"
        if suggesting:
            assert suggesting in text, f"The error should suggest {suggesting}: {text}"

    def team_competitions(self, team):
        return self._ask("team_competitions", {"team": team})

    def confirm_team_competitions(self, team, competitions):
        answer = self.team_competitions(team)
        actual = sorted(c["competition"] for c in answer.data["competitions"])
        assert actual == sorted(competitions), f"Expected {team} to have played in {competitions}, got {actual}"

    def club_profile(self, team):
        return self._ask("club_profile", {"team": team})

    def confirm_club_profile(self, team, expected):
        answer = self.club_profile(team)
        actual = {"squad_size": answer.data["squad"]["size"], "matches_played": answer.data["record"]["played"]}
        for name, value in expected.items():
            assert actual[name] == value, f"Expected {team} {name.replace('_', ' ')} {value}, got {actual[name]}"

    # --- competitions ---------------------------------------------------------------------------------------------

    def league_table(self, season, competition):
        return self._ask("league_table", {"season": season, "competition": competition})

    def confirm_champion(self, season, competition, team):
        answer = self.league_table(season, competition)
        assert _same_team(answer.data["champion"], team), \
            f"Expected {team} to be {season} champion, got {answer.data['champion']}:\n{answer}"
        assert "Champion" in answer.text, f"The table should mark the champion:\n{answer}"

    def confirm_standing(self, season, competition, position, team, expected):
        answer = self.league_table(season, competition)
        standings = answer.data["standings"]
        assert len(standings) >= position, f"The {season} table has only {len(standings)} teams:\n{answer}"
        row = standings[position - 1]
        assert _same_team(row["team"], team), f"Expected {team} in position {position}, got {row['team']}:\n{answer}"
        for name, value in expected.items():
            assert row[name] == value, f"Expected {team} {name} {value}, got {row[name]}:\n{answer}"

    def confirm_relegated(self, season, competition, teams):
        answer = self.league_table(season, competition)
        relegated = answer.data["relegated"]
        assert len(relegated) == len(teams) and all(any(_same_team(r, t) for r in relegated) for t in teams), \
            f"Expected {teams} to be relegated in {season}, got {relegated}:\n{answer}"

    def top_scoring_teams(self, season, competition):
        return self._ask("top_scoring_teams", {"season": season, "competition": competition})

    def confirm_top_scoring_team(self, season, competition, team, goals):
        answer = self.top_scoring_teams(season, competition)
        top = answer.data["teams"][0]
        assert _same_team(top["team"], team) and top["goals"] == goals, \
            f"Expected {team} to top the {season} scoring with {goals} goals, got {top}:\n{answer}"

    def knockout_bracket(self, competition, season):
        return self._ask("knockout_bracket", {"competition": competition, "season": season})

    def confirm_bracket(self, competition, season, stages):
        answer = self.knockout_bracket(competition, season)
        actual = {stage["stage"]: [tie["label"] for tie in stage["ties"]] for stage in answer.data["stages"]}
        assert actual == stages, f"Expected the {season} {competition} bracket {stages}, got {actual}:\n{answer}"

    # --- statistics -----------------------------------------------------------------------------------------------

    def competition_summary(self, competition, season):
        return self._ask("competition_summary", {"competition": competition, "season": season})

    def confirm_competition_summary(self, competition, season, expected):
        answer = self.competition_summary(competition, season)
        formats = {"average_goals": "{:.2f}", "home_win_rate": "{:.1f}%", "draw_rate": "{:.1f}%",
                   "away_win_rate": "{:.1f}%"}
        for name, value in expected.items():
            actual = formats.get(name, "{}").format(answer.data[name])
            assert actual == str(value), f"Expected {name.replace('_', ' ')} {value}, got {actual}:\n{answer}"
            assert name not in formats or actual in answer.text, f"The answer should state {actual}:\n{answer}"

    def biggest_wins(self, competition, season):
        return self._ask("biggest_wins", {"competition": competition, "season": season})

    def confirm_biggest_wins(self, competition, season, listed):
        answer = self.biggest_wins(competition, season)
        actual = [m["summary"] for m in answer.data["matches"][:len(listed)]]
        assert actual == listed, f"Expected the biggest wins {listed}, got {actual}"
        _confirm_lines_in_order(answer.text, listed)

    def best_records(self, venue, competition, season):
        return self._ask("best_records", {"venue": venue, "competition": competition, "season": season})

    def confirm_best_record(self, venue, competition, season, team):
        answer = self.best_records(venue, competition, season)
        best = answer.data["teams"][0]["team"]
        assert _same_team(best, team), f"Expected {team} to have the best {venue} record, got {best}:\n{answer}"

    def compare_seasons(self, season, other_season, competition):
        return self._ask("compare_seasons", {"season": season, "other_season": other_season,
                                             "competition": competition})

    def confirm_season_comparison(self, season, other_season, competition, average_goals):
        answer = self.compare_seasons(season, other_season, competition)
        actual = tuple(f"{s['average_goals']:.2f}" for s in answer.data["seasons"])
        assert actual == tuple(average_goals), \
            f"Expected average goals {average_goals} for {season} and {other_season}, got {actual}:\n{answer}"

    def derbies(self, season):
        return self._ask("find_derbies", {"season": season})

    def confirm_derbies(self, season, rivalries):
        answer = self.derbies(season)
        actual = sorted(m["rivalry"] for m in answer.data["derbies"])
        assert actual == sorted(rivalries), f"Expected the {season} derbies {rivalries}, got {actual}:\n{answer}"

    # --- players --------------------------------------------------------------------------------------------------

    def player_profile(self, name):
        return self._ask("player_profile", {"name": name})

    def confirm_player_profile(self, name, expected):
        answer = self.player_profile(name)
        player = answer.data["player"]
        assert player, f"Expected to find {name}:\n{answer}"
        for field, value in expected.items():
            actual = player[field]
            matches = _same_team(actual, value) if field == "club" else actual == value
            assert matches, f"Expected {name}'s {field} to be {value}, got {actual}:\n{answer}"

    def confirm_player_not_found(self, name, suggesting):
        answer = self.player_profile(name)
        assert answer.data["player"] is None, f"Expected no player called {name}, got {answer.data['player']}"
        similar = [p["name"] for p in answer.data["similar_players"]]
        assert similar[:len(suggesting)] == suggesting, f"Expected suggestions {suggesting}, got {similar}"
        assert "not in the FIFA dataset" in answer.text, f"The answer should say {name} is not in the data:\n{answer}"

    def search_players(self, criteria):
        return self._ask("search_players", {**criteria, "limit": 50})

    def confirm_top_players(self, criteria, ranked, in_any_order):
        answer = self.search_players(criteria)
        actual = [p["name"] for p in answer.data["players"]]
        if in_any_order:
            assert sorted(actual) == sorted(ranked), f"Expected players {ranked} for {_describe(criteria)}, got {actual}"
        else:
            assert actual[:len(ranked)] == ranked, \
                f"Expected the top players for {_describe(criteria)} to be {ranked}, got {actual[:len(ranked)]}"

    def brazilians_at_brazilian_clubs(self):
        return self._ask("brazilian_players_by_club", {})

    def confirm_brazilians_at_brazilian_clubs(self, clubs):
        answer = self.brazilians_at_brazilian_clubs()
        actual = {c["club"]: (c["players"], f"{c['average_overall']:.1f}") for c in answer.data["clubs"]}
        assert actual == clubs, f"Expected Brazilian players at Brazilian clubs {clubs}, got {actual}:\n{answer}"

    # --- the datasets and responsiveness --------------------------------------------------------------------------

    def confirm_datasets_loaded(self, row_counts):
        from .datasets import FILES
        answer = self._ask("dataset_overview", {})
        loaded = {d["file"]: d["rows"] for d in answer.data["datasets"]}
        for dataset, rows in row_counts.items():
            file_name = FILES[dataset][0]
            assert loaded.get(file_name) == rows, \
                f"Expected the {dataset} dataset ({file_name}) to have {rows} rows, got {loaded.get(file_name)}"

    def confirm_answered(self, question, ask, within_seconds):
        self._connection()
        started = time.perf_counter()
        answer = ask()
        elapsed = time.perf_counter() - started
        assert answer.text.strip(), f"No answer to {question!r}"
        assert elapsed < within_seconds, f"{question!r} took {elapsed:.2f}s (limit {within_seconds}s)"

    # --- plumbing -------------------------------------------------------------------------------------------------

    def _connection(self):
        if self._client is None:
            if self._before_start:
                self._before_start()
            self._client = McpStdioClient(soccer_server_command(self._data_dir), env=soccer_server_environment())
        return self._client

    def _ask(self, tool, arguments):
        arguments = {name: value for name, value in arguments.items() if value is not None}
        result = self._connection().call_tool(tool, arguments)
        text = "\n".join(block.get("text", "") for block in result.get("content", []))
        assert not result.get("isError"), f"The server could not answer ({tool} {arguments}): {text}"
        return Answer(text, result.get("structuredContent") or {})


def _plain(name):
    name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return " ".join(name.replace("-", " ").split())


def _same_team(actual, expected):
    """Specs name clubs the way fans do ("Vasco"); the server may use a fuller name ("Vasco da Gama")."""
    actual, expected = _plain(actual), _plain(expected)
    return actual == expected or actual.startswith(expected + " ")


def _confirm_lines_in_order(text, lines):
    position = 0
    for line in lines:
        found = text.find(line, position)
        assert found >= 0, f"Expected the answer to list {line!r} (in order):\n{text}"
        position = found + len(line)


def _describe(criteria):
    return ", ".join(f"{k}={v}" for k, v in criteria.items() if v not in (None, "any")) or "all"
