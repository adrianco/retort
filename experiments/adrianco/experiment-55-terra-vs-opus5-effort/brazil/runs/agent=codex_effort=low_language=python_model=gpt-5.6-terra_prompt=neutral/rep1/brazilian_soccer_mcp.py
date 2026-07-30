"""Brazilian soccer data queries and a small, dependency-free MCP server.

The query service deliberately uses the standard library so it works with the
downloaded CSV files without requiring pandas or a particular MCP SDK version.
Run ``python3 server.py`` to expose the tools over stdio.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


DATA_DIR = Path(__file__).parent / "data" / "kaggle"


def normalize_name(value: Any) -> str:
    """Return a comparison key for team/player names.

    State suffixes (``Flamengo-RJ`` and ``Flamengo - RJ``) are intentionally
    removed, as are accents and punctuation.
    """
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower().strip()
    text = re.sub(r"(?:\s*-\s*|\s+)(?:ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to|uru|arg|bol|chi|col|ecu|equ|par|per|ven)\s*$", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    aliases = {
        "sport club corinthians paulista": "corinthians",
        "sao paulo futebol clube": "sao paulo",
        "clube de regatas do flamengo": "flamengo",
        "sociedade esportiva palmeiras": "palmeiras",
        "fluminense football club": "fluminense",
        "santos futebol clube": "santos",
        "gremio foot ball porto alegrense": "gremio",
    }
    return aliases.get(text, text)


def normalize_competition(value: Any) -> str:
    """Comparison key with common names for the national league unified."""
    key = normalize_name(value)
    aliases = {
        "brasileirao": "serie a", "campeonato brasileiro": "serie a",
        "campeonato brasileiro serie a": "serie a", "brasileirao serie a": "serie a",
        "serie a brazil": "serie a",
    }
    return aliases.get(key, key)


def _number(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _date(value: str) -> date | None:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


class SoccerDataService:
    """Loads all supplied CSVs once and provides structured soccer queries."""

    MATCH_FILES = (
        ("Brasileirao_Matches.csv", "Brasileirão"),
        ("Brazilian_Cup_Matches.csv", "Copa do Brasil"),
        ("Libertadores_Matches.csv", "Libertadores"),
        ("BR-Football-Dataset.csv", None),
        ("novo_campeonato_brasileiro.csv", "Brasileirão"),
    )

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.matches: list[dict[str, Any]] = []
        self.players: list[dict[str, Any]] = []
        self.load()

    def _rows(self, filename: str) -> Iterable[dict[str, str]]:
        with (self.data_dir / filename).open(encoding="utf-8-sig", newline="") as source:
            yield from csv.DictReader(source)

    def load(self) -> None:
        self.matches.clear()
        for filename, fixed_competition in self.MATCH_FILES:
            for row in self._rows(filename):
                if filename == "BR-Football-Dataset.csv":
                    raw_date = row["date"]
                    home, away = row["home"], row["away"]
                    competition = row["tournament"] or "Unknown"
                    season = (_date(raw_date).year if _date(raw_date) else None)
                    round_, stage = None, None
                elif filename == "novo_campeonato_brasileiro.csv":
                    raw_date = row["Data"]
                    home, away = row["Equipe_mandante"], row["Equipe_visitante"]
                    competition, season, round_, stage = fixed_competition, _number(row["Ano"]), row["Rodada"], None
                else:
                    raw_date = row["datetime"]
                    home, away = row["home_team"], row["away_team"]
                    competition, season = fixed_competition, _number(row["season"])
                    round_, stage = row.get("round"), row.get("stage")
                self.matches.append({
                    "date": _date(raw_date).isoformat() if _date(raw_date) else raw_date,
                    "home_team": home, "away_team": away,
                    "home_goal": _number(row.get("home_goal", row.get("Gols_mandante"))),
                    "away_goal": _number(row.get("away_goal", row.get("Gols_visitante"))),
                    "season": season, "competition": competition, "round": round_, "stage": stage,
                    "source": filename,
                    "statistics": ({k: row[k] for k in ("home_corner", "away_corner", "home_attack", "away_attack", "home_shots", "away_shots", "total_corners") if row.get(k) not in (None, "")} if filename == "BR-Football-Dataset.csv" else {}),
                })
        for row in self._rows("fifa_data.csv"):
            self.players.append({
                "id": row.get("ID"), "name": row.get("Name", ""), "age": _number(row.get("Age")),
                "nationality": row.get("Nationality", ""), "overall": _number(row.get("Overall")),
                "potential": _number(row.get("Potential")), "club": row.get("Club", ""),
                "position": row.get("Position", ""), "jersey_number": _number(row.get("Jersey Number")),
            })

    @staticmethod
    def _team_matches(match: dict[str, Any], team: str) -> bool:
        key = normalize_name(team)
        return key in normalize_name(match["home_team"]) or key in normalize_name(match["away_team"])

    @staticmethod
    def _unique(matches: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove the same fixture repeated by overlapping source datasets."""
        unique, seen = [], set()
        for match in matches:
            key = (match["date"], normalize_name(match["home_team"]), normalize_name(match["away_team"]),
                   match["home_goal"], match["away_goal"], normalize_competition(match["competition"]))
            if key not in seen:
                seen.add(key); unique.append(match)
        return unique

    def search_matches(self, team: str | None = None, opponent: str | None = None,
                       competition: str | None = None, season: int | str | None = None,
                       start_date: str | None = None, end_date: str | None = None,
                       stage: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        start, end = _date(start_date or ""), _date(end_date or "")
        result = []
        for match in self.matches:
            match_date = _date(match["date"])
            if team and not self._team_matches(match, team): continue
            if opponent and not self._team_matches(match, opponent): continue
            if competition and normalize_competition(competition) not in normalize_competition(match["competition"]): continue
            if season is not None and match["season"] != _number(season): continue
            if stage and normalize_name(stage) not in normalize_name(match.get("stage")): continue
            if start and (not match_date or match_date < start): continue
            if end and (not match_date or match_date > end): continue
            result.append(match)
        return sorted(result, key=lambda m: m["date"], reverse=True)[:max(0, int(limit))]

    def team_statistics(self, team: str, season: int | str | None = None,
                        competition: str | None = None, venue: str = "all") -> dict[str, Any]:
        key = normalize_name(team)
        matches = self._unique(self.search_matches(team=team, season=season, competition=competition, limit=len(self.matches)))
        wins = draws = losses = goals_for = goals_against = 0
        for m in matches:
            home = normalize_name(m["home_team"]) == key
            if venue == "home" and not home: continue
            if venue == "away" and home: continue
            gf, ga = (m["home_goal"], m["away_goal"]) if home else (m["away_goal"], m["home_goal"])
            if gf is None or ga is None: continue
            goals_for += gf; goals_against += ga
            if gf > ga: wins += 1
            elif gf == ga: draws += 1
            else: losses += 1
        played = wins + draws + losses
        return {"team": team, "season": _number(season), "competition": competition, "venue": venue,
                "matches": played, "wins": wins, "draws": draws, "losses": losses,
                "goals_for": goals_for, "goals_against": goals_against, "points": wins * 3 + draws,
                "win_rate": round(100 * wins / played, 1) if played else 0.0}

    def head_to_head(self, team_a: str, team_b: str, **filters: Any) -> dict[str, Any]:
        matches = self._unique(self.search_matches(team_a, opponent=team_b, **filters))
        a_key = normalize_name(team_a); a_wins = b_wins = draws = 0
        for m in matches:
            a_home = normalize_name(m["home_team"]) == a_key
            a_score = m["home_goal"] if a_home else m["away_goal"]
            b_score = m["away_goal"] if a_home else m["home_goal"]
            if a_score is None or b_score is None: continue
            if a_score > b_score: a_wins += 1
            elif a_score < b_score: b_wins += 1
            else: draws += 1
        return {"team_a": team_a, "team_b": team_b, "matches": len(matches),
                "team_a_wins": a_wins, "team_b_wins": b_wins, "draws": draws, "recent_matches": matches[:10]}

    def search_players(self, name: str | None = None, nationality: str | None = None,
                       club: str | None = None, position: str | None = None,
                       limit: int = 50) -> list[dict[str, Any]]:
        result = []
        for player in self.players:
            if name and normalize_name(name) not in normalize_name(player["name"]): continue
            if nationality and normalize_name(nationality) not in normalize_name(player["nationality"]): continue
            if club and normalize_name(club) not in normalize_name(player["club"]): continue
            if position and normalize_name(position) not in normalize_name(player["position"]): continue
            result.append(player)
        return sorted(result, key=lambda p: (p["overall"] is not None, p["overall"] or -1), reverse=True)[:max(0, int(limit))]

    def standings(self, season: int | str, competition: str = "Brasileirão") -> list[dict[str, Any]]:
        # The supplied files overlap heavily.  A table must use one complete
        # fixture list, rather than treating the same season from each source
        # as additional games. Prefer the extended dataset when available.
        candidates = self.search_matches(season=season, competition=competition, limit=len(self.matches))
        by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for match in candidates:
            by_source[match["source"]].append(match)
        preferred = "BR-Football-Dataset.csv"
        source_matches = by_source.get(preferred) or max(by_source.values(), key=len, default=[])
        table: dict[str, dict[str, Any]] = {}
        def entry(display: str) -> dict[str, Any]:
            key = normalize_name(display)
            return table.setdefault(key, {"team": display, "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0})
        for m in self._unique(source_matches):
            if m["home_goal"] is None or m["away_goal"] is None: continue
            h, a = entry(m["home_team"]), entry(m["away_team"]); hg, ag = m["home_goal"], m["away_goal"]
            h["played"] += 1; a["played"] += 1; h["goals_for"] += hg; h["goals_against"] += ag; a["goals_for"] += ag; a["goals_against"] += hg
            if hg > ag: h["wins"] += 1; a["losses"] += 1; h["points"] += 3
            elif hg < ag: a["wins"] += 1; h["losses"] += 1; a["points"] += 3
            else: h["draws"] += 1; a["draws"] += 1; h["points"] += 1; a["points"] += 1
        values = list(table.values())
        for item in values: item["goal_difference"] = item["goals_for"] - item["goals_against"]
        return sorted(values, key=lambda x: (x["points"], x["wins"], x["goal_difference"], x["goals_for"]), reverse=True)

    def statistics(self, competition: str | None = None, season: int | str | None = None) -> dict[str, Any]:
        matches = self._unique(self.search_matches(competition=competition, season=season, limit=len(self.matches)))
        scored = [m for m in matches if m["home_goal"] is not None and m["away_goal"] is not None]
        home_wins = sum(m["home_goal"] > m["away_goal"] for m in scored); draws = sum(m["home_goal"] == m["away_goal"] for m in scored)
        biggest = sorted(scored, key=lambda m: abs(m["home_goal"] - m["away_goal"]), reverse=True)[:10]
        return {"matches": len(scored), "goals": sum(m["home_goal"] + m["away_goal"] for m in scored),
                "average_goals_per_match": round(sum(m["home_goal"] + m["away_goal"] for m in scored) / len(scored), 2) if scored else 0.0,
                "home_win_rate": round(100 * home_wins / len(scored), 1) if scored else 0.0,
                "draw_rate": round(100 * draws / len(scored), 1) if scored else 0.0, "biggest_wins": biggest}


TOOLS = [
    {"name": "search_matches", "description": "Find matches across every supplied match dataset.", "inputSchema": {"type": "object", "properties": {"team": {"type": "string"}, "opponent": {"type": "string"}, "competition": {"type": "string"}, "season": {"type": "integer"}, "start_date": {"type": "string"}, "end_date": {"type": "string"}, "stage": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "team_statistics", "description": "Calculate a team's win/loss/draw and goal record.", "inputSchema": {"type": "object", "required": ["team"], "properties": {"team": {"type": "string"}, "season": {"type": "integer"}, "competition": {"type": "string"}, "venue": {"type": "string", "enum": ["all", "home", "away"]}}}},
    {"name": "head_to_head", "description": "Compare two teams' results.", "inputSchema": {"type": "object", "required": ["team_a", "team_b"], "properties": {"team_a": {"type": "string"}, "team_b": {"type": "string"}, "season": {"type": "integer"}, "competition": {"type": "string"}}}},
    {"name": "search_players", "description": "Search FIFA player data by name, nationality, club, or position.", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "nationality": {"type": "string"}, "club": {"type": "string"}, "position": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "standings", "description": "Calculate a competition table from match results.", "inputSchema": {"type": "object", "required": ["season"], "properties": {"season": {"type": "integer"}, "competition": {"type": "string"}}}},
    {"name": "statistics", "description": "Get aggregate scoring, home-win, and biggest-win statistics.", "inputSchema": {"type": "object", "properties": {"competition": {"type": "string"}, "season": {"type": "integer"}}}},
]


def serve() -> None:
    """Serve enough of MCP's JSON-RPC stdio transport to interoperate with clients."""
    service = SoccerDataService()
    for line in sys.stdin:
        try:
            request = json.loads(line); method = request.get("method"); params = request.get("params", {}); request_id = request.get("id")
            if method == "initialize": result = {"protocolVersion": params.get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}}, "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}}
            elif method == "tools/list": result = {"tools": TOOLS}
            elif method == "tools/call":
                name, arguments = params["name"], params.get("arguments", {})
                fn = {"search_matches": service.search_matches, "team_statistics": service.team_statistics, "head_to_head": service.head_to_head, "search_players": service.search_players, "standings": service.standings, "statistics": service.statistics}.get(name)
                if not fn: raise ValueError(f"Unknown tool: {name}")
                result = {"content": [{"type": "text", "text": json.dumps(fn(**arguments), ensure_ascii=False, default=str)}]}
            elif method == "notifications/initialized": continue
            else: raise ValueError(f"Unsupported method: {method}")
            if request_id is not None: print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}), flush=True)
        except Exception as exc:
            if 'request_id' in locals() and request_id is not None: print(json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(exc)}}), flush=True)
