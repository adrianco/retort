"""Query operations for the Brazilian soccer knowledge graph.

The service is intentionally independent of MCP transport.  It can therefore
be tested as ordinary Python while the MCP layer only maps typed tool arguments
to these deterministic operations.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Any, Final, Iterable, Mapping, Sequence

from .models import MatchRecord, PlayerRecord
from .normalization import (
    clean_text,
    contains_normalized,
    display_competition,
    normalize_competition,
    normalize_team,
    normalize_text,
    parse_query_date,
)
from .repository import SoccerCatalog, load_catalog


class QueryValidationError(ValueError):
    """Raised for invalid user-supplied query parameters."""


_SOURCE_PRIORITY: Final[dict[str, int]] = {
    "brasileirao_matches": 0,
    "brazilian_cup_matches": 0,
    "libertadores_matches": 0,
    "historical_brasileirao": 1,
    "extended_match_statistics": 2,
}
_MAX_LIMIT: Final[int] = 100
_DEFAULT_LIMIT: Final[int] = 25

# The source datasets do not label derbies.  This compact mapping makes that
# judgement explicit and keeps it testable rather than inferred from names.
RIVALRIES: Final[dict[frozenset[str], str]] = {
    frozenset({"flamengo", "fluminense"}): "Fla-Flu",
    frozenset({"corinthians", "palmeiras"}): "Derby Paulista",
    frozenset({"corinthians", "sao paulo"}): "Majestoso",
    frozenset({"palmeiras", "sao paulo"}): "Choque-Rei",
    frozenset({"palmeiras", "santos"}): "Clássico da Saudade",
    frozenset({"santos", "sao paulo"}): "San-São",
    frozenset({"gremio", "internacional"}): "Gre-Nal",
    frozenset({"atletico mineiro", "cruzeiro"}): "Clássico Mineiro",
    frozenset({"athletico", "coritiba"}): "Atletiba",
    frozenset({"bahia", "vitoria"}): "Ba-Vi",
}

_POSITION_GROUPS: Final[dict[str, frozenset[str]]] = {
    "goalkeeper": frozenset({"gk"}),
    "goalkeepers": frozenset({"gk"}),
    "goalie": frozenset({"gk"}),
    "forward": frozenset({"st", "cf", "lw", "rw", "lf", "rf"}),
    "forwards": frozenset({"st", "cf", "lw", "rw", "lf", "rf"}),
    "striker": frozenset({"st", "cf"}),
    "strikers": frozenset({"st", "cf"}),
    "midfielder": frozenset({"cam", "cm", "cdm", "lm", "rm", "lam", "ram", "lcm", "rcm", "ldm", "rdm"}),
    "midfielders": frozenset({"cam", "cm", "cdm", "lm", "rm", "lam", "ram", "lcm", "rcm", "ldm", "rdm"}),
    "defender": frozenset({"cb", "lcb", "rcb", "lb", "rb", "lwb", "rwb"}),
    "defenders": frozenset({"cb", "lcb", "rcb", "lb", "rb", "lwb", "rwb"}),
}


@dataclass(slots=True)
class SoccerQueryService:
    """Fast, deterministic queries over a loaded :class:`SoccerCatalog`."""

    catalog: SoccerCatalog

    @classmethod
    def from_data_directory(cls, data_directory: str | Path | None = None) -> "SoccerQueryService":
        return cls(catalog=load_catalog(data_directory))

    def data_summary(self) -> dict[str, Any]:
        """Describe loaded data, coverage, source files, and attribution scope."""

        return {
            "match_rows": self.catalog.match_count,
            "player_rows": self.catalog.player_count,
            "source_row_counts": self.catalog.source_row_counts,
            "source_files": self.catalog.source_files,
            "competitions": sorted(
                {match.competition for match in self.catalog.matches}, key=normalize_text
            ),
            "data_directory": str(self.catalog.data_directory),
            "data_note": "Results are calculated only from the bundled dataset snapshots, not live soccer data.",
            "attribution": {
                "Brasileirao_Matches.csv": "Kaggle / ricardomattos05, CC BY 4.0",
                "Brazilian_Cup_Matches.csv": "Kaggle / ricardomattos05, CC BY 4.0",
                "Libertadores_Matches.csv": "Kaggle / ricardomattos05, CC BY 4.0",
                "BR-Football-Dataset.csv": "Kaggle / cuecacuela, CC0",
                "novo_campeonato_brasileiro.csv": "Kaggle / macedojleo, CC BY 4.0",
                "fifa_data.csv": "Kaggle / youssefelbadry10, Apache 2.0",
            },
        }

    def entity_graph(
        self,
        entity_type: str,
        name: str,
        *,
        season: int | None = None,
        competition: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Return a compact, provenance-preserving subgraph for a team or player.

        This makes the underlying domain relationships explicit for MCP clients:
        teams participate in matches, matches belong to competitions/seasons, and
        players have a FIFA club *snapshot* relationship.
        """

        kind = normalize_text(entity_type)
        safe_limit = self._validate_limit(limit)
        if kind in {"team", "club"}:
            team_key = self._require_team(name)
            records = self._sort_matches(
                self._filter_matches(
                    team=name,
                    season=season,
                    competition=competition,
                )
            )[:safe_limit]
            display = self._display_team_name(team_key, records) or clean_text(name)
            nodes: dict[str, dict[str, Any]] = {
                f"team:{team_key}": {"id": f"team:{team_key}", "type": "Team", "label": display}
            }
            edges: list[dict[str, Any]] = []
            for record in records:
                match_id = f"match:{record.id}"
                competition_id = f"competition:{record.competition_key}"
                nodes[match_id] = {
                    "id": match_id,
                    "type": "Match",
                    "label": f"{record.home_team} vs {record.away_team}",
                    "source": record.source_file,
                    "date": record.match_date.isoformat() if record.match_date else None,
                }
                nodes[competition_id] = {
                    "id": competition_id,
                    "type": "Competition",
                    "label": record.competition,
                }
                edges.append(
                    {
                        "from": match_id,
                        "to": competition_id,
                        "type": "IN_COMPETITION",
                    }
                )
                if record.season is not None:
                    season_id = f"season:{record.season}"
                    nodes[season_id] = {
                        "id": season_id,
                        "type": "Season",
                        "label": str(record.season),
                    }
                    edges.append({"from": match_id, "to": season_id, "type": "IN_SEASON"})
                if record.home_team_key == team_key:
                    edges.append({"from": f"team:{team_key}", "to": match_id, "type": "HOME_TEAM"})
                    opponent_key, opponent = record.away_team_key, record.away_team
                else:
                    edges.append({"from": f"team:{team_key}", "to": match_id, "type": "AWAY_TEAM"})
                    opponent_key, opponent = record.home_team_key, record.home_team
                opponent_id = f"team:{opponent_key}"
                nodes.setdefault(opponent_id, {"id": opponent_id, "type": "Team", "label": opponent})
                edges.append({"from": match_id, "to": opponent_id, "type": "OPPONENT"})
            return {
                "entity_type": "team",
                "entity": display,
                "nodes": list(nodes.values()),
                "edges": edges,
                "match_count": len(records),
                "limit": safe_limit,
                "formatted_answer": (
                    f"Knowledge graph subgraph for {display}: {len(nodes)} nodes and {len(edges)} edges "
                    f"from {len(records)} source match rows."
                ),
            }
        if kind in {"player", "fifa player"}:
            players = self.search_players(name=name, limit=safe_limit)["players"]
            nodes: list[dict[str, Any]] = []
            edges: list[dict[str, Any]] = []
            for record in players:
                player_id = f"player:{record['id']}"
                club_id = f"fifa_club:{normalize_team(record['club'])}"
                nodes.extend(
                    [
                        {"id": player_id, "type": "Player", "label": record["name"]},
                        {"id": club_id, "type": "FIFAClubSnapshot", "label": record["club"]},
                    ]
                )
                edges.append(
                    {"from": player_id, "to": club_id, "type": "FIFA_CLUB_SNAPSHOT"}
                )
            return {
                "entity_type": "player",
                "entity": clean_text(name),
                "nodes": nodes,
                "edges": edges,
                "note": "FIFA club snapshot edges do not establish historical match lineups.",
                "formatted_answer": f"Knowledge graph subgraph for {clean_text(name)}: {len(nodes)} nodes and {len(edges)} edges.",
            }
        raise QueryValidationError("entity_type must be either 'team' or 'player'.")

    def search_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        venue: str = "any",
        round_contains: str | None = None,
        stage_contains: str | None = None,
        source: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Find matches using composable filters and preserve row provenance."""

        records = self._filter_matches(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            start_date=start_date,
            end_date=end_date,
            venue=venue,
            round_contains=round_contains,
            stage_contains=stage_contains,
            source=source,
        )
        records = self._sort_matches(records)
        safe_limit = self._validate_limit(limit)
        result = records[:safe_limit]
        filters = self._filters_dict(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            start_date=start_date,
            end_date=end_date,
            venue=venue,
            round_contains=round_contains,
            stage_contains=stage_contains,
            source=source,
        )
        answer = self._format_matches(result, total=len(records), filters=filters)
        response: dict[str, Any] = {
            "total_matches": len(records),
            "returned_matches": len(result),
            "limit": safe_limit,
            "filters": filters,
            "matches": [match.as_dict() for match in result],
            "formatted_answer": answer,
        }
        if team and not records:
            response["team_suggestions"] = self.suggest_teams(team)
        return response

    def team_statistics(
        self,
        team: str,
        *,
        season: int | None = None,
        competition: str | None = None,
        venue: str = "any",
        source: str | None = None,
        deduplicate: bool = True,
    ) -> dict[str, Any]:
        """Calculate wins, draws, losses, goals, and win rate for one team."""

        team_key = self._require_team(team)
        records = self._filter_matches(
            team=team,
            competition=competition,
            season=season,
            venue=venue,
            source=source,
        )
        if deduplicate:
            records = self._coherent_records(records)
        statistics = self._record_for_team(team_key, records)
        display_name = self._display_team_name(team_key, records) or clean_text(team)
        result = {
            "team": display_name,
            "team_key": team_key,
            "scope": self._filters_dict(
                competition=competition,
                season=season,
                venue=venue,
                source=source,
            ),
            "deduplicated_cross_source_matches": deduplicate,
            "source_selection_policy": (
                "For each competition-season aggregate, use the source with the most complete rows; "
                "ties use documented source priority."
                if deduplicate
                else "Raw source rows were intentionally retained."
            ),
            **statistics,
        }
        result["formatted_answer"] = self._format_team_statistics(result)
        if not records:
            result["team_suggestions"] = self.suggest_teams(team)
        return result

    def compare_teams(
        self,
        team_a: str,
        team_b: str,
        *,
        competition: str | None = None,
        season: int | None = None,
        source: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Return orientation-independent head-to-head results for two teams."""

        key_a = self._require_team(team_a)
        key_b = self._require_team(team_b)
        if key_a == key_b:
            raise QueryValidationError("team_a and team_b must identify different teams.")
        records = self._filter_matches(
            team=team_a,
            opponent=team_b,
            competition=competition,
            season=season,
            source=source,
        )
        records = self._coherent_records(records)
        records = self._sort_matches(records)

        wins_a = wins_b = draws = 0
        for match in records:
            if not match.is_complete:
                continue
            winner = self._winner_key(match)
            if winner is None:
                draws += 1
            elif winner == key_a:
                wins_a += 1
            elif winner == key_b:
                wins_b += 1

        name_a = self._display_team_name(key_a, records) or clean_text(team_a)
        name_b = self._display_team_name(key_b, records) or clean_text(team_b)
        safe_limit = self._validate_limit(limit)
        rivalry = RIVALRIES.get(frozenset({key_a, key_b}))
        result: dict[str, Any] = {
            "team_a": name_a,
            "team_b": name_b,
            "rivalry": rivalry,
            "total_matches": len(records),
            "head_to_head": {"team_a_wins": wins_a, "team_b_wins": wins_b, "draws": draws},
            "filters": self._filters_dict(
                competition=competition, season=season, source=source
            ),
            "matches": [match.as_dict() for match in records[:safe_limit]],
            "limit": safe_limit,
        }
        result["formatted_answer"] = self._format_head_to_head(result)
        return result

    def search_players(
        self,
        *,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Find FIFA players by normalized identity, club, position, and ratings."""

        records: Sequence[PlayerRecord] = self.catalog.players
        if name:
            name_key = normalize_text(name)
            exact = self.catalog.players_by_name.get(name_key)
            records = exact if exact is not None else records
            records = [player for player in records if name_key in player.name_key]
        if nationality:
            needle = normalize_text(nationality)
            records = [
                player
                for player in records
                if needle in player.nationality_key
            ]
        if club:
            club_key = normalize_team(club)
            records = [player for player in records if club_key in player.club_key]
        if position:
            position_key = normalize_text(position)
            group = _POSITION_GROUPS.get(position_key)
            if group:
                records = [
                    player for player in records if normalize_text(player.position) in group
                ]
            else:
                records = [
                    player
                    for player in records
                    if position_key in normalize_text(player.position)
                ]
        if min_overall is not None:
            records = [
                player for player in records if player.overall is not None and player.overall >= min_overall
            ]
        if max_overall is not None:
            records = [
                player for player in records if player.overall is not None and player.overall <= max_overall
            ]

        ordered = sorted(
            records,
            key=lambda player: (
                -(player.overall if player.overall is not None else -1),
                player.name_key,
                player.id,
            ),
        )
        safe_limit = self._validate_limit(limit)
        result = ordered[:safe_limit]
        filters = self._filters_dict(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_overall=max_overall,
        )
        response: dict[str, Any] = {
            "total_players": len(ordered),
            "returned_players": len(result),
            "limit": safe_limit,
            "filters": filters,
            "players": [player.as_dict() for player in result],
            "formatted_answer": self._format_players(result, total=len(ordered), filters=filters),
        }
        if name and not ordered:
            response["player_suggestions"] = self.suggest_players(name)
        return response

    def compare_players(self, player_a: str, player_b: str) -> dict[str, Any]:
        """Return comparable FIFA attributes for two named players."""

        first = self.search_players(name=player_a, limit=5)
        second = self.search_players(name=player_b, limit=5)
        response = {
            "player_a_query": player_a,
            "player_b_query": player_b,
            "player_a_matches": first["players"],
            "player_b_matches": second["players"],
        }
        response["formatted_answer"] = (
            f"FIFA player comparison for {clean_text(player_a)} and {clean_text(player_b)}. "
            "Club values are snapshots in the FIFA dataset, not historical lineups."
        )
        return response

    def competition_standings(
        self,
        season: int,
        *,
        competition: str = "Brasileirão",
        source: str | None = None,
    ) -> dict[str, Any]:
        """Calculate a deterministic points table from a coherent match set."""

        if season < 1888 or season > 2100:
            raise QueryValidationError("season must be a plausible four-digit year.")
        records = self._filter_matches(
            competition=competition, season=season, source=source
        )
        records = self._coherent_records(records)
        table: dict[str, dict[str, Any]] = {}

        for match in records:
            if not match.is_complete:
                continue
            home = table.setdefault(match.home_team_key, self._empty_table_row(match.home_team))
            away = table.setdefault(match.away_team_key, self._empty_table_row(match.away_team))
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += match.home_goals  # type: ignore[operator]
            home["goals_against"] += match.away_goals  # type: ignore[operator]
            away["goals_for"] += match.away_goals  # type: ignore[operator]
            away["goals_against"] += match.home_goals  # type: ignore[operator]
            if match.home_goals > match.away_goals:  # type: ignore[operator]
                home["wins"] += 1
                home["points"] += 3
                away["losses"] += 1
            elif match.home_goals < match.away_goals:  # type: ignore[operator]
                away["wins"] += 1
                away["points"] += 3
                home["losses"] += 1
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        rows = []
        for row in table.values():
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
            rows.append(row)
        rows.sort(
            key=lambda row: (
                -row["points"],
                -row["wins"],
                -row["goal_difference"],
                -row["goals_for"],
                normalize_text(row["team"]),
            )
        )
        for position, row in enumerate(rows, start=1):
            row["position"] = position

        complete = self._is_likely_complete_brasileirao(records, competition)
        scope = self._filters_dict(competition=competition, season=season, source=source)
        result: dict[str, Any] = {
            "competition": display_competition(competition),
            "season": season,
            "match_count": len(records),
            "standings": rows,
            "calculated_from_loaded_data": True,
            "deduplicated_cross_source_matches": True,
            "tie_breakers": ["points", "wins", "goal difference", "goals for", "team name"],
            "coverage_complete_for_relegation": complete,
            "scope": scope,
        }
        if not complete:
            result["coverage_note"] = (
                "The loaded match set appears incomplete for a full league-table claim; "
                "treat this as a partial calculated table."
            )
        result["formatted_answer"] = self._format_standings(result)
        return result

    def competition_statistics(
        self,
        *,
        competition: str | None = None,
        season: int | None = None,
        source: str | None = None,
        biggest_wins_limit: int = 10,
    ) -> dict[str, Any]:
        """Compute goal, home/away, and largest-margin statistics."""

        records = self._filter_matches(
            competition=competition, season=season, source=source
        )
        records = self._coherent_records(records)
        complete = [match for match in records if match.is_complete]
        total_goals = sum(
            (match.home_goals or 0) + (match.away_goals or 0) for match in complete
        )
        home_wins = sum(1 for match in complete if match.home_goals > match.away_goals)  # type: ignore[operator]
        away_wins = sum(1 for match in complete if match.home_goals < match.away_goals)  # type: ignore[operator]
        draws = len(complete) - home_wins - away_wins
        safe_limit = self._validate_limit(biggest_wins_limit)
        biggest = sorted(
            complete,
            key=lambda match: (
                -(match.goal_margin or 0),
                match.match_date or date.min,
                match.id,
            ),
        )[:safe_limit]
        result: dict[str, Any] = {
            "scope": self._filters_dict(
                competition=competition, season=season, source=source
            ),
            "complete_match_count": len(complete),
            "total_goals": total_goals,
            "average_goals_per_match": round(total_goals / len(complete), 3) if complete else 0.0,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": _percentage(home_wins, len(complete)),
            "away_win_rate": _percentage(away_wins, len(complete)),
            "biggest_wins": [match.as_dict() for match in biggest],
            "deduplicated_cross_source_matches": True,
        }
        result["formatted_answer"] = self._format_competition_statistics(result)
        return result

    def best_team_record(
        self,
        *,
        venue: str = "any",
        competition: str | None = None,
        season: int | None = None,
        source: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Rank teams by points per match, then win rate and goal difference."""

        normalized_venue = self._validate_venue(venue)
        records = self._filter_matches(
            competition=competition, season=season, source=source
        )
        records = self._coherent_records(records)
        rows: dict[str, dict[str, Any]] = {}
        for match in records:
            if not match.is_complete:
                continue
            candidates: list[tuple[str, str, int, int]] = []
            if normalized_venue in {"any", "home"}:
                candidates.append(
                    (match.home_team_key, match.home_team, match.home_goals, match.away_goals)  # type: ignore[arg-type]
                )
            if normalized_venue in {"any", "away"}:
                candidates.append(
                    (match.away_team_key, match.away_team, match.away_goals, match.home_goals)  # type: ignore[arg-type]
                )
            for key, display, goals_for, goals_against in candidates:
                row = rows.setdefault(key, self._empty_team_record(display))
                row["matches"] += 1
                row["goals_for"] += goals_for
                row["goals_against"] += goals_against
                if goals_for > goals_against:
                    row["wins"] += 1
                    row["points"] += 3
                elif goals_for < goals_against:
                    row["losses"] += 1
                else:
                    row["draws"] += 1
                    row["points"] += 1
        ranking = []
        for row in rows.values():
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
            row["win_rate"] = _percentage(row["wins"], row["matches"])
            row["points_per_match"] = round(row["points"] / row["matches"], 3)
            ranking.append(row)
        ranking.sort(
            key=lambda row: (
                -row["points_per_match"],
                -row["win_rate"],
                -row["goal_difference"],
                -row["goals_for"],
                normalize_text(row["team"]),
            )
        )
        safe_limit = self._validate_limit(limit)
        return {
            "venue": normalized_venue,
            "ranking_metric": "points per match; ties use win rate, goal difference, goals for, then team name",
            "scope": self._filters_dict(
                competition=competition, season=season, source=source
            ),
            "teams": ranking[:safe_limit],
            "total_teams": len(ranking),
            "formatted_answer": self._format_best_records(ranking[:safe_limit], normalized_venue),
        }

    def relegated_teams(
        self,
        season: int,
        *,
        competition: str = "Brasileirão",
        number_of_teams: int = 4,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Return the bottom teams only when coverage looks complete."""

        if number_of_teams < 1 or number_of_teams > 10:
            raise QueryValidationError("number_of_teams must be between 1 and 10.")
        standings = self.competition_standings(
            season, competition=competition, source=source
        )
        if not standings["coverage_complete_for_relegation"]:
            return {
                "season": season,
                "competition": standings["competition"],
                "relegation_status": "not_determined",
                "reason": standings.get("coverage_note"),
                "standings": standings["standings"],
                "formatted_answer": (
                    "Relegation cannot be determined reliably because the loaded season coverage "
                    "is incomplete."
                ),
            }
        relegated = standings["standings"][-number_of_teams:]
        return {
            "season": season,
            "competition": standings["competition"],
            "relegation_status": "calculated_from_loaded_data",
            "teams": relegated,
            "formatted_answer": (
                f"Bottom {number_of_teams} in the calculated {standings['competition']} {season} table: "
                + ", ".join(row["team"] for row in relegated)
            ),
        }

    def libertadores_by_stage(
        self, season: int, *, limit_per_stage: int = 100
    ) -> dict[str, Any]:
        """Group loaded Libertadores results by the supplied stage values."""

        records = self._filter_matches(
            competition="Copa Libertadores", season=season
        )
        records = self._sort_matches(records)
        grouped: dict[str, list[MatchRecord]] = defaultdict(list)
        for record in records:
            grouped[record.stage or "Unspecified stage"].append(record)
        safe_limit = self._validate_limit(limit_per_stage)
        stages = {
            stage: [match.as_dict() for match in matches[:safe_limit]]
            for stage, matches in sorted(grouped.items(), key=lambda item: normalize_text(item[0]))
        }
        return {
            "competition": "Copa Libertadores",
            "season": season,
            "stages": stages,
            "note": (
                "This is a stage-grouped result list from dataset rows, not an inferred knockout bracket "
                "or aggregate-score calculation."
            ),
            "formatted_answer": f"Loaded Copa Libertadores {season} results grouped into {len(stages)} stages.",
        }

    def team_competitions(self, team: str, *, source: str | None = None) -> dict[str, Any]:
        """List competitions in which the given team appears in the match data."""

        records = self._filter_matches(team=team, source=source)
        grouped: dict[str, int] = defaultdict(int)
        for record in records:
            grouped[record.competition] += 1
        return {
            "team": self._display_team_name(normalize_team(team), records) or clean_text(team),
            "competitions": [
                {"competition": competition, "match_count": count}
                for competition, count in sorted(grouped.items(), key=lambda item: normalize_text(item[0]))
            ],
            "formatted_answer": (
                f"{clean_text(team)} appears in: "
                + (", ".join(sorted(grouped, key=normalize_text)) if grouped else "no loaded match records")
            ),
        }

    def derby_matches(
        self, *, season: int | None = None, limit: int = _DEFAULT_LIMIT
    ) -> dict[str, Any]:
        """Find only pairs explicitly included in :data:`RIVALRIES`."""

        records = self._filter_matches(season=season)
        selected = [
            record
            for record in records
            if frozenset({record.home_team_key, record.away_team_key}) in RIVALRIES
        ]
        selected = self._sort_matches(self._deduplicate(selected))
        safe_limit = self._validate_limit(limit)
        returned = selected[:safe_limit]
        return {
            "season": season,
            "total_matches": len(selected),
            "matches": [
                {**record.as_dict(), "derby": RIVALRIES[frozenset({record.home_team_key, record.away_team_key})]}
                for record in returned
            ],
            "rivalry_mapping": "Explicit curated mapping in brazilian_soccer_mcp.service.RIVALRIES.",
            "formatted_answer": self._format_matches(returned, total=len(selected), filters={"season": season, "derbies": True}),
        }

    def teams_by_goals(
        self,
        *,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Rank teams by total goals across the selected coherent match set."""

        records = self._coherent_records(
            self._filter_matches(competition=competition, season=season)
        )
        goals: dict[str, dict[str, Any]] = {}
        for record in records:
            if not record.is_complete:
                continue
            for key, display, scored in (
                (record.home_team_key, record.home_team, record.home_goals),
                (record.away_team_key, record.away_team, record.away_goals),
            ):
                row = goals.setdefault(key, {"team": display, "goals": 0, "matches": 0})
                row["goals"] += scored  # type: ignore[operator]
                row["matches"] += 1
        ordered = sorted(
            goals.values(), key=lambda row: (-row["goals"], normalize_text(row["team"]))
        )
        safe_limit = self._validate_limit(limit)
        return {
            "scope": self._filters_dict(competition=competition, season=season),
            "ranking_metric": "total goals scored",
            "teams": ordered[:safe_limit],
            "formatted_answer": (
                "Top teams by dataset goals: "
                + "; ".join(
                    f"{row['team']} ({row['goals']})" for row in ordered[:safe_limit]
                )
            ),
        }

    def compare_seasons(
        self,
        first_season: int,
        second_season: int,
        *,
        competition: str = "Brasileirão",
    ) -> dict[str, Any]:
        """Compare match volume, goals, and home/away rates across two seasons."""

        def summary(year: int) -> dict[str, Any]:
            stats = self.competition_statistics(competition=competition, season=year)
            return {
                "season": year,
                "complete_match_count": stats["complete_match_count"],
                "total_goals": stats["total_goals"],
                "average_goals_per_match": stats["average_goals_per_match"],
                "home_win_rate": stats["home_win_rate"],
                "away_win_rate": stats["away_win_rate"],
            }

        first, second = summary(first_season), summary(second_season)
        return {
            "competition": display_competition(competition),
            "seasons": [first, second],
            "formatted_answer": (
                f"{display_competition(competition)} comparison: {first_season} had "
                f"{first['average_goals_per_match']} goals/match; {second_season} had "
                f"{second['average_goals_per_match']} goals/match."
            ),
        }

    def players_at_clubs_faced(
        self,
        team: str,
        season: int,
        *,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Join match opponents to FIFA club snapshots with an explicit caveat."""

        team_key = self._require_team(team)
        records = self._filter_matches(team=team, season=season)
        opponent_keys = {
            record.away_team_key if record.home_team_key == team_key else record.home_team_key
            for record in records
        }
        players = [player for player in self.catalog.players if player.club_key in opponent_keys]
        players.sort(
            key=lambda player: (
                -(player.overall if player.overall is not None else -1), player.name_key
            )
        )
        safe_limit = self._validate_limit(limit)
        return {
            "team": self._display_team_name(team_key, records) or clean_text(team),
            "season": season,
            "opponent_club_keys": sorted(opponent_keys),
            "players": [player.as_dict() for player in players[:safe_limit]],
            "total_players": len(players),
            "note": (
                "This cross-file join matches FIFA club snapshots to opponents in the historical match data. "
                "It is not evidence that any player appeared in those matches."
            ),
            "formatted_answer": f"Found {len(players)} FIFA player records at clubs {clean_text(team)} faced in {season}.",
        }

    def top_scorers_status(self, *, competition: str | None = None, season: int | None = None) -> dict[str, Any]:
        """Truthfully explain that supplied schemas contain no scorer-event data."""

        return {
            "available": False,
            "scope": self._filters_dict(competition=competition, season=season),
            "reason": (
                "The supplied match files contain team final scores but no player-goal events. "
                "FIFA ratings cannot be used to infer scorers."
            ),
            "formatted_answer": "Individual top-scorer data is not available in the supplied datasets.",
        }

    def answer_question(
        self, question: str, *, context: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Route common natural-language questions to deterministic tool operations.

        An MCP client can use this convenience tool directly or let an LLM choose
        the structured operations.  It intentionally asks for clarification when
        a conversational follow-up lacks a prior match in ``context``.
        """

        original = clean_text(question)
        if not original:
            raise QueryValidationError("question must not be empty.")
        normalized = normalize_text(original)
        year = _first_year(normalized)

        if normalized in {"what was the score", "what was the score of that match"}:
            previous = (context or {}).get("last_match")
            if isinstance(previous, Mapping):
                return self._answer_from_context(previous)
            return self._clarification(
                "Please name the teams or pass context.last_match from the preceding match result."
            )

        if "top scorer" in normalized or "top scorers" in normalized:
            return self._answer("top_scorers_unavailable", self.top_scorers_status(season=year))

        if "who won" in normalized and "brasileirao" in normalized and year:
            standings = self.competition_standings(year)
            winner = standings["standings"][0] if standings["standings"] else None
            answer = {
                "season": year,
                "winner": winner,
                "coverage_note": standings.get("coverage_note"),
                "formatted_answer": (
                    f"Calculated {year} Brasileirão leader: {winner['team']}" if winner else "No loaded standings rows found."
                ),
            }
            return self._answer("competition_winner", answer)

        if "final standings" in normalized and "brasileirao" in normalized and year:
            return self._answer("competition_standings", self.competition_standings(year))

        if "relegated" in normalized and year:
            return self._answer("relegated_teams", self.relegated_teams(year))

        if "libertadores" in normalized and ("bracket" in normalized or "stage" in normalized) and year:
            return self._answer("libertadores_by_stage", self.libertadores_by_stage(year))

        if "average goals" in normalized or "goals per match" in normalized:
            return self._answer(
                "competition_statistics",
                self.competition_statistics(
                    competition="Brasileirão" if "brasileirao" in normalized else None,
                    season=year,
                ),
            )

        if "biggest win" in normalized or "biggest victories" in normalized:
            return self._answer("competition_statistics", self.competition_statistics(season=year))

        if "best home record" in normalized:
            return self._answer("best_team_record", self.best_team_record(venue="home", season=year))

        if "best away record" in normalized:
            return self._answer("best_team_record", self.best_team_record(venue="away", season=year))

        if "scored the most goals" in normalized or "most goals" in normalized:
            return self._answer(
                "teams_by_goals",
                self.teams_by_goals(
                    competition="Brasileirão" if any(token in normalized for token in ("serie a", "brasileirao")) else None,
                    season=year,
                ),
            )

        if "competitions has" in normalized or "competitions did" in normalized:
            team = _after_phrase(original, r"competitions\s+(?:has|did)\s+(.+?)(?:\s+play(?:ed)?(?:\s+in)?)?\??$")
            if team:
                return self._answer("team_competitions", self.team_competitions(team))

        if "all derbies" in normalized or "all classics" in normalized:
            return self._answer("derby_matches", self.derby_matches(season=year))

        if "compare the" in normalized and "season" in normalized:
            years = _all_years(normalized)
            if len(years) >= 2:
                return self._answer("compare_seasons", self.compare_seasons(years[0], years[1]))

        if "last play" in normalized:
            pair = _extract_pair_after(original, r"(?:when\s+did\s+)?(.+?)\s+last\s+play\s+(.+?)\??$")
            if pair:
                result = self.search_matches(team=pair[0], opponent=pair[1], limit=1)
                return self._answer("last_match", result)

        if any(token in normalized for token in ("home record", "away record")):
            venue = "home" if "home record" in normalized else "away"
            team = _extract_record_team(original)
            if team:
                return self._answer(
                    "team_statistics",
                    self.team_statistics(team, season=year, venue=venue),
                )

        if ("players play for" in normalized or "players at" in normalized) and "fifa listed" not in normalized:
            club = _after_phrase(original, r"players\s+(?:play\s+for|at)\s+(.+?)\??$")
            if club:
                return self._answer("search_players", self.search_players(club=club))

        if "fifa listed players" in normalized and "faced in" in normalized and year:
            team = _after_phrase(
                original,
                r"clubs\s+(.+?)\s+faced\s+in\s+\d{4}\??$",
            )
            if team:
                return self._answer(
                    "players_at_clubs_faced",
                    self.players_at_clubs_faced(team, year),
                )

        if "highest rated" in normalized and " at " in normalized:
            club = _after_phrase(original, r"(?:highest[\s-]+rated\s+players\s+at)\s+(.+?)\??$")
            if club:
                return self._answer("search_players", self.search_players(club=club))

        if "brazilian players" in normalized:
            club = _after_phrase(original, r"brazilian\s+players\s+(?:at|from)\s+(.+?)\??$")
            return self._answer("search_players", self.search_players(nationality="Brazil", club=club))

        if "all forwards" in normalized or "forwards from" in normalized:
            club = _after_phrase(original, r"forwards?\s+from\s+(.+?)\??$")
            return self._answer("search_players", self.search_players(club=club, position="forward"))

        if normalized.startswith("who is "):
            return self._answer("search_players", self.search_players(name=original[7:]))

        if "compare" in normalized:
            pair = _extract_pair_after(
                original,
                r"compare\s+(.+?)\s+(?:and|vs|versus)\s+(.+?)\??$",
            )
            if pair:
                first_players = self.search_players(name=pair[0], limit=1)
                second_players = self.search_players(name=pair[1], limit=1)
                if first_players["total_players"] and second_players["total_players"]:
                    return self._answer("compare_players", self.compare_players(pair[0], pair[1]))
                return self._answer("compare_teams", self.compare_teams(pair[0], pair[1], season=year))

        if "copa do brasil" in normalized and "final" in normalized:
            return self._answer(
                "match_search",
                self.search_matches(
                    competition="Copa do Brasil", round_contains="final", season=year
                ),
            )

        if "matches did" in normalized and "play" in normalized and year:
            team = _after_phrase(original, r"matches\s+did\s+(.+?)\s+play\s+in\s+\d{4}\??$")
            if team:
                return self._answer("match_search", self.search_matches(team=team, season=year))

        if normalized.startswith("did ") and " play " in normalized and year:
            pair = _extract_pair_after(
                original,
                r"did\s+(.+?)\s+play\s+(.+?)\s+in\s+\d{4}\??$",
            )
            if pair:
                return self._answer(
                    "match_search",
                    self.search_matches(team=pair[0], opponent=pair[1], season=year),
                )

        if any(separator in normalized for separator in (" vs ", " versus ")):
            pair = _extract_vs_pair(original)
            if pair:
                return self._answer("head_to_head", self.compare_teams(pair[0], pair[1], season=year))

        generic_match = _after_phrase(
            original,
            r"(?:show|find|list)(?:\s+me)?(?:\s+all)?\s+(.+?)\s+matches\??$",
        )
        if generic_match:
            return self._answer("match_search", self.search_matches(team=generic_match, season=year))

        return self._clarification(
            "I can search matches, teams, players, standings, and aggregate statistics. "
            "Try naming a team, season, competition, or use a structured MCP tool."
        )

    def suggest_teams(self, query: str, *, limit: int = 8) -> list[str]:
        """Offer deterministic candidates for unknown or underspecified team names."""

        query_key = normalize_team(query)
        displays: dict[str, str] = {}
        for record in self.catalog.matches_by_team.get(query_key, ()):
            displays.setdefault(record.home_team_key, record.home_team)
            displays.setdefault(record.away_team_key, record.away_team)
        if displays:
            return sorted(displays.values(), key=normalize_text)[:limit]

        all_displays: dict[str, str] = {}
        for record in self.catalog.matches:
            all_displays.setdefault(record.home_team_key, record.home_team)
            all_displays.setdefault(record.away_team_key, record.away_team)
        candidates = [
            display
            for key, display in all_displays.items()
            if query_key and (query_key in key or key.startswith(query_key[: max(2, len(query_key) // 2)]))
        ]
        return sorted(candidates, key=normalize_text)[:limit]

    def suggest_players(self, query: str, *, limit: int = 8) -> list[str]:
        """Offer player-name candidates without guessing an identity."""

        key = normalize_text(query)
        candidates = [
            player.name
            for player in self.catalog.players
            if key and (key in player.name_key or player.name_key.startswith(key[: max(2, len(key) // 2)]))
        ]
        return sorted(dict.fromkeys(candidates), key=normalize_text)[:limit]

    def _filter_matches(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        venue: str = "any",
        round_contains: str | None = None,
        stage_contains: str | None = None,
        source: str | None = None,
    ) -> list[MatchRecord]:
        normalized_venue = self._validate_venue(venue)
        try:
            start = parse_query_date(start_date, parameter="start_date")
            end = parse_query_date(end_date, parameter="end_date")
        except ValueError as error:
            raise QueryValidationError(str(error)) from error
        if start and end and start > end:
            raise QueryValidationError("start_date must be on or before end_date.")
        if season is not None and (season < 1888 or season > 2100):
            raise QueryValidationError("season must be a plausible four-digit year.")

        team_key = normalize_team(team) if team else None
        opponent_key = normalize_team(opponent) if opponent else None
        competition_key = normalize_competition(competition) if competition else None
        if team_key:
            records: Iterable[MatchRecord] = self.catalog.matches_by_team.get(team_key, ())
        elif competition_key:
            records = self.catalog.matches_by_competition.get(competition_key, ())
        elif season is not None:
            records = self.catalog.matches_by_season.get(season, ())
        else:
            records = self.catalog.matches

        selected: list[MatchRecord] = []
        for record in records:
            if team_key:
                if normalized_venue == "home" and record.home_team_key != team_key:
                    continue
                if normalized_venue == "away" and record.away_team_key != team_key:
                    continue
            elif normalized_venue != "any":
                raise QueryValidationError("venue requires a team filter.")
            if opponent_key and opponent_key not in {record.home_team_key, record.away_team_key}:
                continue
            if team_key and opponent_key and team_key == opponent_key:
                raise QueryValidationError("team and opponent must identify different teams.")
            if competition_key and record.competition_key != competition_key:
                continue
            if season is not None and record.season != season:
                continue
            if start and (record.match_date is None or record.match_date < start):
                continue
            if end and (record.match_date is None or record.match_date > end):
                continue
            if round_contains:
                round_query = normalize_text(round_contains)
                round_value = normalize_text(record.round)
                if round_query not in round_value:
                    continue
                if round_query == "final" and any(
                    excluded in round_value for excluded in ("semi final", "semifinal")
                ):
                    continue
            if stage_contains:
                stage_query = normalize_text(stage_contains)
                stage_value = normalize_text(record.stage)
                if stage_query not in stage_value:
                    continue
                if stage_query == "final" and any(
                    excluded in stage_value for excluded in ("semi final", "semifinal")
                ):
                    continue
            if source and record.source != source:
                continue
            selected.append(record)
        return selected

    def _record_for_team(self, team_key: str, records: Iterable[MatchRecord]) -> dict[str, Any]:
        wins = draws = losses = goals_for = goals_against = 0
        complete_matches = 0
        for record in records:
            if not record.is_complete:
                continue
            complete_matches += 1
            is_home = record.home_team_key == team_key
            scored = record.home_goals if is_home else record.away_goals
            conceded = record.away_goals if is_home else record.home_goals
            goals_for += scored  # type: ignore[operator]
            goals_against += conceded  # type: ignore[operator]
            if scored > conceded:  # type: ignore[operator]
                wins += 1
            elif scored < conceded:  # type: ignore[operator]
                losses += 1
            else:
                draws += 1
        return {
            "matches": complete_matches,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "points": wins * 3 + draws,
            "win_rate": _percentage(wins, complete_matches),
        }

    def _deduplicate(self, records: Iterable[MatchRecord]) -> list[MatchRecord]:
        """Prevent overlapping source files from silently double-counting games."""

        chosen: dict[tuple[Any, ...], MatchRecord] = {}
        for record in records:
            if not record.is_complete or record.match_date is None:
                key = (record.source, record.id)
            else:
                key = (
                    record.match_date,
                    record.competition_key,
                    record.home_team_key,
                    record.away_team_key,
                    record.home_goals,
                    record.away_goals,
                )
            previous = chosen.get(key)
            if previous is None or _SOURCE_PRIORITY.get(record.source, 99) < _SOURCE_PRIORITY.get(previous.source, 99):
                chosen[key] = record
        return list(chosen.values())

    def _coherent_records(self, records: Iterable[MatchRecord]) -> list[MatchRecord]:
        """Choose one best-covered source per competition and season for aggregates.

        The league and cup source files overlap but do not share a universal
        match id.  Exact-row deduplication alone is unsafe when a rescheduled
        fixture has a different date or naming variant, so aggregate queries
        use a coherent source rather than concatenating overlapping feeds.
        """

        by_scope: dict[tuple[str, int | None], dict[str, list[MatchRecord]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for record in records:
            by_scope[(record.competition_key, record.season)][record.source].append(record)

        selected: list[MatchRecord] = []
        for candidates in by_scope.values():
            _, source_records = min(
                candidates.items(),
                key=lambda item: (
                    -sum(record.is_complete for record in item[1]),
                    -len(item[1]),
                    _SOURCE_PRIORITY.get(item[0], 99),
                    item[0],
                ),
            )
            selected.extend(source_records)
        return self._deduplicate(selected)

    @staticmethod
    def _sort_matches(records: Iterable[MatchRecord]) -> list[MatchRecord]:
        return sorted(
            records,
            key=lambda match: (match.match_date or date.min, match.id),
            reverse=True,
        )

    @staticmethod
    def _validate_limit(limit: int) -> int:
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise QueryValidationError("limit must be an integer.")
        if not 1 <= limit <= _MAX_LIMIT:
            raise QueryValidationError(f"limit must be between 1 and {_MAX_LIMIT}.")
        return limit

    @staticmethod
    def _validate_venue(venue: str) -> str:
        value = normalize_text(venue or "any")
        aliases = {"either": "any", "all": "any"}
        value = aliases.get(value, value)
        if value not in {"any", "home", "away"}:
            raise QueryValidationError("venue must be one of: any, home, away.")
        return value

    @staticmethod
    def _require_team(team: str) -> str:
        key = normalize_team(team)
        if not key:
            raise QueryValidationError("team must not be empty.")
        return key

    @staticmethod
    def _winner_key(record: MatchRecord) -> str | None:
        if not record.is_complete or record.home_goals == record.away_goals:
            return None
        return record.home_team_key if record.home_goals > record.away_goals else record.away_team_key

    @staticmethod
    def _empty_table_row(team: str) -> dict[str, Any]:
        return {
            "team": team,
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
        }

    @staticmethod
    def _empty_team_record(team: str) -> dict[str, Any]:
        return {
            "team": team,
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
        }

    @staticmethod
    def _filters_dict(**filters: Any) -> dict[str, Any]:
        return {
            key: (value.isoformat() if isinstance(value, date) else value)
            for key, value in filters.items()
            if value not in (None, "", "any")
        }

    @staticmethod
    def _display_team_name(team_key: str, records: Iterable[MatchRecord]) -> str | None:
        for record in records:
            if record.home_team_key == team_key:
                return record.home_team
            if record.away_team_key == team_key:
                return record.away_team
        return None

    @staticmethod
    def _is_likely_complete_brasileirao(
        records: Sequence[MatchRecord], competition: str
    ) -> bool:
        # A modern double round-robin Brasileirão season contains 380 matches.
        # The 300 threshold avoids asserting relegation from a visibly partial set,
        # while still permits historical data with sparse optional records.
        return normalize_competition(competition) == "brasileirao" and len(records) >= 300

    @staticmethod
    def _format_matches(
        matches: Sequence[MatchRecord], *, total: int, filters: Mapping[str, Any]
    ) -> str:
        if not matches:
            return "No matching dataset rows found."
        lines = []
        for match in matches:
            score = (
                f"{match.home_goals}-{match.away_goals}"
                if match.is_complete
                else "score unavailable"
            )
            context = ", ".join(
                value
                for value in (match.competition, match.stage, f"Round {match.round}" if match.round else None)
                if value
            )
            lines.append(
                f"{match.match_date.isoformat() if match.match_date else 'date unavailable'}: "
                f"{match.home_team} {score} {match.away_team} ({context}; {match.source_file})"
            )
        scope = ", ".join(f"{key}={value}" for key, value in filters.items()) or "all loaded data"
        suffix = f" Showing {len(matches)} of {total} matching rows." if total > len(matches) else ""
        return f"Matches for {scope}:\n" + "\n".join(f"- {line}" for line in lines) + suffix

    @staticmethod
    def _format_team_statistics(result: Mapping[str, Any]) -> str:
        return (
            f"{result['team']} record: {result['matches']} matches, {result['wins']} wins, "
            f"{result['draws']} draws, {result['losses']} losses; {result['goals_for']} goals for, "
            f"{result['goals_against']} against; win rate {result['win_rate']}%."
        )

    @staticmethod
    def _format_head_to_head(result: Mapping[str, Any]) -> str:
        h2h = result["head_to_head"]
        rivalry = f" ({result['rivalry']})" if result.get("rivalry") else ""
        return (
            f"{result['team_a']} vs {result['team_b']}{rivalry}: "
            f"{h2h['team_a_wins']} wins for {result['team_a']}, "
            f"{h2h['team_b_wins']} for {result['team_b']}, {h2h['draws']} draws "
            f"across {result['total_matches']} dataset matches."
        )

    @staticmethod
    def _format_players(
        players: Sequence[PlayerRecord], *, total: int, filters: Mapping[str, Any]
    ) -> str:
        if not players:
            return "No matching FIFA player records found."
        scope = ", ".join(f"{key}={value}" for key, value in filters.items()) or "all players"
        entries = "; ".join(
            f"{player.name} (Overall {player.overall if player.overall is not None else 'N/A'}, {player.position}, {player.club})"
            for player in players
        )
        suffix = f" Showing {len(players)} of {total}." if total > len(players) else ""
        return f"FIFA player search for {scope}: {entries}.{suffix} Club data is a FIFA snapshot."

    @staticmethod
    def _format_standings(result: Mapping[str, Any]) -> str:
        standings = result["standings"]
        if not standings:
            return f"No loaded {result['competition']} matches for {result['season']}."
        rows = "; ".join(
            f"{row['position']}. {row['team']} — {row['points']} pts ({row['wins']}W {row['draws']}D {row['losses']}L)"
            for row in standings
        )
        note = f" {result['coverage_note']}" if result.get("coverage_note") else ""
        return f"Calculated {result['competition']} {result['season']} standings: {rows}.{note}"

    @staticmethod
    def _format_competition_statistics(result: Mapping[str, Any]) -> str:
        return (
            f"Dataset statistics: {result['complete_match_count']} complete matches, "
            f"{result['total_goals']} goals, {result['average_goals_per_match']} goals per match; "
            f"home win rate {result['home_win_rate']}%, away win rate {result['away_win_rate']}%."
        )

    @staticmethod
    def _format_best_records(rows: Sequence[Mapping[str, Any]], venue: str) -> str:
        if not rows:
            return "No complete match records found for the selected scope."
        return f"Best {venue} record by points per match: " + "; ".join(
            f"{row['team']} ({row['points_per_match']} PPM, {row['win_rate']}% wins)" for row in rows
        )

    @staticmethod
    def _answer(intent: str, data: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "intent": intent,
            "answer": data.get("formatted_answer", "Query completed."),
            "data": dict(data),
        }

    @staticmethod
    def _clarification(answer: str) -> dict[str, Any]:
        return {"intent": "clarification", "answer": answer, "data": {}}

    @staticmethod
    def _answer_from_context(previous: Mapping[str, Any]) -> dict[str, Any]:
        home = previous.get("home_team")
        away = previous.get("away_team")
        home_goals = previous.get("home_goals")
        away_goals = previous.get("away_goals")
        if home is None or away is None or home_goals is None or away_goals is None:
            return SoccerQueryService._clarification(
                "The supplied last_match context does not contain both teams and a score."
            )
        return {
            "intent": "contextual_score",
            "answer": f"{home} {home_goals}-{away_goals} {away}.",
            "data": {"last_match": dict(previous)},
        }


def _percentage(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


def _first_year(text: str) -> int | None:
    years = _all_years(text)
    return years[0] if years else None


def _all_years(text: str) -> list[int]:
    return [int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", text)]


def _after_phrase(text: str, pattern: str) -> str | None:
    match = re.search(pattern, clean_text(text).rstrip(".?!"), flags=re.IGNORECASE)
    return clean_text(match.group(1).rstrip(".?!")) if match else None


def _extract_pair_after(text: str, pattern: str) -> tuple[str, str] | None:
    match = re.search(pattern, clean_text(text).rstrip(".?!"), flags=re.IGNORECASE)
    if not match:
        return None
    first, second = (clean_text(value.rstrip(".?!")) for value in match.groups())
    second = re.sub(r"\s+(?:head[\s-]*to[\s-]*head|matches|results)$", "", second, flags=re.IGNORECASE)
    return (first, second) if first and second else None


def _extract_vs_pair(text: str) -> tuple[str, str] | None:
    match = re.search(
        r"(.+?)\s+(?:vs\.?|versus)\s+(.+?)\??$",
        clean_text(text).rstrip(".?!"),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    first = _strip_team_prompt(match.group(1))
    second = re.sub(
        r"\s+(?:matches|results|games)$", "", clean_text(match.group(2).rstrip(".?!")), flags=re.IGNORECASE
    )
    return (first, second) if first and second else None


def _strip_team_prompt(value: str) -> str:
    return re.sub(
        r"^(?:(?:show|find|list)(?:\s+me)?(?:\s+all)?\s+|all\s+)",
        "",
        clean_text(value),
        flags=re.IGNORECASE,
    )


def _extract_record_team(text: str) -> str | None:
    match = re.search(
        r"(?:what\s+is\s+)?(.+?)(?:'s|’s)?\s+(?:home|away)\s+record(?:\s+in\s+\d{4})?\??$",
        clean_text(text).rstrip(".?!"),
        flags=re.IGNORECASE,
    )
    return clean_text(match.group(1)) if match else None
