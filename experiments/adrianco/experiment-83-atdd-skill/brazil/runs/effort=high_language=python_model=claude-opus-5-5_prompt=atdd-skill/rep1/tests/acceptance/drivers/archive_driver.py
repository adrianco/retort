"""Protocol driver for the system's input: the Kaggle CSV files.

The datasets are outside the system boundary, so this driver plays the part of the data
provider: it writes each spec's matches and players into files with exactly the layout
of the real downloads, in a directory that belongs to that one spec.
"""
import csv
import re
from dataclasses import dataclass

FIFA_COLUMNS = [
    "", "ID", "Name", "Age", "Photo", "Nationality", "Flag", "Overall", "Potential", "Club", "Club Logo",
    "Value", "Wage", "Special", "Preferred Foot", "International Reputation", "Weak Foot", "Skill Moves",
    "Work Rate", "Body Type", "Real Face", "Position", "Jersey Number", "Joined", "Loaned From",
    "Contract Valid Until", "Height", "Weight", "LS", "ST", "RS", "LW", "LF", "CF", "RF", "RW", "LAM", "CAM",
    "RAM", "LM", "LCM", "CM", "RCM", "RM", "LWB", "LDM", "CDM", "RDM", "RWB", "LB", "LCB", "CB", "RCB", "RB",
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve", "FKAccuracy",
    "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower",
    "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions", "Positioning", "Vision",
    "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes", "Release Clause",
]

FILES = {
    "brasileirao": ("Brasileirao_Matches.csv",
                    ["datetime", "home_team", "home_team_state", "away_team", "away_team_state",
                     "home_goal", "away_goal", "season", "round"]),
    "copa do brasil": ("Brazilian_Cup_Matches.csv",
                       ["round", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season"]),
    "libertadores": ("Libertadores_Matches.csv",
                     ["datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "stage"]),
    "extended statistics": ("BR-Football-Dataset.csv",
                            ["tournament", "home", "home_goal", "away_goal", "away", "home_corner", "away_corner",
                             "home_attack", "away_attack", "home_shots", "away_shots", "time", "date", "ht_diff",
                             "at_diff", "ht_result", "at_result", "total_corners"]),
    "historical brasileirao": ("novo_campeonato_brasileiro.csv",
                               ["ID", "Data", "Ano", "Rodada", "Equipe_mandante", "Equipe_visitante",
                                "Gols_mandante", "Gols_visitante", "Mandante_UF", "Visitante_UF", "Vencedor",
                                "Arena", "OBS"]),
    "players": ("fifa_data.csv", FIFA_COLUMNS),
}

EXTENDED_TOURNAMENT = {"Brasileirão": "Serie A", "Série B": "Serie B", "Série C": "Serie C",
                       "Copa do Brasil": "Copa do Brasil"}

STATE_SUFFIX = re.compile(r"\s*-\s*([A-Z]{2})$")


@dataclass
class ArchivedMatch:
    source: str
    competition: str
    date: str
    season: int
    home: str
    away: str
    home_goals: int
    away_goals: int
    league_round: int
    cup_round: int
    stage: str
    corners: tuple = None
    shots: tuple = None


@dataclass
class ArchivedPlayer:
    name: str
    nationality: str
    club: str
    position: str
    overall: int
    potential: int
    age: int
    jersey_number: int


def _state(team):
    found = STATE_SUFFIX.search(team)
    return found.group(1) if found else ""


def _outcome(goal_difference):
    return "WON" if goal_difference > 0 else "LOST" if goal_difference < 0 else "DRAW"


class ArchiveDriver:
    def __init__(self, directory):
        self.directory = directory
        self._rows = {source: [] for source in FILES}

    def record_match(self, match):
        if match.source not in FILES or match.source == "players":
            raise AssertionError(f"There is no match dataset called '{match.source}'")
        self._rows[match.source].append(getattr(self, "_" + match.source.replace(" ", "_"))(match))

    def record_player(self, player):
        row = {column: "" for column in FIFA_COLUMNS}
        number = len(self._rows["players"])
        row.update({"": number, "ID": 100000 + number, "Name": player.name, "Age": player.age,
                    "Nationality": player.nationality, "Overall": player.overall,
                    "Potential": player.potential, "Club": player.club, "Value": "€1M", "Wage": "€10K",
                    "Preferred Foot": "Right", "Position": player.position,
                    "Jersey Number": player.jersey_number, "Height": "5'11", "Weight": "165lbs",
                    "Finishing": 60, "Dribbling": 60, "ShortPassing": 60})
        self._rows["players"].append(row)

    def publish(self):
        """Write every dataset, empty or not, as the real download would contain them all."""
        for source, (file_name, columns) in FILES.items():
            with open(self.directory / file_name, "w", newline="", encoding="utf-8") as out:
                writer = csv.DictWriter(out, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                writer.writerows(self._rows[source])

    @staticmethod
    def _brasileirao(match):
        return {"datetime": f"{match.date} 16:00:00", "home_team": match.home, "home_team_state": _state(match.home),
                "away_team": match.away, "away_team_state": _state(match.away), "home_goal": match.home_goals,
                "away_goal": match.away_goals, "season": match.season, "round": match.league_round}

    @staticmethod
    def _copa_do_brasil(match):
        return {"round": match.cup_round, "datetime": f"{match.date} 20:30:00", "home_team": match.home,
                "away_team": match.away, "home_goal": match.home_goals, "away_goal": match.away_goals,
                "season": match.season}

    @staticmethod
    def _libertadores(match):
        return {"datetime": f"{match.date} 21:30:00", "home_team": match.home, "away_team": match.away,
                "home_goal": match.home_goals, "away_goal": match.away_goals, "season": match.season,
                "stage": match.stage}

    @staticmethod
    def _extended_statistics(match):
        corners = match.corners or ("", "")
        shots = match.shots or ("", "")
        difference = match.home_goals - match.away_goals
        return {"tournament": EXTENDED_TOURNAMENT[match.competition], "home": match.home,
                "home_goal": f"{match.home_goals:.1f}", "away_goal": f"{match.away_goals:.1f}", "away": match.away,
                "home_corner": corners[0], "away_corner": corners[1], "home_attack": "", "away_attack": "",
                "home_shots": shots[0], "away_shots": shots[1], "time": "19:00:00", "date": match.date,
                "ht_diff": float(difference), "at_diff": float(-difference),
                "ht_result": _outcome(difference), "at_result": _outcome(-difference),
                "total_corners": float(sum(match.corners)) if match.corners else ""}

    @staticmethod
    def _historical_brasileirao(match):
        year, month, day = match.date.split("-")
        winner = ("Mandante" if match.home_goals > match.away_goals
                  else "Visitante" if match.home_goals < match.away_goals else "Empate")
        return {"ID": f"{match.season}.{match.league_round:02d}.0001", "Data": f"{day}/{month}/{year}",
                "Ano": match.season, "Rodada": match.league_round, "Equipe_mandante": match.home,
                "Equipe_visitante": match.away, "Gols_mandante": match.home_goals,
                "Gols_visitante": match.away_goals, "Mandante_UF": _state(match.home),
                "Visitante_UF": _state(match.away), "Vencedor": winner, "Arena": "Estádio", "OBS": ""}
