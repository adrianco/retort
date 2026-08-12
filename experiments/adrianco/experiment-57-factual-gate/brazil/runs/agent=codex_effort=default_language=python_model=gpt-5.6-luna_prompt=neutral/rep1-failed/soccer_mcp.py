"""Brazilian soccer data service and dependency-free MCP stdio server.

The public ``SoccerDatabase`` class is useful in ordinary Python programs and
the ``main`` entry point speaks the JSON-RPC subset used by MCP clients.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DATA_DIR = Path(__file__).parent / "data" / "kaggle"
MATCH_FILES = {
    "Brasileirão": "Brasileirao_Matches.csv",
    "Copa do Brasil": "Brazilian_Cup_Matches.csv",
    "Libertadores": "Libertadores_Matches.csv",
}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_team(value: Any) -> str:
    """Normalize accents, punctuation, state suffixes, and common whitespace."""
    value = unicodedata.normalize("NFKD", _text(value)).encode("ascii", "ignore").decode()
    value = re.sub(r"\s*[-–—]\s*[A-Z]{2}\s*$", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip().casefold()
    return value


def parse_date(value: Any) -> dt.date | None:
    value = _text(value)
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def _number(value: Any) -> int | float | None:
    try:
        n = float(str(value).replace(",", "."))
        return int(n) if n.is_integer() else n
    except (TypeError, ValueError):
        return None


class SoccerDatabase:
    """Load all supplied datasets once and answer structured soccer queries."""

    def __init__(self, data_dir: str | Path = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.matches: list[dict[str, Any]] = []
        self.players: list[dict[str, Any]] = []
        self._load_matches()
        self._load_players()

    def _rows(self, filename: str) -> Iterable[dict[str, str]]:
        with (self.data_dir / filename).open(encoding="utf-8-sig", newline="") as f:
            yield from csv.DictReader(f)

    def _add_match(self, row: dict[str, Any], competition: str, source: str, *, date_key: str,
                   home_key: str, away_key: str, hg_key: str, ag_key: str, season_key: str,
                   round_key: str | None = None, stage_key: str | None = None) -> None:
        date = parse_date(row.get(date_key))
        self.matches.append({
            "date": date.isoformat() if date else _text(row.get(date_key)),
            "home_team": _text(row.get(home_key)), "away_team": _text(row.get(away_key)),
            "home_goal": _number(row.get(hg_key)), "away_goal": _number(row.get(ag_key)),
            "season": _number(row.get(season_key)), "competition": competition,
            "round": _text(row.get(round_key)) if round_key else "",
            "stage": _text(row.get(stage_key)) if stage_key else "", "source": source,
        })

    def _load_matches(self) -> None:
        for competition, filename in MATCH_FILES.items():
            if not (self.data_dir / filename).exists():
                continue
            sample = next(iter(self._rows(filename)), {})
            # Re-read after peeking; the files are small enough and this keeps the mapper clear.
            if competition == "Brasileirão":
                rows = self._rows(filename)
                for row in rows:
                    self._add_match(row, competition, filename, date_key="datetime", home_key="home_team", away_key="away_team", hg_key="home_goal", ag_key="away_goal", season_key="season", round_key="round")
            elif competition == "Copa do Brasil":
                for row in self._rows(filename):
                    self._add_match(row, competition, filename, date_key="datetime", home_key="home_team", away_key="away_team", hg_key="home_goal", ag_key="away_goal", season_key="season", round_key="round")
            else:
                for row in self._rows(filename):
                    self._add_match(row, competition, filename, date_key="datetime", home_key="home_team", away_key="away_team", hg_key="home_goal", ag_key="away_goal", season_key="season", stage_key="stage")

        historical = self.data_dir / "novo_campeonato_brasileiro.csv"
        if historical.exists():
            for row in self._rows(historical.name):
                self._add_match(row, "Brasileirão", historical.name, date_key="Data", home_key="Equipe_mandante", away_key="Equipe_visitante", hg_key="Gols_mandante", ag_key="Gols_visitante", season_key="Ano", round_key="Rodada")

        extended = self.data_dir / "BR-Football-Dataset.csv"
        if extended.exists():
            for row in self._rows(extended.name):
                self._add_match(row, _text(row.get("tournament")) or "Extended dataset", extended.name, date_key="date", home_key="home", away_key="away", hg_key="home_goal", ag_key="away_goal", season_key="date")
                # Date-derived season is preferable to an absent season column.
                self.matches[-1]["season"] = parse_date(row.get("date")).year if parse_date(row.get("date")) else None

    def _load_players(self) -> None:
        filename = self.data_dir / "fifa_data.csv"
        if filename.exists():
            self.players = list(self._rows(filename))

    def matches_query(self, team: str | None = None, opponent: str | None = None,
                      season: int | str | None = None, competition: str | None = None,
                      start_date: str | None = None, end_date: str | None = None,
                      limit: int = 100) -> list[dict[str, Any]]:
        team_n, opp_n = normalize_team(team), normalize_team(opponent)
        season_n = int(season) if season not in (None, "") else None
        start, end = parse_date(start_date), parse_date(end_date)
        result = []
        for match in self.matches:
            home_n, away_n = normalize_team(match["home_team"]), normalize_team(match["away_team"])
            if team and team_n not in (home_n, away_n) and team_n not in home_n and team_n not in away_n:
                continue
            if opponent and not (opp_n in home_n or opp_n in away_n):
                continue
            if team and opponent and not ((team_n in home_n and opp_n in away_n) or (team_n in away_n and opp_n in home_n)):
                continue
            if season_n is not None and match["season"] != season_n:
                continue
            if competition and competition.casefold() not in match["competition"].casefold():
                continue
            date = parse_date(match["date"])
            if start and (not date or date < start):
                continue
            if end and (not date or date > end):
                continue
            result.append(match)
        result.sort(key=lambda x: x["date"], reverse=True)
        return result[: max(0, limit)]

    def team_stats(self, team: str, season: int | str | None = None, competition: str | None = None,
                   home_only: bool = False, away_only: bool = False) -> dict[str, Any]:
        rows = self.matches_query(team=team, season=season, competition=competition, limit=10**9)
        tn = normalize_team(team)
        stats = {"team": team, "matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0, "win_rate": 0.0}
        for m in rows:
            is_home = tn in normalize_team(m["home_team"])
            if home_only and not is_home or away_only and is_home:
                continue
            gf, ga = (m["home_goal"], m["away_goal"]) if is_home else (m["away_goal"], m["home_goal"])
            if gf is None or ga is None: continue
            stats["matches"] += 1; stats["goals_for"] += gf; stats["goals_against"] += ga
            if gf > ga: stats["wins"] += 1; stats["points"] += 3
            elif gf == ga: stats["draws"] += 1; stats["points"] += 1
            else: stats["losses"] += 1
        stats["win_rate"] = round(stats["wins"] / stats["matches"] * 100, 1) if stats["matches"] else 0.0
        return stats

    def head_to_head(self, team_a: str, team_b: str, **filters: Any) -> dict[str, Any]:
        rows = self.matches_query(team_a, team_b, limit=10**9, **filters)
        a = normalize_team(team_a); wins = {team_a: 0, team_b: 0, "draws": 0}
        for m in rows:
            ag, bg = (m["home_goal"], m["away_goal"]) if a in normalize_team(m["home_team"]) else (m["away_goal"], m["home_goal"])
            if ag > bg: wins[team_a] += 1
            elif bg > ag: wins[team_b] += 1
            else: wins["draws"] += 1
        return {"team_a": team_a, "team_b": team_b, **wins, "matches": rows}

    def players_query(self, name: str | None = None, nationality: str | None = None,
                      club: str | None = None, position: str | None = None,
                      min_overall: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
        def has(row: dict[str, str], key: str, value: str | None) -> bool:
            return not value or value.casefold() in _text(row.get(key)).casefold()
        out = [p for p in self.players if has(p, "Name", name) and has(p, "Nationality", nationality) and has(p, "Club", club) and has(p, "Position", position)]
        if min_overall is not None:
            out = [p for p in out if (_number(p.get("Overall")) or 0) >= min_overall]
        out.sort(key=lambda p: (_number(p.get("Overall")) or 0), reverse=True)
        return out[:max(0, limit)]

    def standings(self, season: int | str, competition: str = "Brasileirão") -> list[dict[str, Any]]:
        table: dict[str, dict[str, Any]] = {}
        for m in self.matches_query(season=season, competition=competition, limit=10**9):
            if m["home_goal"] is None or m["away_goal"] is None: continue
            for side, other, gf, ga in ((m["home_team"], m["away_team"], m["home_goal"], m["away_goal"]), (m["away_team"], m["home_team"], m["away_goal"], m["home_goal"])):
                key = normalize_team(side); t = table.setdefault(key, {"team": side, "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0})
                t["played"] += 1; t["goals_for"] += gf; t["goals_against"] += ga
                if gf > ga: t["wins"] += 1; t["points"] += 3
                elif gf == ga: t["draws"] += 1; t["points"] += 1
                else: t["losses"] += 1
        return sorted(table.values(), key=lambda t: (t["points"], t["goals_for"] - t["goals_against"], t["goals_for"]), reverse=True)

    def aggregate_stats(self, competition: str | None = None, season: int | str | None = None) -> dict[str, Any]:
        rows = self.matches_query(competition=competition, season=season, limit=10**9)
        goals = sum((m["home_goal"] or 0) + (m["away_goal"] or 0) for m in rows)
        home_wins = sum((m["home_goal"] or 0) > (m["away_goal"] or 0) for m in rows)
        return {"matches": len(rows), "goals": goals, "average_goals": round(goals / len(rows), 3) if rows else 0.0, "home_wins": home_wins, "home_win_rate": round(home_wins / len(rows) * 100, 1) if rows else 0.0}

    def query(self, question: str, limit: int = 20) -> dict[str, Any]:
        """Best-effort natural-language dispatch for common soccer questions."""
        q = question.strip(); years = re.findall(r"\b(?:19|20)\d{2}\b", q); season = int(years[0]) if years else None
        if any(x in q.casefold() for x in ("player", "jogador", "who is")):
            nationality = "Brazil" if re.search(r"brazilian|brasileir", q, re.I) else None
            return {"players": self.players_query(name=None if "all" in q.casefold() else q, nationality=nationality, limit=limit)}
        teams = re.findall(r"[A-ZÀ-Ý][\wÀ-ÿ]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ]+){0,2}", q)
        if "average" in q.casefold() or "most goals" in q.casefold() or "statistics" in q.casefold(): return {"statistics": self.aggregate_stats(season=season)}
        if len(teams) >= 2 or "between" in q.casefold(): return {"matches": self.matches_query(team=teams[0] if teams else None, opponent=teams[1] if len(teams)>1 else None, season=season, limit=limit)}
        if teams: return {"matches": self.matches_query(team=teams[0], season=season, limit=limit)}
        return {"matches": self.matches_query(season=season, limit=limit)}


TOOLS = {
    "search_matches": {"description": "Find soccer matches by teams, season, competition, and dates."},
    "team_statistics": {"description": "Calculate a team's match record and goals."},
    "head_to_head": {"description": "Compare two teams head-to-head."},
    "search_players": {"description": "Search the FIFA player database."},
    "standings": {"description": "Calculate competition standings from match results."},
    "statistics": {"description": "Calculate aggregate match statistics."},
    "ask_soccer": {"description": "Answer a common natural-language soccer question."},
}


def _call(db: SoccerDatabase, name: str, args: dict[str, Any]) -> Any:
    methods = {"search_matches": db.matches_query, "team_statistics": db.team_stats, "head_to_head": db.head_to_head, "search_players": db.players_query, "standings": db.standings, "statistics": db.aggregate_stats, "ask_soccer": db.query}
    if name not in methods: raise ValueError(f"Unknown tool: {name}")
    return methods[name](**args)


def main() -> None:
    db = SoccerDatabase()
    for line in sys.stdin:
        try:
            request = json.loads(line); method = request.get("method"); result: Any
            if method == "initialize": result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}}
            elif method == "tools/list": result = {"tools": [{"name": n, **v, "inputSchema": {"type": "object"}} for n, v in TOOLS.items()]}
            elif method == "tools/call":
                p = request.get("params", {}); result = {"content": [{"type": "text", "text": json.dumps(_call(db, p["name"], p.get("arguments", {})), ensure_ascii=False, default=str)}]}
            else: result = {}
            response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(locals().get("request"), dict) else None, "error": {"code": -32603, "message": str(exc)}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
