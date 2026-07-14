"""BDD specs for brazilian_soccer_mcp.server: the MCP tools themselves,
exercised end-to-end through the same call_tool interface an LLM client
uses, matching the example questions from TASK.md's "Sample Questions"
table.
"""

import asyncio
import re

from brazilian_soccer_mcp.server import mcp

_RANKED_LINE_RE = re.compile(r"^\d+\.\s")


def call_tool(name: str, arguments: dict) -> str:
    result = asyncio.run(mcp.call_tool(name, arguments))
    return result[0][0].text


class TestToolRegistration:
    def test_given_the_server_when_started_then_every_required_capability_has_a_tool(self):
        # Given the required capability categories from TASK.md (match, team,
        # player, competition and statistical queries)
        tool_names = {t.name for t in asyncio.run(mcp.list_tools())}
        # When the server's registered tools are inspected
        # Then each category has at least one corresponding tool
        assert "search_matches" in tool_names
        assert "get_team_record" in tool_names
        assert "search_players" in tool_names
        assert "get_standings" in tool_names
        assert "get_statistics" in tool_names


class TestMatchQueryTools:
    def test_given_flamengo_and_corinthians_when_search_matches_is_called_then_a_formatted_history_is_returned(self):
        # Given "When did Flamengo last play Corinthians? What was the score?"
        text = call_tool("search_matches", {"team": "Flamengo", "opponent": "Corinthians"})
        # When the tool response is inspected
        # Then it reads as a formatted match list, most recent first
        assert "Flamengo" in text and "Corinthians" in text
        assert text.split("\n")[0].startswith("- ")

    def test_given_no_matching_criteria_when_search_matches_is_called_then_a_friendly_empty_message_is_returned(self):
        # Given a search with an impossible date range
        text = call_tool("search_matches", {"team": "Flamengo", "date_from": "1800-01-01", "date_to": "1800-01-02"})
        # When the tool response is inspected
        # Then a friendly "no results" message is returned rather than an empty string
        assert "No matches found" in text


class TestTeamQueryTools:
    def test_given_corinthians_2022_home_when_get_team_record_is_called_then_a_formatted_record_is_returned(self):
        # Given "What is Corinthians' home record in 2022?"
        text = call_tool(
            "get_team_record", {"team": "Corinthians", "season": 2022, "competition": "Brasileirao", "venue": "home"}
        )
        # When the tool response is inspected
        # Then it reports matches, wins/draws/losses and a win rate
        assert "Matches:" in text
        assert "Win rate:" in text

    def test_given_palmeiras_and_santos_when_compare_teams_is_called_then_both_records_and_h2h_are_present(self):
        # Given "Compare Palmeiras and Santos head-to-head"
        text = call_tool("compare_teams", {"team_a": "Palmeiras", "team_b": "Santos"})
        # When the tool response is inspected
        # Then both team records and their head-to-head summary are included
        assert "Palmeiras" in text and "Santos" in text
        assert "Head-to-head in dataset" in text

    def test_given_an_unknown_team_when_get_team_record_is_called_then_a_readable_error_message_is_returned(self):
        # Given a nonsense team name reaching the tool boundary
        text = call_tool("get_team_record", {"team": "Not A Real Club"})
        # When the tool response is inspected
        # Then a readable error string is returned instead of a stack trace
        assert "No team found" in text


class TestPlayerQueryTools:
    def test_given_a_player_name_when_search_players_is_called_then_a_formatted_result_is_returned(self):
        # Given "Who is Neymar Jr?"
        text = call_tool("search_players", {"name": "Neymar"})
        # When the tool response is inspected
        # Then it includes the player's overall rating and club
        assert "Neymar" in text
        assert "Overall:" in text

    def test_given_brazil_nationality_when_search_players_is_called_then_a_ranked_list_is_returned(self):
        # Given "Find all Brazilian players in the dataset"
        text = call_tool("search_players", {"nationality": "Brazil", "limit": 5})
        # When the tool response is inspected
        # Then a numbered list of players is returned
        assert text.startswith("1. ")


class TestCompetitionQueryTools:
    def test_given_the_2019_brasileirao_when_get_champion_is_called_then_flamengo_is_named(self):
        # Given "Who won the 2019 Brasileirao?"
        text = call_tool("get_champion", {"competition": "Brasileirao", "season": 2019})
        # When the tool response is inspected
        # Then Flamengo is named as champion
        assert "Flamengo" in text

    def test_given_the_2020_brasileirao_when_get_relegated_teams_is_called_then_four_teams_are_listed(self):
        # Given "Which teams were relegated in 2020?"
        text = call_tool("get_relegated_teams", {"competition": "Brasileirao", "season": 2020, "count": 4})
        # When the tool response is inspected
        # Then exactly 4 ranked team rows are listed
        lines = [line for line in text.split("\n") if _RANKED_LINE_RE.match(line)]
        assert len(lines) == 4


class TestStatisticalAnalysisTools:
    def test_given_the_brasileirao_when_get_statistics_is_called_then_average_goals_and_home_win_rate_are_reported(
        self,
    ):
        # Given "What's the average goals per match in the Brasileirao?"
        text = call_tool("get_statistics", {"competition": "Brasileirao"})
        # When the tool response is inspected
        # Then both requested statistics are present
        assert "Average goals per match:" in text
        assert "Home win rate:" in text

    def test_given_the_full_dataset_when_get_biggest_wins_is_called_then_a_ranked_list_of_blowouts_is_returned(self):
        # Given "Show me the biggest wins in the dataset"
        text = call_tool("get_biggest_wins", {"limit": 5})
        # When the tool response is inspected
        # Then a numbered list of lopsided results is returned
        assert text.startswith("1. ")
