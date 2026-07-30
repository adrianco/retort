"""Brazilian soccer data service and a small dependency-free MCP stdio server.

The service loads the six CSV files supplied with this project and presents a
single, normalized view of matches.  It deliberately uses only the Python
standard library so a fresh checkout can run it without a package install.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator


DATA_DIR = Path(__file__).parent / "data" / "kaggle"


def normalized(value: object) -> str:
    """Return a comparison key that accepts accents, case, and state suffixes."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower().strip()
    text = re.sub(r"\s*-\s*(?:ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to|uru|arg|bol|chi|col|ecu|par|per|ven)\s*$", "", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    aliases = {
        "sport club corinthians paulista": "corinthians",
        "sao paulo futebol clube": "sao paulo",
        "sao paulo fc": "sao paulo",
        "club de regatas do flamengo": "flamengo",
        "sociedade esportiva palmeiras": "palmeiras",
        "fluminense football club": "fluminense",
        "santos futebol clube": "santos",
        "gremio foot ball porto alegrense": "gremio",
        "sport club internacional": "internacional",
        "club athletico paranaense": "athletico paranaense",
    }
    return aliases.get(text, text)


def parse_date(value: object) -> date | None:
    value = str(value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except ValueError:
            pass
    return None


def integer(value: object) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class Match:
    date: str | None
    home_team: str
    away_team: str
    home_goal: int | None
    away_goal: int | None
    season: int | None
    competition: str
    stage: str | None = None
    round: str | None = None
    source: str = ""
    extras: dict[str, Any] | None = None

    def result(self) -> str:
        home = "?" if self.home_goal is None else str(self.home_goal)
        away = "?" if self.away_goal is None else str(self.away_goal)
        return f"{self.home_team} {home}-{away} {self.away_team}"


class SoccerData:
    """In-memory, read-only access to the supplied football CSVs."""

    FILES = (
        ("Brasileirao_Matches.csv", "Brasileirão", "standard"),
        ("Brazilian_Cup_Matches.csv", "Copa do Brasil", "standard"),
        ("Libertadores_Matches.csv", "Libertadores", "standard"),
        ("BR-Football-Dataset.csv", None, "extended"),
        ("novo_campeonato_brasileiro.csv", "Brasileirão", "historic"),
    )

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.matches: list[Match] = []
        self.players: list[dict[str, Any]] = []
        self._loaded = False

    def load(self) -> "SoccerData":
        if self._loaded:
            return self
        for filename, competition, kind in self.FILES:
            path = self.data_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Required dataset is missing: {path}")
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    match = self._row_to_match(row, filename, competition, kind)
                    if match:
                        self.matches.append(match)
        path = self.data_dir / "fifa_data.csv"
        if not path.exists():
            raise FileNotFoundError(f"Required dataset is missing: {path}")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                self.players.append({key: value for key, value in row.items() if key})
        self._loaded = True
        return self

    @staticmethod
    def _row_to_match(row: dict[str, str], source: str, competition: str | None, kind: str) -> Match | None:
        if kind == "extended":
            raw_date, home, away = row.get("date"), row.get("home"), row.get("away")
            competition = row.get("tournament") or "Unknown"
            goals, away_goals = row.get("home_goal"), row.get("away_goal")
            season = parse_date(raw_date).year if parse_date(raw_date) else None
            stage = round_ = None
            extras = {key: row.get(key) for key in ("home_corner", "away_corner", "home_shots", "away_shots", "total_corners")}
        elif kind == "historic":
            raw_date, home, away = row.get("Data"), row.get("Equipe_mandante"), row.get("Equipe_visitante")
            goals, season, round_ = row.get("Gols_mandante"), row.get("Ano"), row.get("Rodada")
            # Keep explicit values so a blank score remains unknown.
            away_goals, stage = row.get("Gols_visitante"), None
            extras = {"stadium": row.get("Arena"), "winner": row.get("Vencedor")}
            if not home or not away:
                return None
            return Match(parse_date(raw_date).isoformat() if parse_date(raw_date) else None, home, away,
                         integer(goals), integer(away_goals), integer(season), competition or "Brasileirão",
                         stage, round_, source, extras)
        else:
            raw_date, home, away = row.get("datetime"), row.get("home_team"), row.get("away_team")
            goals, away_goals, season = row.get("home_goal"), row.get("away_goal"), row.get("season")
            stage, round_, extras = row.get("stage"), row.get("round"), {}
        if not home or not away:
            return None
        parsed = parse_date(raw_date)
        return Match(parsed.isoformat() if parsed else None, home, away, integer(goals), integer(away_goals),
                     integer(season), competition or "Unknown", stage, round_, source, extras)

    def search_matches(self, team: str | None = None, opponent: str | None = None,
                       competition: str | None = None, season: int | str | None = None,
                       start_date: str | None = None, end_date: str | None = None,
                       stage: str | None = None, limit: int = 100) -> list[Match]:
        self.load()
        team_key, opponent_key, competition_key = normalized(team), normalized(opponent), normalized(competition)
        start, end = parse_date(start_date), parse_date(end_date)
        season_num = integer(season)
        def includes(match: Match) -> bool:
            home, away = normalized(match.home_team), normalized(match.away_team)
            if team_key and team_key not in (home, away): return False
            if opponent_key and opponent_key not in (home, away): return False
            if team_key and opponent_key and {team_key, opponent_key} != {home, away}: return False
            if competition_key and competition_key not in normalized(match.competition): return False
            if season_num is not None and match.season != season_num: return False
            match_date = parse_date(match.date)
            if start and (not match_date or match_date < start): return False
            if end and (not match_date or match_date > end): return False
            if stage and normalized(stage) not in normalized(match.stage): return False
            return True
        matches = [match for match in self.matches if includes(match)]
        return sorted(matches, key=lambda item: item.date or "", reverse=True)[:max(0, min(limit, 1000))]

    def team_statistics(self, team: str, *, season: int | str | None = None,
                        competition: str | None = None, venue: str = "all") -> dict[str, Any]:
        key = normalized(team)
        matches = self.search_matches(team=team, season=season, competition=competition, limit=1000)
        if venue not in {"all", "home", "away"}:
            raise ValueError("venue must be 'all', 'home', or 'away'")
        if venue != "all":
            matches = [m for m in matches if (normalized(m.home_team) == key) == (venue == "home")]
        stats = {"team": team, "matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}
        for match in matches:
            if match.home_goal is None or match.away_goal is None: continue
            stats["matches"] += 1
            is_home = normalized(match.home_team) == key
            own, other = (match.home_goal, match.away_goal) if is_home else (match.away_goal, match.home_goal)
            stats["goals_for"] += own; stats["goals_against"] += other
            stats["wins" if own > other else "losses" if own < other else "draws"] += 1
        stats["points"] = stats["wins"] * 3 + stats["draws"]
        stats["win_rate"] = round(100 * stats["wins"] / stats["matches"], 1) if stats["matches"] else 0.0
        return stats

    def head_to_head(self, team_a: str, team_b: str, **filters: Any) -> dict[str, Any]:
        matches = self.search_matches(team=team_a, opponent=team_b, limit=1000, **filters)
        result = {"team_a": team_a, "team_b": team_b, "matches": len(matches), "team_a_wins": 0, "team_b_wins": 0, "draws": 0, "matches_data": [asdict(m) for m in matches]}
        a_key = normalized(team_a)
        for match in matches:
            if match.home_goal is None or match.away_goal is None: continue
            if match.home_goal == match.away_goal: result["draws"] += 1
            elif (match.home_goal > match.away_goal) == (normalized(match.home_team) == a_key): result["team_a_wins"] += 1
            else: result["team_b_wins"] += 1
        return result

    def standings(self, season: int | str, competition: str = "Brasileirão") -> list[dict[str, Any]]:
        table: dict[str, dict[str, Any]] = {}
        # Prefer the dedicated, non-duplicated season file for Brasileirão standings.
        source = "novo_campeonato_brasileiro.csv" if normalized(competition) == "brasileirao" and 2003 <= (integer(season) or 0) <= 2019 else None
        matches = self.search_matches(competition=competition, season=season, limit=1000)
        if source: matches = [m for m in matches if m.source == source]
        for match in matches:
            if match.home_goal is None or match.away_goal is None: continue
            for name in (match.home_team, match.away_team):
                table.setdefault(normalized(name), {"team": name, "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0})
            home, away = table[normalized(match.home_team)], table[normalized(match.away_team)]
            home["played"] += 1; away["played"] += 1
            home["goals_for"] += match.home_goal; home["goals_against"] += match.away_goal
            away["goals_for"] += match.away_goal; away["goals_against"] += match.home_goal
            if match.home_goal > match.away_goal: home["wins"] += 1; away["losses"] += 1; home["points"] += 3
            elif match.home_goal < match.away_goal: away["wins"] += 1; home["losses"] += 1; away["points"] += 3
            else: home["draws"] += 1; away["draws"] += 1; home["points"] += 1; away["points"] += 1
        rows = list(table.values())
        for row in rows: row["goal_difference"] = row["goals_for"] - row["goals_against"]
        # Brasileirão's first tiebreaker is wins, followed by goal difference
        # and goals scored (rather than goal difference alone).
        return sorted(rows, key=lambda row: (-row["points"], -row["wins"], -row["goal_difference"], -row["goals_for"], row["team"]))

    def search_players(self, name: str | None = None, nationality: str | None = None,
                       club: str | None = None, position: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        self.load()
        filters = {"Name": normalized(name), "Nationality": normalized(nationality), "Club": normalized(club), "Position": normalized(position)}
        result = []
        for player in self.players:
            if all(not needle or needle in normalized(player.get(field)) for field, needle in filters.items()):
                result.append({field: player.get(field) for field in ("ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position", "Jersey Number")})
        return sorted(result, key=lambda row: integer(row.get("Overall")) or 0, reverse=True)[:max(0, min(limit, 1000))]

    def aggregate_statistics(self, competition: str | None = None, season: int | str | None = None) -> dict[str, Any]:
        matches = [m for m in self.search_matches(competition=competition, season=season, limit=1000) if m.home_goal is not None and m.away_goal is not None]
        total = len(matches); home_wins = sum(m.home_goal > m.away_goal for m in matches); draws = sum(m.home_goal == m.away_goal for m in matches)
        goals = sum(m.home_goal + m.away_goal for m in matches)
        biggest = sorted(matches, key=lambda m: abs(m.home_goal - m.away_goal), reverse=True)[:10]
        return {"matches": total, "goals": goals, "goals_per_match": round(goals / total, 2) if total else 0.0,
                "home_win_rate": round(100 * home_wins / total, 1) if total else 0.0, "draw_rate": round(100 * draws / total, 1) if total else 0.0,
                "biggest_wins": [asdict(m) for m in biggest]}


TOOLS = [
    {"name": "search_matches", "description": "Find matches by team, opponent, competition, season, date range, or stage.", "inputSchema": {"type": "object", "properties": {"team": {"type": "string"}, "opponent": {"type": "string"}, "competition": {"type": "string"}, "season": {"type": "integer"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "stage": {"type": "string"}, "limit": {"type": "integer", "default": 100}}}},
    {"name": "team_statistics", "description": "Calculate a team's wins, draws, losses, and goals.", "inputSchema": {"type": "object", "required": ["team"], "properties": {"team": {"type": "string"}, "season": {"type": "integer"}, "competition": {"type": "string"}, "venue": {"enum": ["all", "home", "away"]}}}},
    {"name": "head_to_head", "description": "Compare two teams' results against one another.", "inputSchema": {"type": "object", "required": ["team_a", "team_b"], "properties": {"team_a": {"type": "string"}, "team_b": {"type": "string"}, "season": {"type": "integer"}, "competition": {"type": "string"}}}},
    {"name": "get_standings", "description": "Calculate a league table from match results.", "inputSchema": {"type": "object", "required": ["season"], "properties": {"season": {"type": "integer"}, "competition": {"type": "string", "default": "Brasileirão"}}}},
    {"name": "search_players", "description": "Search FIFA players by name, nationality, club, or position.", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "nationality": {"type": "string"}, "club": {"type": "string"}, "position": {"type": "string"}, "limit": {"type": "integer", "default": 100}}}},
    {"name": "aggregate_statistics", "description": "Return goals, home-win rates, and biggest wins.", "inputSchema": {"type": "object", "properties": {"competition": {"type": "string"}, "season": {"type": "integer"}}}},
]


def call_tool(data: SoccerData, name: str, arguments: dict[str, Any]) -> Any:
    methods = {"search_matches": data.search_matches, "team_statistics": data.team_statistics, "head_to_head": data.head_to_head, "get_standings": data.standings, "search_players": data.search_players, "aggregate_statistics": data.aggregate_statistics}
    if name not in methods: raise ValueError(f"Unknown tool: {name}")
    outcome = methods[name](**arguments)
    if isinstance(outcome, list) and outcome and isinstance(outcome[0], Match): return [asdict(item) for item in outcome]
    return outcome


def serve() -> None:
    """Serve the MCP JSON-RPC protocol over stdin/stdout (one JSON object/line)."""
    data = SoccerData()
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method, request_id = request.get("method"), request.get("id")
            if method == "initialize": result = {"protocolVersion": request.get("params", {}).get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}}, "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}}
            elif method == "tools/list": result = {"tools": TOOLS}
            elif method == "tools/call":
                params = request.get("params", {}); value = call_tool(data, params["name"], params.get("arguments", {}))
                result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, default=str)}], "structuredContent": value}
            elif method == "notifications/initialized": continue
            else: raise ValueError(f"Unsupported method: {method}")
            if request_id is not None: print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}, ensure_ascii=False), flush=True)
        except Exception as exc:
            if 'request_id' in locals() and request_id is not None: print(json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(exc)}}), flush=True)


if __name__ == "__main__":
    serve()
