import math

from mcp.server.fastmcp import FastMCP

from brazilian_soccer_mcp import queries
from brazilian_soccer_mcp.data_loader import load_matches, load_players

mcp = FastMCP("brazilian-soccer")


def _format_goal(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "?"
    return str(int(value))


def _match_line(m: dict) -> str:
    score = f"{_format_goal(m['home_goal'])}-{_format_goal(m['away_goal'])}"
    return (
        f"{m['date']}: {m['home_team_display']} {score} "
        f"{m['away_team_display']} ({m['competition']})"
    )


@mcp.tool()
def find_matches(team: str, opponent: str | None = None, competition: str | None = None, season: int | None = None) -> str:
    """Find matches for a team, optionally filtered by opponent, competition, or season."""
    matches = queries.find_matches(load_matches(), team=team, opponent=opponent, competition=competition, season=season)
    if not matches:
        return f"No matches found for {team}."
    lines = [_match_line(m) for m in matches]
    return "\n".join(lines)


@mcp.tool()
def head_to_head(team_a: str, team_b: str, competition: str | None = None, season: int | None = None) -> str:
    """Compare two teams head-to-head across their match history."""
    summary = queries.head_to_head(load_matches(), team_a, team_b, competition=competition, season=season)
    header = f"{team_a} vs {team_b} ({summary['total_matches']} matches in dataset)"
    record = f"{team_a} wins: {summary['team_a_wins']}, {team_b} wins: {summary['team_b_wins']}, Draws: {summary['draws']}"
    lines = [_match_line(m) for m in summary["matches"]]
    return "\n".join([header, record, ""] + lines)


@mcp.tool()
def team_record(team: str, competition: str | None = None, season: int | None = None, venue: str | None = None) -> str:
    """Get win/draw/loss record and goals for/against for a team."""
    record = queries.team_record(load_matches(), team, competition=competition, season=season, venue=venue)
    return (
        f"{team} record:\n"
        f"Matches: {record['matches']}\n"
        f"Wins: {record['wins']}, Draws: {record['draws']}, Losses: {record['losses']}\n"
        f"Goals For: {record['goals_for']}, Goals Against: {record['goals_against']}\n"
        f"Win rate: {record['win_rate'] * 100:.1f}%"
    )


@mcp.tool()
def standings(competition: str = "Brasileirao", season: int | None = None) -> str:
    """Calculate league standings for a competition and season from match results."""
    table = queries.standings(load_matches(), competition=competition, season=season)
    lines = []
    for i, row in enumerate(table, start=1):
        suffix = " - Champion" if i == 1 else ""
        lines.append(
            f"{i}. {row['team_display']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L){suffix}"
        )
    return "\n".join(lines) if lines else "No matches found for the given filters."


@mcp.tool()
def biggest_wins(competition: str | None = None, season: int | None = None, n: int = 10) -> str:
    """List the biggest victories (by goal margin) in the dataset."""
    wins = queries.biggest_wins(load_matches(), competition=competition, season=season, n=n)
    if not wins:
        return "No matches found for the given filters."
    lines = [f"{i}. {_match_line(m)}" for i, m in enumerate(wins, start=1)]
    return "\n".join(lines)


@mcp.tool()
def average_goals_per_match(competition: str | None = None, season: int | None = None) -> str:
    """Calculate the average number of goals scored per match."""
    avg = queries.average_goals_per_match(load_matches(), competition=competition, season=season)
    return f"Average goals per match: {avg:.2f}"


@mcp.tool()
def home_win_rate(competition: str | None = None, season: int | None = None) -> str:
    """Calculate the percentage of matches won by the home team."""
    rate = queries.home_win_rate(load_matches(), competition=competition, season=season)
    return f"Home win rate: {rate * 100:.1f}%"


@mcp.tool()
def search_players(name: str | None = None, nationality: str | None = None, club: str | None = None, position: str | None = None) -> str:
    """Search FIFA player data by name, nationality, club, or position."""
    players = queries.search_players(load_players(), name=name, nationality=nationality, club=club, position=position)
    if not players:
        return "No players found."
    lines = [
        f"{p['name']} - Overall: {p['overall']}, Position: {p['position']}, Club: {p['club']}, Nationality: {p['nationality']}"
        for p in players
    ]
    return "\n".join(lines)


@mcp.tool()
def top_players(n: int = 10, nationality: str | None = None, club: str | None = None) -> str:
    """Get the top-rated players, optionally filtered by nationality or club."""
    players = queries.top_players(load_players(), n=n, nationality=nationality, club=club)
    if not players:
        return "No players found."
    lines = [
        f"{i}. {p['name']} - Overall: {p['overall']}, Position: {p['position']}, Club: {p['club']}"
        for i, p in enumerate(players, start=1)
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
