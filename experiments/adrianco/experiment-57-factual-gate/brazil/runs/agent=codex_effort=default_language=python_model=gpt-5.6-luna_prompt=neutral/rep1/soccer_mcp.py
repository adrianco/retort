"""Brazilian soccer data service and optional MCP server.

The query layer intentionally uses only the Python standard library.  The MCP
adapter is optional so the data and statistics remain easy to test offline.
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


COMPETITION_FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "copa_do_brasil": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
}
COMPETITION_ALIASES = {"serie a": "brasileirao", "brasileirao serie a": "brasileirao", "brasileirao": "brasileirao", "copa do brasil": "copa_do_brasil", "copa brasil": "copa_do_brasil", "libertadores": "libertadores", "copa libertadores": "libertadores"}


def _key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    text = re.sub(r"\s+", " ", text).strip().lower()
    text = re.sub(r"\s*-\s*[a-z]{2}$", "", text)
    return text


def _competition(value: Any) -> str:
    raw = _key(value).replace("_", " ")
    return COMPETITION_ALIASES.get(raw, raw.replace(" ", "_"))


def _number(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _date(value: Any) -> dt.date | None:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%YT%H:%M:%S"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _same_team(left: Any, right: Any) -> bool:
    """Match common dataset naming variants without hard-coding club names."""
    a, b = _key(left), _key(right)
    return bool(a and b) and (a == b or a in b or b in a)


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k).strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


class SoccerData:
    """Load the supplied datasets and expose deterministic domain queries."""

    def __init__(self, data_dir: str | Path = "data/kaggle") -> None:
        self.data_dir = Path(data_dir)
        self.matches_data: list[dict[str, Any]] = []
        for competition, filename in COMPETITION_FILES.items():
            path = self.data_dir / filename
            if not path.exists():
                continue
            for row in _read(path):
                self.matches_data.append(self._match(row, competition))
        historical = self.data_dir / "novo_campeonato_brasileiro.csv"
        if historical.exists():
            for row in _read(historical):
                self.matches_data.append(self._historical_match(row))
        extended = self.data_dir / "BR-Football-Dataset.csv"
        if extended.exists():
            self.extended_data = _read(extended)
        else:
            self.extended_data = []
        players = self.data_dir / "fifa_data.csv"
        self.players_data = _read(players) if players.exists() else []

    @staticmethod
    def _match(row: dict[str, str], competition: str) -> dict[str, Any]:
        return {
            "competition": competition,
            "date": row.get("datetime", ""), "date_value": _date(row.get("datetime")),
            "home_team": row.get("home_team", ""), "away_team": row.get("away_team", ""),
            "home_goal": _number(row.get("home_goal")), "away_goal": _number(row.get("away_goal")),
            "season": _number(row.get("season")), "round": row.get("round", ""),
            "stage": row.get("stage", ""),
        }

    @staticmethod
    def _historical_match(row: dict[str, str]) -> dict[str, Any]:
        return {
            "competition": "brasileirao", "date": row.get("Data", ""), "date_value": _date(row.get("Data")),
            "home_team": row.get("Equipe_mandante", ""), "away_team": row.get("Equipe_visitante", ""),
            "home_goal": _number(row.get("Gols_mandante")), "away_goal": _number(row.get("Gols_visitante")),
            "season": _number(row.get("Ano")), "round": row.get("Rodada", ""), "stage": "",
        }

    @staticmethod
    def _public_match(row: dict[str, Any]) -> dict[str, Any]:
        return {k: v.isoformat() if isinstance(v, dt.date) else v for k, v in row.items() if k != "date_value"}

    def matches(self, team: str | None = None, opponent: str | None = None,
                start_date: str | None = None, end_date: str | None = None,
                competition: str | None = None, season: int | None = None,
                limit: int = 100) -> list[dict[str, Any]]:
        team_key, opponent_key = _key(team), _key(opponent)
        start, end = _date(start_date), _date(end_date)
        rows = []
        for row in self.matches_data:
            homes, aways = _key(row["home_team"]), _key(row["away_team"])
            if team and not (_same_team(team, homes) or _same_team(team, aways)):
                continue
            if opponent and not ((_same_team(team, homes) and _same_team(opponent, aways)) or
                                 (_same_team(team, aways) and _same_team(opponent, homes))):
                continue
            if competition and _competition(competition) != row["competition"]:
                continue
            if season is not None and row["season"] != int(season):
                continue
            if start and (row["date_value"] is None or row["date_value"] < start):
                continue
            if end and (row["date_value"] is None or row["date_value"] > end):
                continue
            rows.append(row)
        rows.sort(key=lambda r: (r["date_value"] or dt.date.min, r["home_team"]))
        return [self._public_match(r) for r in rows[: max(0, limit)]]

    def team_stats(self, team: str, season: int | None = None, competition: str | None = None,
                   venue: str = "any") -> dict[str, Any]:
        wanted = _key(team)
        rows = [r for r in self.matches_data if (not season or r["season"] == int(season)) and
                (not competition or _competition(competition) == r["competition"]) and
                ((venue == "home" and _same_team(r["home_team"], wanted)) or
                 (venue == "away" and _same_team(r["away_team"], wanted)) or
                 (venue == "any" and (_same_team(r["home_team"], wanted) or
                                      _same_team(r["away_team"], wanted))))]
        stats = {"team": team, "matches": len(rows), "wins": 0, "draws": 0, "losses": 0,
                 "goals_for": 0, "goals_against": 0}
        for r in rows:
            home = _same_team(r["home_team"], wanted)
            gf, ga = (r["home_goal"], r["away_goal"]) if home else (r["away_goal"], r["home_goal"])
            stats["goals_for"] += gf; stats["goals_against"] += ga
            if gf > ga: stats["wins"] += 1
            elif gf == ga: stats["draws"] += 1
            else: stats["losses"] += 1
        stats["win_rate"] = round(stats["wins"] / stats["matches"] * 100, 1) if rows else 0.0
        return stats

    def head_to_head(self, team_a: str, team_b: str, start_date: str | None = None,
                     end_date: str | None = None, competition: str | None = None,
                     season: int | None = None, limit: int = 100000) -> dict[str, Any]:
        rows = self.matches(team=team_a, opponent=team_b, start_date=start_date,
                            end_date=end_date, competition=competition, season=season,
                            limit=limit)
        a, b = _key(team_a), _key(team_b)
        result = {"team_a": team_a, "team_b": team_b, "matches": rows, "team_a_wins": 0, "team_b_wins": 0, "draws": 0}
        for r in rows:
            a_home = _same_team(r["home_team"], a)
            diff = r["home_goal"] - r["away_goal"]
            if diff == 0: result["draws"] += 1
            elif (diff > 0) == a_home: result["team_a_wins"] += 1
            else: result["team_b_wins"] += 1
        return result

    def players(self, name: str | None = None, nationality: str | None = None,
                club: str | None = None, position: str | None = None,
                min_overall: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
        def contains(row: dict[str, str], field: str, value: str | None) -> bool:
            return not value or _key(value) in _key(row.get(field, ""))
        out = []
        for row in self.players_data:
            if not contains(row, "Name", name) or not contains(row, "Nationality", nationality) or not contains(row, "Club", club) or not contains(row, "Position", position): continue
            if min_overall is not None and _number(row.get("Overall")) < min_overall: continue
            item = {k: row[k] for k in ("ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position") if k in row}
            item["Overall"] = _number(item.get("Overall")); out.append(item)
        out.sort(key=lambda p: (-p["Overall"], p.get("Name", "")))
        return out[:max(0, limit)]

    def standings(self, season: int, competition: str = "brasileirao") -> list[dict[str, Any]]:
        table: dict[str, dict[str, Any]] = defaultdict(lambda: {"team": "", "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0})
        for r in self.matches_data:
            if r["season"] != int(season) or _competition(competition) != r["competition"]: continue
            for side, gf, ga in ((r["home_team"], r["home_goal"], r["away_goal"]), (r["away_team"], r["away_goal"], r["home_goal"])):
                t = table[_key(side)]; t["team"] = side; t["played"] += 1; t["goals_for"] += gf; t["goals_against"] += ga
                if gf > ga: t["wins"] += 1; t["points"] += 3
                elif gf == ga: t["draws"] += 1; t["points"] += 1
                else: t["losses"] += 1
        result = list(table.values())
        result.sort(key=lambda x: (-x["points"], -(x["goals_for"] - x["goals_against"]), -x["goals_for"], x["team"]))
        for i, row in enumerate(result, 1): row["position"] = i; row["goal_difference"] = row["goals_for"] - row["goals_against"]
        return result

    def statistics(self, competition: str | None = None, season: int | None = None, limit: int = 10) -> dict[str, Any]:
        rows = [r for r in self.matches_data if (not competition or _competition(competition) == r["competition"]) and (season is None or r["season"] == int(season))]
        biggest = sorted(rows, key=lambda r: (-(abs(r["home_goal"] - r["away_goal"])), -(r["home_goal"] + r["away_goal"])))[:limit]
        return {"matches": len(rows), "average_goals": round(sum(r["home_goal"] + r["away_goal"] for r in rows) / len(rows), 3) if rows else 0.0,
                "home_wins": sum(r["home_goal"] > r["away_goal"] for r in rows), "away_wins": sum(r["away_goal"] > r["home_goal"] for r in rows),
                "draws": sum(r["home_goal"] == r["away_goal"] for r in rows), "biggest_wins": [self._public_match(r) for r in biggest]}

    def extended_matches(self, tournament: str | None = None, home_team: str | None = None, away_team: str | None = None, season: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
        out = []
        for row in self.extended_data:
            if tournament and _key(tournament) not in _key(row.get("tournament")): continue
            if home_team and _key(home_team) not in _key(row.get("home")): continue
            if away_team and _key(away_team) not in _key(row.get("away")): continue
            date = _date(row.get("date"))
            if season is not None and (date is None or date.year != int(season)): continue
            item = dict(row); item["home_goal"] = _number(row.get("home_goal")); item["away_goal"] = _number(row.get("away_goal")); out.append(item)
        return out[:max(0, limit)]

    def ask(self, question: str, limit: int = 20) -> dict[str, Any]:
        """Handle common natural-language questions without requiring an LLM."""
        low = _key(question); found = re.search(r"\b(19|20)\d{2}\b", question); season = int(found.group()) if found else None
        if "player" in low or "jogador" in low:
            return {"type": "players", "results": self.players(nationality="Brazil" if "brazil" in low or "brasileir" in low else None, limit=limit)}
        if "standings" in low or "classificacao" in low or "tabela" in low:
            if season is None: raise ValueError("A season is required for standings questions")
            return {"type": "standings", "season": season, "results": self.standings(season)}
        if "average" in low or "media" in low or "biggest" in low:
            return {"type": "statistics", "results": self.statistics(season=season, limit=limit)}
        return {"type": "matches", "results": self.matches(season=season, limit=limit)}


def create_server(data_dir: str | Path = "data/kaggle") -> Any:
    """Create the FastMCP server and register the public soccer tools."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("MCP support requires the 'mcp' package; install requirements.txt") from exc
    data = SoccerData(data_dir)
    server = FastMCP("Brazilian Soccer")
    server.tool()(data.matches); server.tool()(data.team_stats); server.tool()(data.head_to_head)
    server.tool()(data.players); server.tool()(data.standings); server.tool()(data.statistics)
    server.tool()(data.extended_matches); server.tool()(data.ask)
    return server


def main(argv: list[str] | None = None) -> None:
    """Run the MCP server over stdio, using data beside this source by default."""
    args = list(sys.argv[1:] if argv is None else argv)
    data_dir = Path(args[0]) if args else Path(__file__).resolve().parent / "data" / "kaggle"
    create_server(data_dir).run(transport="stdio")


if __name__ == "__main__":
    main()
