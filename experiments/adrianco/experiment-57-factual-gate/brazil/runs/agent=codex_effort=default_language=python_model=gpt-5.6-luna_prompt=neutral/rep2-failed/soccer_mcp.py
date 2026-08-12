"""Query and normalization layer for the Brazilian Soccer MCP server.

The implementation intentionally uses only Python's standard library so the
server can run in a clean MCP host. CSVs are normalized once at startup and
all public methods return JSON-serializable dictionaries.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _number(value: Any) -> int | float:
    try:
        number = float(_text(value).replace(",", "."))
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return 0


def parse_date(value: Any) -> datetime | None:
    value = _text(value)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            pass
    return None


def normalize_team(name: Any) -> str:
    """Return a comparison key while preserving original display names."""
    value = unicodedata.normalize("NFKD", _text(name)).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"\s*[-/]\s*[a-z]{2}\s*$", "", value)
    value = re.sub(r"\b(futebol clube|football club|fc|sc|sport club|club)\b", " ", value)
    value = re.sub(r"\s*\([^)]*\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    aliases = {
        "sport club corinthians paulista": "corinthians",
        "corinthians paulista": "corinthians",
        "sao paulo futebol clube": "sao paulo",
        "sao paulo fc": "sao paulo",
        "clube atletico mineiro": "atletico mineiro",
        "atletico mg": "atletico mineiro",
        "atletico pr": "atletico paranaense",
        "athletico paranaense": "atletico paranaense",
        "gremio": "gremio",
    }
    return aliases.get(value, value)


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

    def as_dict(self) -> dict[str, Any]:
        result = {"date": self.date, "home_team": self.home_team, "away_team": self.away_team,
                  "home_goals": self.home_goals, "away_goals": self.away_goals,
                  "competition": self.competition}
        if self.season is not None: result["season"] = self.season
        if self.round: result["round"] = self.round
        if self.stage: result["stage"] = self.stage
        if self.stats: result.update(self.stats)
        return result


COMPETITION_FILES = {
    "Brasileirão": ("Brasileirao_Matches.csv", "brasileirao"),
    "Copa do Brasil": ("Brazilian_Cup_Matches.csv", "copa do brasil"),
    "Copa Libertadores": ("Libertadores_Matches.csv", "libertadores"),
}


class SoccerData:
    def __init__(self, data_dir: str | Path = "data/kaggle") -> None:
        self.data_dir = Path(data_dir)
        self.matches: list[Match] = []
        self.players: list[dict[str, Any]] = []
        self._load_matches()
        self._load_players()

    def _rows(self, filename: str) -> Iterable[dict[str, str]]:
        with (self.data_dir / filename).open(encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)

    def _load_matches(self) -> None:
        for competition, (filename, _) in COMPETITION_FILES.items():
            for row in self._rows(filename):
                self.matches.append(Match(_text(row.get("datetime")), _text(row.get("home_team")),
                    _text(row.get("away_team")), _number(row.get("home_goal")), _number(row.get("away_goal")),
                    competition, int(_number(row.get("season"))) or None, _text(row.get("round")) or None,
                    _text(row.get("stage")) or None))
        for row in self._rows("BR-Football-Dataset.csv"):
            self.matches.append(Match(_text(row.get("date")), _text(row.get("home")), _text(row.get("away")),
                _number(row.get("home_goal")), _number(row.get("away_goal")), _text(row.get("tournament")),
                parse_date(row.get("date")).year if parse_date(row.get("date")) else None,
                stats={k: _number(row[k]) for k in ("home_corner", "away_corner", "home_attack", "away_attack", "home_shots", "away_shots", "total_corners") if row.get(k) != ""}))
        for row in self._rows("novo_campeonato_brasileiro.csv"):
            self.matches.append(Match(_text(row.get("Data")), _text(row.get("Equipe_mandante")), _text(row.get("Equipe_visitante")),
                _number(row.get("Gols_mandante")), _number(row.get("Gols_visitante")), "Brasileirão (histórico)",
                int(_number(row.get("Ano"))) or None, _text(row.get("Rodada")) or None,
                stats={"winner": _text(row.get("Vencedor")), "stadium": _text(row.get("Arena"))}))

    def _load_players(self) -> None:
        for row in self._rows("fifa_data.csv"):
            self.players.append({k: row[k].strip() for k in row if k})

    def find_matches(self, team: str | None = None, opponent: str | None = None,
                     competition: str | None = None, season: int | str | None = None,
                     date_from: str | None = None, date_to: str | None = None,
                     limit: int = 100) -> list[dict[str, Any]]:
        team_key, opponent_key = normalize_team(team), normalize_team(opponent)
        from_date, to_date = parse_date(date_from), parse_date(date_to)
        season_num = int(season) if season is not None and str(season).isdigit() else None
        result = []
        for match in self.matches:
            homes, aways = normalize_team(match.home_team), normalize_team(match.away_team)
            if team and team_key not in (homes, aways): continue
            if opponent and {team_key, opponent_key} != {homes, aways}: continue
            if competition and competition.lower() not in match.competition.lower(): continue
            if season_num is not None and match.season != season_num: continue
            date = parse_date(match.date)
            if from_date and (not date or date < from_date): continue
            if to_date and (not date or date > to_date): continue
            result.append(match)
        result.sort(key=lambda m: parse_date(m.date) or datetime.min, reverse=True)
        return [m.as_dict() for m in result[:max(0, limit)]]

    def team_stats(self, team: str, season: int | str | None = None, competition: str | None = None,
                   home_only: bool = False, away_only: bool = False) -> dict[str, Any]:
        key = normalize_team(team); games = []
        for m in self.matches:
            if season is not None and m.season != int(season): continue
            if competition and competition.lower() not in m.competition.lower(): continue
            side = "home" if normalize_team(m.home_team) == key else "away" if normalize_team(m.away_team) == key else None
            if not side or (home_only and side != "home") or (away_only and side != "away"): continue
            gf, ga = (m.home_goals, m.away_goals) if side == "home" else (m.away_goals, m.home_goals)
            games.append((gf, ga))
        wins = sum(gf > ga for gf, ga in games); draws = sum(gf == ga for gf, ga in games)
        matches = len(games); losses = matches - wins - draws
        return {"team": team, "matches": matches, "wins": wins, "draws": draws, "losses": losses,
                "goals_for": sum(gf for gf, _ in games), "goals_against": sum(ga for _, ga in games),
                "win_rate": round(wins / matches * 100, 2) if matches else 0.0}

    def head_to_head(self, team_a: str, team_b: str, **filters: Any) -> dict[str, Any]:
        games = self.find_matches(team_a, team_b, **filters, limit=100000)
        a, b = normalize_team(team_a), normalize_team(team_b); wins = {team_a: 0, team_b: 0, "draws": 0}
        for g in games:
            ah = normalize_team(g["home_team"]) == a
            score_a, score_b = (g["home_goals"], g["away_goals"]) if ah else (g["away_goals"], g["home_goals"])
            if score_a > score_b: wins[team_a] += 1
            elif score_b > score_a: wins[team_b] += 1
            else: wins["draws"] += 1
        return {"team_a": team_a, "team_b": team_b, "matches": games, "summary": wins}

    def players_search(self, name: str | None = None, nationality: str | None = None,
                       club: str | None = None, position: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        def contains(value: str, query: str | None) -> bool:
            return not query or normalize_team(query) in normalize_team(value)
        found = [p for p in self.players if contains(p.get("Name", ""), name) and contains(p.get("Nationality", ""), nationality)
                 and contains(p.get("Club", ""), club) and contains(p.get("Position", ""), position)]
        found.sort(key=lambda p: float(p.get("Overall", 0) or 0), reverse=True)
        return found[:max(0, limit)]

    def standings(self, season: int | str, competition: str = "Brasileirão") -> list[dict[str, Any]]:
        table: dict[str, dict[str, Any]] = defaultdict(lambda: {"team": "", "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0})
        for m in self.matches:
            if m.season != int(season) or competition.lower() not in m.competition.lower(): continue
            for name, gf, ga in ((m.home_team, m.home_goals, m.away_goals), (m.away_team, m.away_goals, m.home_goals)):
                row = table[normalize_team(name)]; row["team"] = name; row["played"] += 1; row["goals_for"] += gf; row["goals_against"] += ga
                if gf > ga: row["wins"] += 1; row["points"] += 3
                elif gf == ga: row["draws"] += 1; row["points"] += 1
                else: row["losses"] += 1
        rows = list(table.values())
        rows.sort(key=lambda r: (r["points"], r["goals_for"] - r["goals_against"], r["goals_for"]), reverse=True)
        for i, row in enumerate(rows, 1): row["position"] = i
        return rows

    def statistics(self, competition: str | None = None, season: int | str | None = None) -> dict[str, Any]:
        games = [m for m in self.matches if (not competition or competition.lower() in m.competition.lower()) and (season is None or m.season == int(season))]
        goals = sum(m.home_goals + m.away_goals for m in games)
        return {"matches": len(games), "total_goals": goals, "average_goals": round(goals / len(games), 3) if games else 0.0,
                "home_wins": sum(m.home_goals > m.away_goals for m in games), "away_wins": sum(m.away_goals > m.home_goals for m in games),
                "draws": sum(m.home_goals == m.away_goals for m in games)}

    def biggest_wins(self, competition: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        games = [m for m in self.matches if not competition or competition.lower() in m.competition.lower()]
        return [m.as_dict() for m in sorted(games, key=lambda m: (abs(m.home_goals - m.away_goals), m.home_goals + m.away_goals), reverse=True)[:limit]]

