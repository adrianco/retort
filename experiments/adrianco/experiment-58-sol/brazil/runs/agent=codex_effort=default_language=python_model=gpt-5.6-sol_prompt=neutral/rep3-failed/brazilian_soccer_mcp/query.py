"""Conservative natural-language routing into deterministic service methods."""

from __future__ import annotations

import re
from typing import Any

from .normalize import fold_text
from .service import SoccerService


class NaturalLanguageQuery:
    """Recognize common demo questions without pretending to be a general LLM."""

    def __init__(self, service: SoccerService) -> None:
        self.service = service
        names: dict[str, str] = {}
        for match in service.repository.matches:
            names[match.home_key] = match.home_team
            names[match.away_key] = match.away_team
        self.team_names = names

    def _teams(self, question: str) -> list[str]:
        folded = " " + re.sub(r"[^a-z0-9]+", " ", fold_text(question)).strip() + " "
        hits = []
        for key in sorted(self.team_names, key=len, reverse=True):
            if len(key) >= 3 and f" {key} " in folded:
                if not any(key in existing or existing in key for existing in hits):
                    hits.append(key)
        return hits

    @staticmethod
    def _years(question: str) -> list[int]:
        return [int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", question)]

    @staticmethod
    def _competition(question: str) -> str | None:
        text = fold_text(question)
        if "libertadores" in text:
            return "Copa Libertadores"
        if "copa do brasil" in text or "brazilian cup" in text:
            return "Copa do Brasil"
        if "brasileirao" in text or "serie a" in text or "brasileiro" in text:
            return "Brasileirão Série A"
        if "serie b" in text:
            return "Serie B"
        if "serie c" in text:
            return "Serie C"
        return None

    @staticmethod
    def _result(answer: str, intent: str, data: Any) -> dict[str, Any]:
        return {"answer": answer, "intent": intent, "data": data}

    def ask(self, question: str, limit: int = 20) -> dict[str, Any]:
        if not question.strip():
            raise ValueError("question cannot be empty")
        text = fold_text(question)
        years = self._years(question)
        season = years[0] if years else None
        competition = self._competition(question)
        teams = self._teams(question)

        if text in {"what was the score", "what was the score?"}:
            return self._result("Please include the teams or date; this server does not guess conversational context.", "clarification", {})

        if "dataset" in text and any(word in text for word in ("status", "loaded", "coverage")):
            data = self.service.dataset_status()
            return self._result(f"Loaded {data['total_matches']} matches and {data['total_players']} players from all six datasets.", "dataset_status", data)

        if "derb" in text or "classico" in text:
            data = self.service.derby_matches(season=season, limit=limit)
            return self._result(f"Found {data['total']} recognized derby matches" + (f" in {season}." if season else "."), "derbies", data)

        if len(years) >= 2 and any(word in text for word in ("compare", "comparison", "versus")):
            data = self.service.compare_seasons(years[0], years[1], competition or "Brasileirão Série A")
            return self._result(f"Compared {years[0]} with {years[1]} using match totals, goals, and home/away outcomes.", "compare_seasons", data)

        if "biggest" in text and any(word in text for word in ("win", "victor", "defeat", "score")):
            data = self.service.biggest_victories(competition=competition, season=season, limit=limit)
            return self._result(f"The largest goal margins among {data['total_considered']} matching games are listed in descending order.", "biggest_victories", data)

        if ("average" in text or "per match" in text) and "goal" in text:
            data = self.service.competition_statistics(competition=competition, season=season)
            return self._result(f"Average goals per match: {data['goals_per_match']} across {data['matches']} matches.", "competition_statistics", data)

        if "best" in text and ("home" in text or "away" in text) and "record" in text:
            side = "home" if "home" in text else "away"
            data = self.service.best_record(side, season=season, competition=competition, limit=limit)
            leader = data["records"][0] if data["records"] else None
            answer = f"Best {side} record: {leader['team']} ({leader['win_rate']}% wins)." if leader else "No team met the minimum match threshold."
            return self._result(answer, "best_record", data)

        if "top scorer" in text:
            return self._result("The match datasets contain team scores but no goal-scorer events, so individual top scorers cannot be inferred safely.", "unavailable_statistic", {"missing_field": "goal scorer"})

        if season and any(phrase in text for phrase in ("most goals", "highest scoring team", "scored the most")):
            data = self.service.standings(season, competition or "Brasileirão Série A", limit=100)
            leaders = sorted(data["standings"], key=lambda row: row["goals_for"], reverse=True)
            leader = leaders[0] if leaders else None
            answer = f"{leader['team']} scored the most with {leader['goals_for']} goals." if leader else "No scored matches were found."
            return self._result(answer, "most_team_goals", {**data, "goals_leader": leader})

        if "player" in text or text.startswith("who is"):
            nationality = "Brazil" if "brazil" in text else None
            position = None
            for word in ("forward", "midfielder", "defender", "goalkeeper"):
                if word in text:
                    position = word
            club = teams[0] if teams else None
            name = None
            if text.startswith("who is"):
                name = re.sub(r"^\s*who is\s+", "", question, flags=re.I).rstrip(" ?.!")
            data = self.service.search_players(name=name, nationality=nationality, club=club, position=position, limit=limit)
            return self._result(f"Found {data['total']} players matching the requested FIFA filters.", "player_search", data)

        if any(phrase in text for phrase in ("who won", "champion", "relegated", "standings", "table")) and season:
            data = self.service.standings(season, competition or "Brasileirão Série A")
            rows = data["standings"]
            if "relegated" in text:
                selected = rows[-4:] if len(rows) >= 4 else rows
                return self._result("Bottom four in the calculated league table: " + ", ".join(str(row["team"]) for row in selected) + ".", "relegation_table", {**data, "relegation_positions": selected})
            champion = rows[0]["team"] if rows else "unknown"
            return self._result(f"Calculated table leader for {season}: {champion}.", "standings", data)

        if "bracket" in text and competition == "Copa Libertadores":
            data = self.service.search_matches(season=season, competition=competition, limit=limit)
            knockout = [match for match in data["matches"] if fold_text(match.get("stage")) != "group stage"]
            return self._result(f"Returned {len(knockout)} knockout matches from the requested page; stages are included for bracket reconstruction.", "competition_bracket", {**data, "matches": knockout})

        if "final" in text and competition:
            data = self.service.competition_finals(competition, season=season, limit=limit)
            return self._result(f"Found {data['total']} matches whose round or stage is marked as a final.", "competition_finals", data)

        if teams and "competition" in text:
            data = self.service.team_competitions(teams[0], season=season)
            return self._result(f"Found {len(data['competitions'])} competitions for {self.team_names.get(teams[0], teams[0])}.", "team_competitions", data)

        if len(teams) >= 2 and any(word in text for word in ("compare", "head", " vs ", "versus", "play")):
            if any(word in text for word in ("last", "latest", "recent")):
                data = self.service.search_matches(team=teams[0], opponent=teams[1], season=season, competition=competition, limit=1)
                return self._result(f"The latest matching game is {data['matches'][0]['date']}." if data["matches"] else "No matching game was found.", "latest_match", data)
            data = self.service.head_to_head(teams[0], teams[1], season=season, competition=competition, limit=limit)
            return self._result(f"Head-to-head: {data['meetings']} meetings, {data['team1_wins']}-{data['team2_wins']} wins, {data['draws']} draws.", "head_to_head", data)

        if teams and any(word in text for word in ("record", "statistic", "performance")):
            side = "home" if "home" in text else "away" if "away" in text else "either"
            data = self.service.team_statistics(teams[0], season=season, competition=competition, side=side)
            return self._result(f"{data['team']}: {data['wins']}W {data['draws']}D {data['losses']}L, {data['goals_for']} scored and {data['goals_against']} conceded.", "team_statistics", data)

        if teams:
            kwargs: dict[str, Any] = {"team": teams[0], "season": season, "competition": competition, "limit": limit}
            if len(teams) > 1:
                kwargs["opponent"] = teams[1]
            data = self.service.search_matches(**kwargs)
            descriptor = "most recent " if any(word in text for word in ("last", "latest", "recent")) else ""
            if descriptor and data["matches"]:
                data = {**data, "matches": data["matches"][:1], "limit": 1, "has_more": data["total"] > 1}
            return self._result(f"Found {data['total']} matches; returning the {descriptor or 'matching '}results.", "match_search", data)

        return self._result(
            "I could not map that question safely. Include a team, player, season, or competition, or call a structured tool such as search_matches, search_players, standings, or team_statistics.",
            "unsupported",
            {"supported_topics": ["matches", "teams", "players", "standings", "derbies", "season comparisons", "aggregate statistics"]},
        )
