"""Small deterministic natural-language router for common soccer questions."""

from __future__ import annotations

import re
from typing import Any

from soccer_graph import SoccerGraph, normalize_text


COMPETITION_PHRASES = {
    "copa do brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "brasileirao": "Brasileirão",
    "serie a": "Brasileirão",
}

POSITION_WORDS = {
    "forward": ("ST", "CF", "LF", "RF", "LW", "RW"),
    "forwards": ("ST", "CF", "LF", "RF", "LW", "RW"),
    "goalkeeper": ("GK",), "goalkeepers": ("GK",),
    "defender": ("CB", "LB", "RB", "LWB", "RWB"),
    "defenders": ("CB", "LB", "RB", "LWB", "RWB"),
    "midfielder": ("CM", "CDM", "CAM", "LM", "RM"),
    "midfielders": ("CM", "CDM", "CAM", "LM", "RM"),
}


class QueryEngine:
    """Maps frequent natural-language intents to graph operations without an LLM."""

    def __init__(self, graph: SoccerGraph) -> None:
        self.graph = graph

    @staticmethod
    def _year(question: str) -> int | None:
        found = re.search(r"\b(19\d{2}|20\d{2})\b", question)
        return int(found.group(1)) if found else None

    @staticmethod
    def _competition(key: str) -> str | None:
        return next((value for phrase, value in COMPETITION_PHRASES.items() if phrase in key), None)

    def _mentioned_teams(self, key: str) -> list[str]:
        found = []
        for team_key in self.graph._matches_by_team:  # index keys are the graph vocabulary
            if len(team_key) >= 4 and re.search(rf"\b{re.escape(team_key)}\b", key):
                found.append(team_key)
        # Longest matches suppress nested names such as "america" in "america mineiro".
        found.sort(key=len, reverse=True)
        result = []
        for item in found:
            if not any(item in existing for existing in result):
                result.append(item)
        return result

    @staticmethod
    def _answer_matches(matches: list[dict[str, Any]], label: str) -> str:
        if not matches:
            return f"No matches found for {label}."
        lines = [f"{label}: {len(matches)} match(es) found."]
        for match in matches[:10]:
            when = match["date"] or "unknown date"
            score = match["score"] or "not played"
            lines.append(
                f"- {when}: {match['home_team']} {score} {match['away_team']} ({match['competition']})"
            )
        if len(matches) > 10:
            lines.append(f"- … and {len(matches) - 10} more")
        return "\n".join(lines)

    def ask(self, question: str, limit: int = 20) -> dict[str, Any]:
        if not question or not question.strip():
            raise ValueError("question must not be empty")
        key = normalize_text(question)
        year, competition = self._year(key), self._competition(key)
        teams = self._mentioned_teams(key)

        if "derb" in key or "rivalr" in key:
            results = self.graph.find_derbies(season=year, competition=competition, limit=limit)
            return {"intent": "derby_search", "answer": self._answer_matches(results, "Derbies"), "data": results}

        if "top scorer" in key:
            return {
                "intent": "unsupported_top_scorers",
                "answer": "The supplied match files contain team scores but no goal-scorer events, so top scorers cannot be inferred reliably.",
                "data": {"available": False, "reason": "no player-level goal events"},
            }

        years = [int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", key)]
        if "compare" in key and len(set(years)) >= 2 and not teams:
            data = [
                self.graph.aggregate_statistics(competition=competition or "Brasileirão", season=value)
                for value in dict.fromkeys(years)
            ]
            return {
                "intent": "season_comparison",
                "answer": "Compared seasons: " + ", ".join(
                    f"{row['season']} ({row['goals_per_match']:.3f} goals/match)" for row in data
                ),
                "data": data,
            }

        if "biggest" in key and any(word in key for word in ("win", "victor", "score")):
            results = self.graph.biggest_wins(competition=competition, season=year, limit=limit)
            return {"intent": "biggest_wins", "answer": self._answer_matches(results, "Biggest wins"), "data": results}

        if any(phrase in key for phrase in ("average goals", "goals per match", "home win rate")):
            data = self.graph.aggregate_statistics(competition=competition, season=year)
            answer = (
                f"{data['matches']} matches, {data['goals_per_match']:.3f} goals per match; "
                f"home win rate {data['home_win_rate']:.1f}%."
            )
            return {"intent": "aggregate_statistics", "answer": answer, "data": data}

        if any(word in key for word in ("standings", "table", "relegated")) or re.search(r"\bwho won\b", key):
            if year is None:
                return {"intent": "standings", "answer": "Please include a season year.", "data": []}
            table = self.graph.standings(year, competition or "Brasileirão", limit=limit)
            champion = table[0]["team"] if table else "Unknown"
            answer = f"{year} {competition or 'Brasileirão'}: {champion} leads the calculated table."
            return {"intent": "standings", "answer": answer, "data": table}

        if any(phrase in key for phrase in ("most goals", "best home record", "best away record")):
            venue = "home" if "home" in key else "away" if "away" in key else "all"
            metric = "goals_for" if "most goals" in key else "win_rate"
            rows = self.graph.rank_teams(
                season=year, competition=competition or "Brasileirão",
                venue=venue, metric=metric, limit=limit,
            )
            leader = rows[0]["team"] if rows else "No team"
            return {
                "intent": "team_ranking",
                "answer": f"{leader} ranks first by {metric.replace('_', ' ')}.",
                "data": rows,
            }

        player_words = ("player", "players", "rated", "rating", "who is", "forward", "goalkeeper", "defender", "midfielder")
        if any(word in key for word in player_words):
            nationality = "Brazil" if "brazilian" in key else None
            club = self.graph.display_team(teams[0]) if teams else None
            name = None
            who = re.search(r"\bwho is (.+?)(?:\?|$)", question, re.I)
            if who:
                name = who.group(1).strip()
            positions = next((codes for word, codes in POSITION_WORDS.items() if word in key), ())
            players = self.graph.search_players(name=name, nationality=nationality, club=club, limit=500)
            if positions:
                players = [p for p in players if p.position in positions]
            players = players[:limit]
            data = [player.to_dict() for player in players]
            answer = f"Found {len(data)} player(s)." + (
                "\n" + "\n".join(f"- {p['name']} — {p['overall']} ({p['position']}, {p['club']})" for p in data[:10])
                if data else ""
            )
            return {"intent": "player_search", "answer": answer, "data": data}

        if len(teams) >= 2 or "head to head" in key:
            if len(teams) < 2:
                return {"intent": "head_to_head", "answer": "Please name two teams.", "data": {}}
            data = self.graph.head_to_head(teams[0], teams[1], competition=competition, season=year, limit=limit)
            answer = (
                f"{data['team1']} vs {data['team2']}: {data['matches']} matches; "
                f"{data['team1']} {data['team1_wins']} wins, {data['team2']} "
                f"{data['team2_wins']} wins, {data['draws']} draws."
            )
            if "last" in key and data["results"]:
                answer = self._answer_matches(data["results"][:1], "Most recent meeting")
            return {"intent": "head_to_head", "answer": answer, "data": data}

        if teams and "competition" in key:
            data = self.graph.team_competitions(teams[0])
            return {
                "intent": "team_competitions",
                "answer": f"{self.graph.display_team(teams[0])} appears in {len(data)} competitions.",
                "data": data,
            }

        if competition and any(word in key for word in ("match", "matches", "final", "results", "schedule", "bracket")):
            matches = self.graph.find_matches(competition=competition, season=year, limit=1000)
            if "final" in key:
                staged = [match for match in matches if normalize_text(match.stage) == "final"]
                if staged:
                    matches = staged
                else:
                    numeric_rounds = [int(match.round) for match in matches if (match.round or "").isdigit()]
                    if numeric_rounds:
                        final_round = max(numeric_rounds)
                        matches = [match for match in matches if match.round == str(final_round)]
            matches = matches[:limit]
            data = [match.to_dict() for match in matches]
            return {
                "intent": "match_search",
                "answer": self._answer_matches(data, competition),
                "data": data,
            }

        if teams and any(word in key for word in ("record", "statistics", "stats", "performance", "best home", "best away")):
            venue = "home" if "home" in key else "away" if "away" in key else "all"
            data = self.graph.team_statistics(teams[0], season=year, competition=competition, venue=venue)
            answer = (
                f"{data['team']} {venue} record: {data['matches']} matches, {data['wins']}W, "
                f"{data['draws']}D, {data['losses']}L; goals {data['goals_for']}-{data['goals_against']}."
            )
            return {"intent": "team_statistics", "answer": answer, "data": data}

        if teams:
            matches = self.graph.find_matches(team=teams[0], season=year, competition=competition, limit=limit)
            data = [match.to_dict() for match in matches]
            return {
                "intent": "match_search",
                "answer": self._answer_matches(data, f"Matches for {self.graph.display_team(teams[0])}"),
                "data": data,
            }

        return {
            "intent": "clarification",
            "answer": "I can search matches, team records, head-to-heads, players, standings, and aggregate statistics. Please name a team, player, competition, or season.",
            "data": {},
        }
