"""Brazilian soccer data service and dependency-free MCP stdio server.

The public ``SoccerDatabase`` class is useful in tests and applications.  The
module's CLI speaks the MCP JSON-RPC wire format over stdin/stdout without
requiring an optional SDK, which keeps the demo easy to run in a clean Python
environment.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "kaggle"


def _key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    text = re.sub(r"\s+", " ", text).strip().lower()
    # Dataset suffixes and punctuation should not prevent a team match.
    text = re.sub(r"\s*[-(](?:[a-z]{2,3}|uru|arg|equ)\)?$", "", text)
    return re.sub(r"[^a-z0-9 ]", "", text)


def _number(value: Any) -> int | float:
    try:
        number = float(str(value).strip())
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return 0


def _date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


@dataclass(frozen=True)
class Match:
    date: str
    home_team: str
    away_team: str
    home_goals: int | float
    away_goals: int | float
    competition: str
    season: int | None = None
    round: str | None = None
    stage: str | None = None
    stats: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SoccerDatabase:
    """Loads the six supplied CSV files once and exposes deterministic queries."""

    def __init__(self, data_dir: str | Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.matches: list[Match] = []
        self.players: list[dict[str, Any]] = []
        self._load_matches()
        self._load_players()

    def _rows(self, filename: str) -> Iterable[dict[str, str]]:
        with (self.data_dir / filename).open(encoding="utf-8-sig", newline="") as fh:
            yield from csv.DictReader(fh)

    def _load_matches(self) -> None:
        specs = [
            ("Brasileirao_Matches.csv", "Brasileirão", "home_team", "away_team", "datetime", "season", "round", "stage"),
            ("Brazilian_Cup_Matches.csv", "Copa do Brasil", "home_team", "away_team", "datetime", "season", "round", None),
            ("Libertadores_Matches.csv", "Copa Libertadores", "home_team", "away_team", "datetime", "season", None, "stage"),
        ]
        for filename, competition, home, away, date, season, round_col, stage in specs:
            for row in self._rows(filename):
                self.matches.append(Match(row.get(date, ""), row.get(home, ""), row.get(away, ""),
                    _number(row.get("home_goal")), _number(row.get("away_goal")), competition,
                    int(_number(row.get(season))) or None, row.get(round_col) if round_col else None,
                    row.get(stage) if stage else None))
        for row in self._rows("BR-Football-Dataset.csv"):
            stats = {k: _number(row[k]) for k in ("home_corner", "away_corner", "home_attack", "away_attack", "home_shots", "away_shots", "total_corners") if row.get(k, "") != ""}
            self.matches.append(Match(row.get("date", ""), row.get("home", ""), row.get("away", ""), _number(row.get("home_goal")), _number(row.get("away_goal")), row.get("tournament", "Unknown"), _date(row.get("date")).year if _date(row.get("date")) else None, stats=stats))
        for row in self._rows("novo_campeonato_brasileiro.csv"):
            self.matches.append(Match(row.get("Data", ""), row.get("Equipe_mandante", ""), row.get("Equipe_visitante", ""), _number(row.get("Gols_mandante")), _number(row.get("Gols_visitante")), "Brasileirão (histórico)", int(_number(row.get("Ano"))) or None, row.get("Rodada"), stats={"stadium": row.get("Arena", "")}))

    def _load_players(self) -> None:
        for row in self._rows("fifa_data.csv"):
            self.players.append({k.strip(): (int(_number(v)) if k.strip() in {"ID", "Age", "Overall", "Potential"} else v.strip()) for k, v in row.items() if k is not None})

    @staticmethod
    def _team_match(team: str, value: str) -> bool:
        wanted, actual = _key(team), _key(value)
        return bool(wanted) and (wanted == actual or wanted in actual or actual in wanted)

    def search_matches(self, team: str | None = None, opponent: str | None = None, start_date: str | None = None, end_date: str | None = None, competition: str | None = None, season: int | str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        start, end = _date(start_date) if start_date else None, _date(end_date) if end_date else None
        season_num = int(season) if season not in (None, "") else None
        found = []
        for match in self.matches:
            md = _date(match.date)
            if team and not (self._team_match(team, match.home_team) or self._team_match(team, match.away_team)): continue
            if opponent and not ((self._team_match(team or "", match.home_team) and self._team_match(opponent, match.away_team)) or (self._team_match(team or "", match.away_team) and self._team_match(opponent, match.home_team))): continue
            if start and (not md or md < start): continue
            if end and (not md or md > end): continue
            if competition:
                wanted_comp = _key(competition)
                actual_comp = _key(match.competition)
                # Keep the two Brasileirão sources independently selectable;
                # asking for "Brasileirão" means the dedicated Serie A file.
                if wanted_comp == "brasileirao":
                    if actual_comp != "brasileirao": continue
                elif wanted_comp not in actual_comp: continue
            if season_num is not None and match.season != season_num: continue
            found.append(match)
        found.sort(key=lambda m: _date(m.date) or datetime.min, reverse=True)
        return [m.to_dict() for m in (found[:limit] if limit else found)]

    def team_stats(self, team: str, season: int | str | None = None, competition: str | None = None, home_only: bool = False, away_only: bool = False) -> dict[str, Any]:
        games = [Match(**m) for m in self.search_matches(team=team, season=season, competition=competition)]
        games = [m for m in games if not home_only or self._team_match(team, m.home_team)]
        games = [m for m in games if not away_only or self._team_match(team, m.away_team)]
        wins = draws = losses = gf = ga = 0
        for m in games:
            home = self._team_match(team, m.home_team); scored, conceded = (m.home_goals, m.away_goals) if home else (m.away_goals, m.home_goals)
            gf += scored; ga += conceded
            wins += scored > conceded; draws += scored == conceded; losses += scored < conceded
        return {"team": team, "matches": len(games), "wins": wins, "draws": draws, "losses": losses, "goals_for": gf, "goals_against": ga, "points": wins * 3 + draws, "win_rate": round(wins / len(games) * 100, 1) if games else 0.0}

    def head_to_head(self, team_a: str, team_b: str, **filters: Any) -> dict[str, Any]:
        games = [Match(**m) for m in self.search_matches(team=team_a, opponent=team_b, **filters)]
        a_wins = b_wins = draws = 0
        for m in games:
            a_home = self._team_match(team_a, m.home_team); a_score, b_score = (m.home_goals, m.away_goals) if a_home else (m.away_goals, m.home_goals)
            a_wins += a_score > b_score; b_wins += b_score > a_score; draws += a_score == b_score
        return {"team_a": team_a, "team_b": team_b, "matches": len(games), "team_a_wins": a_wins, "team_b_wins": b_wins, "draws": draws, "results": [m.to_dict() for m in games]}

    def search_players(self, name: str | None = None, nationality: str | None = None, club: str | None = None, position: str | None = None, limit: int = 50, min_overall: int | None = None) -> list[dict[str, Any]]:
        def contains(value: Any, query: str | None) -> bool: return not query or _key(query) in _key(value)
        result = [p for p in self.players if contains(p.get("Name"), name) and contains(p.get("Nationality"), nationality) and contains(p.get("Club"), club) and contains(p.get("Position"), position) and (min_overall is None or p.get("Overall", 0) >= min_overall)]
        result.sort(key=lambda p: p.get("Overall", 0), reverse=True)
        return result[:limit]

    def standings(self, season: int | str, competition: str = "Brasileirão") -> list[dict[str, Any]]:
        table: dict[str, dict[str, Any]] = defaultdict(lambda: {"team": "", "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0})
        for raw in self.search_matches(season=season, competition=competition):
            m = Match(**raw); h, a = table[m.home_team], table[m.away_team]; h["team"], a["team"] = m.home_team, m.away_team
            h["played"] += 1; a["played"] += 1; h["goals_for"] += m.home_goals; h["goals_against"] += m.away_goals; a["goals_for"] += m.away_goals; a["goals_against"] += m.home_goals
            if m.home_goals > m.away_goals: h["wins"] += 1; h["points"] += 3; a["losses"] += 1
            elif m.home_goals < m.away_goals: a["wins"] += 1; a["points"] += 3; h["losses"] += 1
            else: h["draws"] += 1; a["draws"] += 1; h["points"] += 1; a["points"] += 1
        return sorted(table.values(), key=lambda x: (x["points"], x["goals_for"] - x["goals_against"], x["goals_for"]), reverse=True)

    def statistics(self, competition: str | None = None, season: int | str | None = None) -> dict[str, Any]:
        games = [Match(**m) for m in self.search_matches(competition=competition, season=season)]
        total = sum(m.home_goals + m.away_goals for m in games)
        return {"matches": len(games), "total_goals": total, "average_goals": round(total / len(games), 3) if games else 0.0, "home_wins": sum(m.home_goals > m.away_goals for m in games), "away_wins": sum(m.away_goals > m.home_goals for m in games), "draws": sum(m.home_goals == m.away_goals for m in games)}

    def query(self, question: str) -> dict[str, Any]:
        """Small deterministic intent router for MCP clients without an LLM."""
        q = question.strip(); low = _key(q)
        years = re.findall(r"\b(?:19|20)\d{2}\b", q); season = int(years[0]) if years else None
        teams = re.findall(r"\b(Flamengo|Fluminense|Palmeiras|Corinthians|Santos|Gremio|Grêmio|Vasco|Botafogo|Sao Paulo|São Paulo|Internacional|Cruzeiro|Atletico Mineiro|Atlético Mineiro)\b", q, re.I)
        if any(x in low for x in ("player", "players", "jogador", "jogadores")):
            return {"type": "players", "results": self.search_players(nationality="Brazil" if "brazil" in low or "brasil" in low else None, club=teams[0] if teams else None)}
        if "standings" in low or "table" in low or "classificacao" in low: return {"type": "standings", "results": self.standings(season or 2019)}
        if "average" in low or "biggest" in low or "statistics" in low or "media" in low: return {"type": "statistics", "results": self.statistics(season=season)}
        if len(teams) >= 2: return {"type": "head_to_head", "results": self.head_to_head(teams[0], teams[1], season=season)}
        return {"type": "matches", "results": self.search_matches(team=teams[0] if teams else None, season=season)}


TOOLS = [{"name": "search_matches", "description": "Find soccer matches by team, opponent, dates, competition, season", "inputSchema": {"type": "object", "properties": {"team": {"type": "string"}, "opponent": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "competition": {"type": "string"}, "season": {"type": "integer"}, "limit": {"type": "integer"}}}}, {"name": "team_stats", "description": "Calculate a team's record and goals", "inputSchema": {"type": "object", "properties": {"team": {"type": "string"}, "season": {"type": "integer"}, "competition": {"type": "string"}, "home_only": {"type": "boolean"}, "away_only": {"type": "boolean"}}, "required": ["team"]}}, {"name": "head_to_head", "description": "Compare two teams", "inputSchema": {"type": "object", "properties": {"team_a": {"type": "string"}, "team_b": {"type": "string"}, "season": {"type": "integer"}}, "required": ["team_a", "team_b"]}}, {"name": "search_players", "description": "Search FIFA players", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "nationality": {"type": "string"}, "club": {"type": "string"}, "position": {"type": "string"}, "limit": {"type": "integer"}}}}, {"name": "standings", "description": "Calculate competition standings", "inputSchema": {"type": "object", "properties": {"season": {"type": "integer"}, "competition": {"type": "string"}}, "required": ["season"]}}, {"name": "statistics", "description": "Aggregate goals and results", "inputSchema": {"type": "object", "properties": {"competition": {"type": "string"}, "season": {"type": "integer"}}}}, {"name": "query_soccer", "description": "Answer a natural-language soccer question", "inputSchema": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}]


def _mcp_result(request: dict[str, Any], db: SoccerDatabase) -> dict[str, Any] | None:
    if request.get("method") == "notifications/initialized": return None
    method, rid = request.get("method"), request.get("id")
    if method == "initialize": result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}}
    elif method == "tools/list": result = {"tools": TOOLS}
    elif method == "tools/call":
        args = request.get("params", {}).get("arguments", {}); name = request.get("params", {}).get("name")
        try:
            value = getattr(db, name)(**args) if name != "query_soccer" else db.query(args["question"])
            result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, default=str)}], "structuredContent": value}
        except (AttributeError, TypeError, KeyError, ValueError) as exc: return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": str(exc)}}
    else: return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown method: {method}"}}
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def main() -> None:
    db = SoccerDatabase()
    for line in sys.stdin:
        try:
            response = _mcp_result(json.loads(line), db)
            if response is not None: print(json.dumps(response, ensure_ascii=False), flush=True)
        except json.JSONDecodeError as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}), flush=True)


if __name__ == "__main__": main()
