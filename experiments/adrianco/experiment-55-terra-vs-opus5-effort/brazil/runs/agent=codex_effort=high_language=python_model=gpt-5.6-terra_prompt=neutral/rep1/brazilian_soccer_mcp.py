"""Brazilian soccer knowledge-graph MCP server.

The module deliberately uses only the Python standard library.  ``SoccerData``
is useful directly from Python and ``main`` exposes the same operations as MCP
tools over the stdio JSON-RPC transport.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional


DATA_DIR = Path(__file__).parent / "data" / "kaggle"


def normalized(value: object) -> str:
    """Return an accent/case/punctuation insensitive value for matching."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


_TEAM_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "corinthians paulista": "corinthians",
    "club de regatas do flamengo": "flamengo",
    "flamengo rj": "flamengo",
    "sociedade esportiva palmeiras": "palmeiras",
    "sao paulo futebol clube": "sao paulo",
    "sao paulo fc": "sao paulo",
    "fluminense football club": "fluminense",
    "gremio foot ball porto alegrense": "gremio",
    "club athletico paranaense": "athletico pr",
    "atletico paranaense": "athletico pr",
    "atletico pr": "athletico pr",
    "cr vasco da gama": "vasco",
    "vasco da gama": "vasco",
    "botafogo futebol e regatas": "botafogo",
    "sport recife": "sport",
}


def canonical_team(value: object) -> str:
    """Normalize known variants, including the ``-SP`` style state suffix."""
    raw = str(value or "").strip()
    raw = re.sub(r"\s*-\s*[A-Z]{2}$", "", raw)
    key = normalized(raw)
    return _TEAM_ALIASES.get(key, key)


def _as_int(value: object) -> Optional[int]:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


def _parse_date(value: object) -> Optional[date]:
    text = str(value or "").strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    return None


def _competition_key(value: object) -> str:
    term = normalized(value)
    if "libertadores" in term:
        return "libertadores"
    if "copa" in term and "brasil" in term:
        return "copa do brasil"
    if any(part in term for part in ("brasileirao", "brasileiro", "serie a")):
        return "brasileirao"
    return term


@dataclass(frozen=True)
class Match:
    date: Optional[date]
    home_team: str
    away_team: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    competition: str
    season: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    source: str = ""
    venue: Optional[str] = None
    corners: Optional[int] = None
    shots_home: Optional[int] = None
    shots_away: Optional[int] = None

    @property
    def home_key(self) -> str:
        return canonical_team(self.home_team)

    @property
    def away_key(self) -> str:
        return canonical_team(self.away_team)

    def public(self) -> dict[str, Any]:
        result = asdict(self)
        result["date"] = self.date.isoformat() if self.date else None
        result["home_team_key"] = self.home_key
        result["away_team_key"] = self.away_key
        return result


class SoccerData:
    """In-memory, normalized view of all supplied Kaggle data files."""

    def __init__(self, data_dir: Path | str = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.matches: list[Match] = []
        self.players: list[dict[str, Any]] = []
        self._load()

    def _rows(self, filename: str) -> Iterable[dict[str, str]]:
        path = self.data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Required dataset is missing: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)

    def _add_matches(self, filename: str, competition: str, mapper: Any) -> None:
        for row in self._rows(filename):
            self.matches.append(mapper(row, competition, filename))

    def _load(self) -> None:
        self._add_matches("Brasileirao_Matches.csv", "Brasileirao", self._standard_match)
        self._add_matches("Brazilian_Cup_Matches.csv", "Copa do Brasil", self._standard_match)
        self._add_matches("Libertadores_Matches.csv", "Libertadores", self._standard_match)
        self._add_matches("BR-Football-Dataset.csv", "", self._extended_match)
        self._add_matches("novo_campeonato_brasileiro.csv", "Brasileirao", self._historical_match)
        for row in self._rows("fifa_data.csv"):
            self.players.append({
                "id": _as_int(row.get("ID")), "name": row.get("Name", ""),
                "age": _as_int(row.get("Age")), "nationality": row.get("Nationality", ""),
                "overall": _as_int(row.get("Overall")), "potential": _as_int(row.get("Potential")),
                "club": row.get("Club", ""), "position": row.get("Position", ""),
                "jersey_number": _as_int(row.get("Jersey Number")), "height": row.get("Height", ""),
                "weight": row.get("Weight", ""),
            })

    @staticmethod
    def _standard_match(row: dict[str, str], competition: str, source: str) -> Match:
        return Match(
            _parse_date(row.get("datetime")), row.get("home_team", ""), row.get("away_team", ""),
            _as_int(row.get("home_goal")), _as_int(row.get("away_goal")), competition,
            _as_int(row.get("season")), row.get("round"), row.get("stage"), source,
        )

    @staticmethod
    def _extended_match(row: dict[str, str], _: str, source: str) -> Match:
        parsed = _parse_date(row.get("date"))
        return Match(
            parsed, row.get("home", ""), row.get("away", ""), _as_int(row.get("home_goal")),
            _as_int(row.get("away_goal")), row.get("tournament", "Unknown"), parsed.year if parsed else None,
            source=source, corners=_as_int(row.get("total_corners")),
            shots_home=_as_int(row.get("home_shots")), shots_away=_as_int(row.get("away_shots")),
        )

    @staticmethod
    def _historical_match(row: dict[str, str], competition: str, source: str) -> Match:
        return Match(
            _parse_date(row.get("Data")), row.get("Equipe_mandante", ""), row.get("Equipe_visitante", ""),
            _as_int(row.get("Gols_mandante")), _as_int(row.get("Gols_visitante")), competition,
            _as_int(row.get("Ano")), str(row.get("Rodada") or ""), source=source,
            venue=row.get("Arena") or None,
        )

    @staticmethod
    def _team_matches_team(match: Match, team: str, location: str) -> bool:
        key = canonical_team(team)
        return (location in ("any", "home") and match.home_key == key) or (
            location in ("any", "away") and match.away_key == key
        )

    def search_matches(
        self, team: Optional[str] = None, opponent: Optional[str] = None,
        competition: Optional[str] = None, season: Optional[int] = None,
        start_date: Optional[str] = None, end_date: Optional[str] = None,
        stage: Optional[str] = None, location: str = "any", limit: int = 100,
    ) -> dict[str, Any]:
        """Find matches.  ``team``/``opponent`` are orientation-independent."""
        if location not in {"any", "home", "away"}:
            raise ValueError("location must be one of: any, home, away")
        if limit < 1:
            raise ValueError("limit must be positive")
        start, end = _parse_date(start_date), _parse_date(end_date)
        if start_date and not start:
            raise ValueError("start_date must be YYYY-MM-DD or DD/MM/YYYY")
        if end_date and not end:
            raise ValueError("end_date must be YYYY-MM-DD or DD/MM/YYYY")
        if start and end and start > end:
            raise ValueError("start_date must not be after end_date")
        comp = _competition_key(competition) if competition else None
        stage_key = normalized(stage) if stage else None
        found = []
        for match in self.matches:
            if team and not self._team_matches_team(match, team, location):
                continue
            if opponent and not self._team_matches_team(match, opponent, "any"):
                continue
            if team and opponent and canonical_team(team) == canonical_team(opponent):
                continue
            if comp and _competition_key(match.competition) != comp:
                continue
            if season is not None and match.season != int(season):
                continue
            if start and (not match.date or match.date < start):
                continue
            if end and (not match.date or match.date > end):
                continue
            if stage_key and stage_key not in normalized(match.stage):
                continue
            found.append(match)
        found.sort(key=lambda item: item.date or date.min, reverse=True)
        return {"count": len(found), "matches": [item.public() for item in found[:limit]],
                "truncated": len(found) > limit}

    def team_stats(self, team: str, season: Optional[int] = None,
                   competition: Optional[str] = None, location: str = "any") -> dict[str, Any]:
        selection = self.search_matches(team=team, season=season, competition=competition,
                                        location=location, limit=max(1, len(self.matches)))
        matches = selection["matches"]
        key = canonical_team(team)
        wins = draws = losses = goals_for = goals_against = 0
        for match in matches:
            home = match["home_team_key"] == key
            mine = match["home_goals"] if home else match["away_goals"]
            theirs = match["away_goals"] if home else match["home_goals"]
            if mine is None or theirs is None:
                continue
            goals_for += mine
            goals_against += theirs
            if mine > theirs: wins += 1
            elif mine < theirs: losses += 1
            else: draws += 1
        played = wins + draws + losses
        return {"team": team, "team_key": key, "season": season, "competition": competition,
                "location": location, "matches": played, "wins": wins, "draws": draws,
                "losses": losses, "goals_for": goals_for, "goals_against": goals_against,
                "points": wins * 3 + draws, "win_rate": round(wins / played * 100, 1) if played else 0.0}

    def head_to_head(self, team_a: str, team_b: str, season: Optional[int] = None,
                     competition: Optional[str] = None, limit: int = 50) -> dict[str, Any]:
        # Calculate the record over the complete relationship, then present a
        # bounded match list so an MCP response remains practical.
        complete = self.search_matches(team=team_a, opponent=team_b, season=season,
                                       competition=competition, limit=max(1, len(self.matches)))
        a, b = canonical_team(team_a), canonical_team(team_b)
        a_wins = b_wins = draws = 0
        for match in complete["matches"]:
            home_score, away_score = match["home_goals"], match["away_goals"]
            if home_score is None or away_score is None: continue
            if home_score == away_score: draws += 1
            elif (home_score > away_score) == (match["home_team_key"] == a): a_wins += 1
            else: b_wins += 1
        result = {"count": complete["count"], "matches": complete["matches"][:limit],
                  "truncated": complete["count"] > limit}
        result.update({"team_a": team_a, "team_b": team_b, "team_a_wins": a_wins,
                       "team_b_wins": b_wins, "draws": draws})
        return result

    def search_players(self, name: Optional[str] = None, nationality: Optional[str] = None,
                       club: Optional[str] = None, position: Optional[str] = None,
                       min_overall: Optional[int] = None, limit: int = 100) -> dict[str, Any]:
        if limit < 1: raise ValueError("limit must be positive")
        tests = {"name": name, "nationality": nationality, "club": club, "position": position}
        selected = []
        for player in self.players:
            if any(value and normalized(value) not in normalized(player[field]) for field, value in tests.items()):
                continue
            if min_overall is not None and (player["overall"] is None or player["overall"] < int(min_overall)):
                continue
            selected.append(player)
        selected.sort(key=lambda p: (p["overall"] is not None, p["overall"] or -1, p["name"]), reverse=True)
        return {"count": len(selected), "players": selected[:limit], "truncated": len(selected) > limit}

    def standings(self, season: int, competition: str = "Brasileirao") -> dict[str, Any]:
        result = self.search_matches(season=season, competition=competition, limit=max(1, len(self.matches)))
        table: dict[str, dict[str, Any]] = {}
        def row(key: str, display: str) -> dict[str, Any]:
            return table.setdefault(key, {"team": display, "matches": 0, "wins": 0, "draws": 0,
                                          "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0})
        for match in result["matches"]:
            hg, ag = match["home_goals"], match["away_goals"]
            if hg is None or ag is None: continue
            home, away = row(match["home_team_key"], match["home_team"]), row(match["away_team_key"], match["away_team"])
            home["matches"] += 1; away["matches"] += 1
            home["goals_for"] += hg; home["goals_against"] += ag
            away["goals_for"] += ag; away["goals_against"] += hg
            if hg > ag:
                home["wins"] += 1; home["points"] += 3; away["losses"] += 1
            elif ag > hg:
                away["wins"] += 1; away["points"] += 3; home["losses"] += 1
            else:
                home["draws"] += 1; away["draws"] += 1; home["points"] += 1; away["points"] += 1
        rows = list(table.values())
        for item in rows: item["goal_difference"] = item["goals_for"] - item["goals_against"]
        rows.sort(key=lambda x: (x["points"], x["wins"], x["goal_difference"], x["goals_for"]), reverse=True)
        for index, item in enumerate(rows, 1): item["position"] = index
        return {"season": int(season), "competition": competition, "matches_used": result["count"], "standings": rows}

    def competition_stats(self, competition: Optional[str] = None, season: Optional[int] = None,
                          limit: int = 10) -> dict[str, Any]:
        result = self.search_matches(competition=competition, season=season, limit=max(1, len(self.matches)))
        matches = result["matches"]
        scored = [m for m in matches if m["home_goals"] is not None and m["away_goals"] is not None]
        total = sum(m["home_goals"] + m["away_goals"] for m in scored)
        home_wins = sum(m["home_goals"] > m["away_goals"] for m in scored)
        biggest = sorted(scored, key=lambda m: (abs(m["home_goals"] - m["away_goals"]), m["home_goals"] + m["away_goals"]), reverse=True)
        return {"competition": competition, "season": season, "matches": len(scored), "goals": total,
                "goals_per_match": round(total / len(scored), 2) if scored else 0.0,
                "home_win_rate": round(home_wins / len(scored) * 100, 1) if scored else 0.0,
                "biggest_wins": biggest[:limit]}

    def competitions_for_team(self, team: str) -> dict[str, Any]:
        result = self.search_matches(team=team, limit=max(1, len(self.matches)))
        groups: dict[str, int] = defaultdict(int)
        for match in result["matches"]: groups[match["competition"]] += 1
        return {"team": team, "competitions": [{"competition": name, "matches": count}
                 for name, count in sorted(groups.items())]}


TOOL_DEFINITIONS = [
    {"name": "search_matches", "description": "Find soccer matches by team, opponent, competition, season, date range, or stage.", "inputSchema": {"type": "object", "properties": {"team": {"type": "string"}, "opponent": {"type": "string"}, "competition": {"type": "string"}, "season": {"type": "integer"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "stage": {"type": "string"}, "location": {"enum": ["any", "home", "away"]}, "limit": {"type": "integer", "minimum": 1}}}},
    {"name": "team_stats", "description": "Calculate a team's wins, draws, losses, goals, points and win rate.", "inputSchema": {"type": "object", "required": ["team"], "properties": {"team": {"type": "string"}, "season": {"type": "integer"}, "competition": {"type": "string"}, "location": {"enum": ["any", "home", "away"]}}}},
    {"name": "head_to_head", "description": "Compare two teams' head-to-head results.", "inputSchema": {"type": "object", "required": ["team_a", "team_b"], "properties": {"team_a": {"type": "string"}, "team_b": {"type": "string"}, "season": {"type": "integer"}, "competition": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "search_players", "description": "Find FIFA players by name, nationality, club, position or rating.", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "nationality": {"type": "string"}, "club": {"type": "string"}, "position": {"type": "string"}, "min_overall": {"type": "integer"}, "limit": {"type": "integer", "minimum": 1}}}},
    {"name": "standings", "description": "Calculate a competition table from match results.", "inputSchema": {"type": "object", "required": ["season"], "properties": {"season": {"type": "integer"}, "competition": {"type": "string"}}}},
    {"name": "competition_stats", "description": "Calculate goals, home-win rate and biggest wins for a competition.", "inputSchema": {"type": "object", "properties": {"competition": {"type": "string"}, "season": {"type": "integer"}, "limit": {"type": "integer"}}}},
    {"name": "competitions_for_team", "description": "List competitions in which a team appears across all supplied files.", "inputSchema": {"type": "object", "required": ["team"], "properties": {"team": {"type": "string"}}}},
]


def _tool_text(name: str, value: dict[str, Any]) -> str:
    if name == "search_matches":
        return "\n".join(f"{m['date'] or 'unknown date'}: {m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']} ({m['competition']})" for m in value["matches"]) or "No matches found."
    return json.dumps(value, ensure_ascii=False, indent=2)


def handle_request(request: dict[str, Any], data: SoccerData) -> Optional[dict[str, Any]]:
    """Handle one JSON-RPC MCP request; exposed to make protocol tests simple."""
    method, request_id = request.get("method"), request.get("id")
    if method == "notifications/initialized": return None
    if method == "initialize":
        result: dict[str, Any] = {"protocolVersion": request.get("params", {}).get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}}, "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}}
    elif method == "tools/list": result = {"tools": TOOL_DEFINITIONS}
    elif method == "tools/call":
        params = request.get("params", {})
        name, arguments = params.get("name"), params.get("arguments", {})
        tool = getattr(data, name, None)
        if not callable(tool) or name.startswith("_"):
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        try:
            value = tool(**arguments)
            result = {"content": [{"type": "text", "text": _tool_text(name, value)}], "structuredContent": value}
        except (ValueError, TypeError) as exc:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(exc)}}
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(data_dir: Path | str = DATA_DIR) -> None:
    data = SoccerData(data_dir)
    for line in sys.stdin:
        try:
            response = handle_request(json.loads(line), data)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except json.JSONDecodeError as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian soccer MCP server")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    serve(args.data_dir)


if __name__ == "__main__":
    main()
