"""Brazilian Soccer MCP Server."""
import os
from mcp.server.fastmcp import FastMCP
from data_loader import DataLoader
from query_engine import QueryEngine

_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "kaggle")


def _fmt_match(m: dict) -> str:
    home = m.get("home_team_norm") or m.get("home_team", "?")
    away = m.get("away_team_norm") or m.get("away_team", "?")
    hg = m.get("home_goal", "?")
    ag = m.get("away_goal", "?")
    date = str(m.get("datetime", ""))[:10]
    comp = m.get("competition", "")
    season = m.get("season", "")
    parts = [f"{date}: {home} {hg}-{ag} {away}"]
    if comp:
        parts.append(f"({comp}")
        if season:
            parts[-1] += f" {int(season) if season == season else ''}"
        parts[-1] += ")"
    return " ".join(parts)


def _fmt_player(p: dict) -> str:
    name = p.get("Name", "?")
    overall = p.get("Overall", "?")
    pos = p.get("Position", "?")
    club = p.get("Club", "?")
    nat = p.get("Nationality", "")
    return f"{name} | Rating: {overall} | Pos: {pos} | Club: {club} | Nat: {nat}"


def get_tool_handlers(data_dir: str = _DEFAULT_DATA_DIR) -> dict:
    """Return a dict of callable tool handlers (for testing and server wiring)."""
    loader = DataLoader(data_dir)
    engine = QueryEngine(loader)

    def find_matches(
        team: str | None = None,
        team2: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 20,
    ) -> str:
        results = engine.find_matches(team=team, team2=team2,
                                      competition=competition, season=season, limit=limit)
        if not results:
            return "No matches found for the given criteria."
        lines = [_fmt_match(m) for m in results]
        header = f"Found {len(results)} match(es)"
        if team:
            header += f" for {team}"
        if team2:
            header += f" vs {team2}"
        return header + ":\n" + "\n".join(lines)

    def team_stats(
        team: str,
        season: int | None = None,
        competition: str | None = None,
    ) -> str:
        stats = engine.team_stats(team, season=season, competition=competition)
        if stats["total"] == 0:
            return f"No match data found for {team}."
        win_rate = round(stats["wins"] / stats["total"] * 100, 1) if stats["total"] else 0
        lines = [
            f"Stats for {team}" + (f" ({competition})" if competition else "") + (f" - {season}" if season else ""),
            f"  Matches: {stats['total']}",
            f"  Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}",
            f"  Win rate: {win_rate}%",
            f"  Home wins: {stats['home_wins']}, Away wins: {stats['away_wins']}",
            f"  Goals scored: {stats['goals_scored']}, Goals conceded: {stats['goals_conceded']}",
        ]
        return "\n".join(lines)

    def head_to_head(team1: str, team2: str) -> str:
        h2h = engine.head_to_head(team1, team2)
        if h2h["total"] == 0:
            return f"No head-to-head matches found between {team1} and {team2}."
        lines = [
            f"Head-to-head: {team1} vs {team2}",
            f"  Total matches: {h2h['total']}",
            f"  {team1} wins: {h2h['team1_wins']}",
            f"  {team2} wins: {h2h['team2_wins']}",
            f"  Draws: {h2h['draws']}",
        ]
        return "\n".join(lines)

    def find_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        limit: int = 20,
    ) -> str:
        results = engine.find_players(name=name, nationality=nationality,
                                      club=club, sort_by="Overall", limit=limit)
        if not results:
            return "No players found for the given criteria."
        lines = [_fmt_player(p) for p in results]
        header = f"Found {len(results)} player(s)"
        return header + ":\n" + "\n".join(lines)

    def season_standings(season: int, competition: str = "Brasileirão") -> str:
        table = engine.season_standings(season, competition)
        if not table:
            return f"No data found for {competition} {season}."
        lines = [f"{competition} {season} Standings:"]
        for i, entry in enumerate(table, 1):
            lines.append(
                f"  {i:2}. {entry['team']:30s} | Pts: {entry['points']:3d} | "
                f"W {entry['wins']} D {entry['draws']} L {entry['losses']} | "
                f"GF {entry['goals_for']} GA {entry['goals_against']}"
            )
        return "\n".join(lines)

    def biggest_wins(
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> str:
        results = engine.biggest_wins(competition=competition, season=season, limit=limit)
        if not results:
            return "No matches found."
        lines = [f"Biggest wins" + (f" in {competition}" if competition else "") + ":"]
        for m in results:
            try:
                margin = abs(int(m["home_goal"]) - int(m["away_goal"]))
            except (TypeError, ValueError):
                margin = 0
            lines.append(f"  {_fmt_match(m)} (margin: {margin})")
        return "\n".join(lines)

    def average_goals(competition: str | None = None) -> str:
        avg = engine.average_goals_per_match(competition=competition)
        label = competition or "all competitions"
        return f"Average goals per match in {label}: {avg}"

    def home_win_rate(competition: str | None = None) -> str:
        rate = engine.home_win_rate(competition=competition)
        label = competition or "all competitions"
        return f"Home win rate in {label}: {round(rate * 100, 1)}%"

    def top_scoring_teams(
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> str:
        results = engine.top_scoring_teams(competition=competition, season=season, limit=limit)
        if not results:
            return "No data found."
        lines = [f"Top scoring teams" + (f" in {competition}" if competition else "") + ":"]
        for i, t in enumerate(results, 1):
            lines.append(f"  {i}. {t['team']}: {t['goals']} goals")
        return "\n".join(lines)

    return {
        "find_matches": find_matches,
        "team_stats": team_stats,
        "head_to_head": head_to_head,
        "find_players": find_players,
        "season_standings": season_standings,
        "biggest_wins": biggest_wins,
        "average_goals": average_goals,
        "home_win_rate": home_win_rate,
        "top_scoring_teams": top_scoring_teams,
    }


def build_mcp_server(data_dir: str = _DEFAULT_DATA_DIR) -> FastMCP:
    """Build and return the FastMCP server instance."""
    mcp = FastMCP("Brazilian Soccer Knowledge Graph")
    handlers = get_tool_handlers(data_dir)

    @mcp.tool()
    def find_matches(
        team: str | None = None,
        team2: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 20,
    ) -> str:
        """Find matches filtered by team, competition, or season.

        Args:
            team: Team name (partial match supported, e.g. 'Flamengo')
            team2: Second team for head-to-head search
            competition: 'Brasileirão', 'Copa do Brasil', or 'Copa Libertadores'
            season: Year (e.g. 2019)
            limit: Maximum results to return (default 20)
        """
        return handlers["find_matches"](team=team, team2=team2,
                                        competition=competition, season=season, limit=limit)

    @mcp.tool()
    def team_stats(
        team: str,
        season: int | None = None,
        competition: str | None = None,
    ) -> str:
        """Get win/draw/loss record and goals for a team.

        Args:
            team: Team name (e.g. 'Corinthians')
            season: Filter by season year
            competition: Filter by competition name
        """
        return handlers["team_stats"](team=team, season=season, competition=competition)

    @mcp.tool()
    def head_to_head(team1: str, team2: str) -> str:
        """Get head-to-head record between two teams.

        Args:
            team1: First team name
            team2: Second team name
        """
        return handlers["head_to_head"](team1=team1, team2=team2)

    @mcp.tool()
    def find_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        limit: int = 20,
    ) -> str:
        """Search FIFA player database.

        Args:
            name: Player name (partial match)
            nationality: Nationality (e.g. 'Brazil')
            club: Club name (partial match)
            limit: Maximum results (default 20)
        """
        return handlers["find_players"](name=name, nationality=nationality,
                                        club=club, limit=limit)

    @mcp.tool()
    def season_standings(season: int, competition: str = "Brasileirão") -> str:
        """Calculate season standings from match results.

        Args:
            season: Year (e.g. 2019)
            competition: Competition name (default 'Brasileirão')
        """
        return handlers["season_standings"](season=season, competition=competition)

    @mcp.tool()
    def biggest_wins(
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> str:
        """List matches with the biggest goal margins.

        Args:
            competition: Filter by competition
            season: Filter by season year
            limit: Number of results (default 10)
        """
        return handlers["biggest_wins"](competition=competition, season=season, limit=limit)

    @mcp.tool()
    def average_goals(competition: str | None = None) -> str:
        """Calculate average goals per match.

        Args:
            competition: Filter by competition (optional)
        """
        return handlers["average_goals"](competition=competition)

    @mcp.tool()
    def home_win_rate(competition: str | None = None) -> str:
        """Calculate home team win rate.

        Args:
            competition: Filter by competition (optional)
        """
        return handlers["home_win_rate"](competition=competition)

    @mcp.tool()
    def top_scoring_teams(
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> str:
        """List teams by total goals scored.

        Args:
            competition: Filter by competition
            season: Filter by season year
            limit: Number of teams to return (default 10)
        """
        return handlers["top_scoring_teams"](competition=competition, season=season, limit=limit)

    return mcp


if __name__ == "__main__":
    mcp_server = build_mcp_server()
    mcp_server.run()
