"""
The Brazilian Soccer MCP server: the system's public interface.

Exposes the knowledge base as MCP tools an LLM can call to answer natural
language questions about Brazilian football - matches, teams, competitions,
statistics and players - from the provided Kaggle datasets.

Every tool returns:
  - text content: a formatted, human-readable answer, and
  - structured content: the same facts as JSON, for precise follow-up.
Questions the data can't answer (unknown team, malformed date, ...) come back
as tool errors with a helpful message, so the LLM can correct itself.

Run:  python -m brazilian_soccer_mcp [--data-dir data/kaggle]     (stdio transport)
The data directory can also be set with BRAZILIAN_SOCCER_DATA_DIR.
"""
import argparse
import os
import pathlib
import sys

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult, TextContent

from .knowledge import QueryError, SoccerKnowledge

DEFAULT_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "kaggle"

INSTRUCTIONS = """Answers questions about Brazilian football from Kaggle datasets: Brasileirão Série A
(2003-2023), Série B/C (2014-2023), Copa do Brasil (2012-2023), Copa Libertadores (2013-2022) and FIFA 19
player ratings. Team names are matched leniently (accents, state suffixes like '-SP', full club names).
Competitions: 'Brasileirão' (Série A), 'Série B', 'Série C', 'Copa do Brasil', 'Libertadores'.
Dates: YYYY-MM-DD or DD/MM/YYYY."""


def build_server(knowledge):
    server = MCPServer("brazilian-soccer", instructions=INSTRUCTIONS, version="1.0.0")

    def answer(query, *args, **kwargs):
        try:
            result = query(*args, **kwargs)
        except QueryError as error:
            raise ToolError(str(error)) from None
        return CallToolResult(content=[TextContent(type="text", text=result.text)], structured_content=result.data)

    @server.tool()
    def find_matches(team: str | None = None, opponent: str | None = None, venue: str = "any",
                     competition: str | None = None, season: int | None = None, date_from: str | None = None,
                     date_to: str | None = None, stage: str | None = None, limit: int = 20) -> CallToolResult:
        """Find matches, most recent first. Filter by team, opponent (head-to-head), venue of the team
        ('home', 'away' or 'any'), competition, season, date range (YYYY-MM-DD or DD/MM/YYYY) and knockout
        stage ('final', 'semifinals', 'quarterfinals', 'round of 16', 'group stage').
        E.g. 'Show me all Flamengo vs Fluminense matches', 'What matches did Palmeiras play in 2022?',
        'Find all Copa do Brasil finals'."""
        return answer(knowledge.find_matches, team=team, opponent=opponent, venue=venue, competition=competition,
                      season=season, date_from=date_from, date_to=date_to, stage=stage, limit=limit)

    @server.tool()
    def head_to_head(team: str, opponent: str, competition: str | None = None) -> CallToolResult:
        """Head-to-head record between two teams: wins, draws, goals, recent meetings and the last meeting.
        E.g. 'Compare Palmeiras and Santos head-to-head', 'When did Flamengo last play Corinthians?'"""
        return answer(knowledge.head_to_head, team, opponent, competition=competition)

    @server.tool()
    def team_record(team: str, season: int | None = None, competition: str | None = None,
                    venue: str = "all") -> CallToolResult:
        """A team's record: matches, wins, draws, losses, goals for/against and win rate, optionally for one
        season, competition and venue ('home', 'away' or 'all'). E.g. 'What is Corinthians' home record in 2022?'"""
        return answer(knowledge.team_record, team, season=season, competition=competition, venue=venue)

    @server.tool()
    def team_competitions(team: str) -> CallToolResult:
        """Which competitions a team has played in, with match counts and seasons."""
        return answer(knowledge.team_competitions, team)

    @server.tool()
    def club_profile(team: str) -> CallToolResult:
        """Everything known about a club across all datasets: match record, competitions and FIFA squad."""
        return answer(knowledge.club_profile, team)

    @server.tool()
    def league_table(season: int, competition: str = "Brasileirão") -> CallToolResult:
        """Final league standings for a season, calculated from match results (3 points a win), with the
        champion and relegated teams. E.g. 'Who won the 2019 Brasileirão?', 'Which teams were relegated in 2020?'"""
        return answer(knowledge.league_table, season, competition)

    @server.tool()
    def top_scoring_teams(season: int | None = None, competition: str = "Brasileirão",
                          limit: int = 10) -> CallToolResult:
        """Teams ranked by goals scored. E.g. 'Which team scored the most goals in Serie A 2022?'"""
        return answer(knowledge.top_scoring_teams, season=season, competition=competition, limit=limit)

    @server.tool()
    def knockout_bracket(competition: str, season: int) -> CallToolResult:
        """Knockout stages of a cup season (round of 16 to final) with ties, legs and aggregate scores.
        E.g. 'Show the 2018 Copa Libertadores bracket'."""
        return answer(knowledge.knockout_bracket, competition, season)

    @server.tool()
    def competition_summary(competition: str | None = None, season: int | None = None) -> CallToolResult:
        """Aggregate statistics: matches, goals, average goals per match, home win / draw / away win rates.
        E.g. 'What's the average goals per match in the Brasileirão?'"""
        return answer(knowledge.competition_summary, competition=competition, season=season)

    @server.tool()
    def compare_seasons(season: int, other_season: int, competition: str = "Brasileirão") -> CallToolResult:
        """Compare two seasons of a competition: goals, results split and champion.
        E.g. 'Compare the 2018 and 2019 seasons'."""
        return answer(knowledge.compare_seasons, season, other_season, competition)

    @server.tool()
    def biggest_wins(competition: str | None = None, season: int | None = None, team: str | None = None,
                     limit: int = 10) -> CallToolResult:
        """The biggest victories by goal margin. E.g. 'Show me the biggest wins in the dataset'."""
        return answer(knowledge.biggest_wins, competition=competition, season=season, team=team, limit=limit)

    @server.tool()
    def best_records(venue: str = "all", competition: str | None = None, season: int | None = None,
                     min_matches: int | None = None, limit: int = 10) -> CallToolResult:
        """Teams ranked by win rate, at home, away or overall. Teams need a minimum number of matches
        (default: a quarter of the most any team played). E.g. 'Which team has the best away record?'"""
        return answer(knowledge.best_records, venue=venue, competition=competition, season=season,
                      min_matches=min_matches, limit=limit)

    @server.tool()
    def find_derbies(season: int | None = None, competition: str | None = None,
                     rivalry: str | None = None) -> CallToolResult:
        """Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, Choque-Rei, Clássico Mineiro,
        Ba-Vi, Atletiba, ...). E.g. 'Show me all derbies in 2022'."""
        return answer(knowledge.find_derbies, season=season, competition=competition, rivalry=rivalry)

    @server.tool()
    def search_players(name: str | None = None, nationality: str | None = None, club: str | None = None,
                       position: str | None = None, min_overall: int | None = None,
                       limit: int = 20) -> CallToolResult:
        """Search the FIFA player database, highest rated first. Position may be a code (ST, GK, CB, ...) or a
        group ('forward', 'midfielder', 'defender', 'goalkeeper'). E.g. 'Find all Brazilian players',
        'Who are the highest-rated players at Grêmio?', 'Show me all forwards from Santos'."""
        return answer(knowledge.search_players, name=name, nationality=nationality, club=club, position=position,
                      min_overall=min_overall, limit=limit)

    @server.tool()
    def player_profile(name: str) -> CallToolResult:
        """A player's full profile: club, nationality, position, ratings and attributes.
        E.g. 'Who is Gabriel Barbosa?'"""
        return answer(knowledge.player_profile, name)

    @server.tool()
    def brazilian_players_by_club(nationality: str = "Brazil", brazilian_clubs_only: bool = True) -> CallToolResult:
        """How many players of a nationality (default Brazilian) each club has, with average rating -
        by default only clubs that play in the Brazilian league."""
        return answer(knowledge.brazilian_players_by_club, nationality=nationality,
                      brazilian_clubs_only=brazilian_clubs_only)

    @server.tool()
    def dataset_overview() -> CallToolResult:
        """Which datasets are loaded, their row counts, and the seasons covered for each competition."""
        return answer(knowledge.dataset_overview)

    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server (stdio)")
    parser.add_argument("--data-dir", default=os.environ.get("BRAZILIAN_SOCCER_DATA_DIR", str(DEFAULT_DATA_DIR)),
                        help="directory containing the Kaggle CSV files")
    args = parser.parse_args(argv)
    knowledge = SoccerKnowledge(args.data_dir)
    for dataset in knowledge.datasets:
        if not dataset.loaded:
            print(f"warning: {dataset.file}: {dataset.problem}", file=sys.stderr)
    build_server(knowledge).run("stdio")


if __name__ == "__main__":
    main()
