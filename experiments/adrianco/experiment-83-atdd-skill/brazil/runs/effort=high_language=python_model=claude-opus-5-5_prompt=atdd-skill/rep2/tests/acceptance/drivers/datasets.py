"""
Protocol driver (layer 3) for the system's external inputs: the Kaggle datasets.

The datasets are outside the system under test, so - like a stub - this driver
is programmed by the DSL before the system is asked anything. It is a
translator, not a simulation: it takes facts in football language and writes
them in each dataset's own native format (file name, columns, team-name style,
date format, number format), exactly as the real Kaggle files do.

Each test gets its own data directory, which gives functional isolation: one
spec's matches can never leak into another spec's answers.
"""
import csv

FIFA_SKILLS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve", "FKAccuracy",
    "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower",
    "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions", "Positioning", "Vision",
    "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling", "GKKicking",
    "GKPositioning", "GKReflexes",
]
FIFA_COLUMNS = (
    ["", "ID", "Name", "Age", "Photo", "Nationality", "Flag", "Overall", "Potential", "Club", "Club Logo", "Value",
     "Wage", "Special", "Preferred Foot", "International Reputation", "Weak Foot", "Skill Moves", "Work Rate",
     "Body Type", "Real Face", "Position", "Jersey Number", "Joined", "Loaned From", "Contract Valid Until",
     "Height", "Weight"] + FIFA_SKILLS + ["Release Clause"]
)

FILES = {
    "brasileirão": ("Brasileirao_Matches.csv",
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
    "historical brasileirão": ("novo_campeonato_brasileiro.csv",
                               ["ID", "Data", "Ano", "Rodada", "Equipe_mandante", "Equipe_visitante",
                                "Gols_mandante", "Gols_visitante", "Mandante_UF", "Visitante_UF", "Vencedor",
                                "Arena", "OBS"]),
    "fifa players": ("fifa_data.csv", FIFA_COLUMNS),
}

TOURNAMENT_NAMES = {"brasileirão": "Serie A", "série a": "Serie A", "série b": "Serie B", "série c": "Serie C",
                    "copa do brasil": "Copa do Brasil"}
CUP_ROUND_FOR_STAGE = {"round of 16": 5, "quarterfinals": 6, "semifinals": 7, "final": 8}


class DatasetsDriver:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self._rows = {source: [] for source in FILES}

    def record_match(self, source, competition, date, season, round, stage, home, away, home_goals, away_goals,
                     corners=None, shots=None):
        writer = {
            "brasileirão": self._brasileirao_row,
            "copa do brasil": self._copa_row,
            "libertadores": self._libertadores_row,
            "extended statistics": self._extended_row,
            "historical brasileirão": self._historical_row,
        }.get(source.lower())
        assert writer, f"No dataset called {source!r}; known datasets: {', '.join(FILES)}"
        self._rows[source.lower()].append(writer(
            competition=competition, date=date, season=season, round=round, stage=stage, home=home, away=away,
            home_goals=home_goals, away_goals=away_goals, corners=corners, shots=shots))

    def record_player(self, player_id, name, club, nationality, overall, potential, position, age):
        row = {column: "" for column in FIFA_COLUMNS}
        row.update({
            "": len(self._rows["fifa players"]), "ID": player_id, "Name": name, "Age": age,
            "Nationality": nationality, "Overall": overall, "Potential": potential, "Club": club,
            "Value": "€1M", "Wage": "€10K", "Preferred Foot": "Right", "Position": position,
            "Jersey Number": 10, "Height": "5'10", "Weight": "165lbs",
        })
        row.update({skill: overall for skill in FIFA_SKILLS})
        self._rows["fifa players"].append(row)

    def write(self):
        for source, (file_name, columns) in FILES.items():
            encoding = "utf-8-sig" if source == "fifa players" else "utf-8"
            with open(self.data_dir / file_name, "w", newline="", encoding=encoding) as out:
                writer = csv.DictWriter(out, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                writer.writerows(self._rows[source])

    # --- native formats -------------------------------------------------------------------------------------------

    def _brasileirao_row(self, date, season, round, home, away, home_goals, away_goals, **_):
        return {"datetime": f"{date.isoformat()} 16:00:00", "home_team": home, "home_team_state": _state(home),
                "away_team": away, "away_team_state": _state(away), "home_goal": _goals(home_goals),
                "away_goal": _goals(away_goals), "season": season, "round": round or ""}

    def _copa_row(self, date, season, stage, round, home, away, home_goals, away_goals, **_):
        return {"round": CUP_ROUND_FOR_STAGE.get(stage, round or 1), "datetime": f"{date.isoformat()} 21:30:00",
                "home_team": home, "away_team": away, "home_goal": _goals(home_goals),
                "away_goal": _goals(away_goals), "season": season}

    def _libertadores_row(self, date, season, stage, home, away, home_goals, away_goals, **_):
        return {"datetime": f"{date.isoformat()} 21:30:00", "home_team": home, "away_team": away,
                "home_goal": _goals(home_goals), "away_goal": _goals(away_goals), "season": season,
                "stage": stage or ""}

    def _extended_row(self, competition, date, home, away, home_goals, away_goals, corners, shots, **_):
        corners = corners or (5, 4)
        shots = shots or (10, 9)
        difference = (home_goals or 0) - (away_goals or 0)
        outcome = "WON" if difference > 0 else "LOST" if difference < 0 else "DRAW"
        opposite = {"WON": "LOST", "LOST": "WON", "DRAW": "DRAW"}[outcome]
        return {"tournament": TOURNAMENT_NAMES[competition.lower()], "home": home, "away": away,
                "home_goal": _decimal(home_goals), "away_goal": _decimal(away_goals),
                "home_corner": _decimal(corners[0]), "away_corner": _decimal(corners[1]),
                "home_attack": "100.0", "away_attack": "90.0",
                "home_shots": _decimal(shots[0]), "away_shots": _decimal(shots[1]),
                "time": "20:00:00", "date": date.isoformat(), "ht_diff": _decimal(difference),
                "at_diff": _decimal(-difference), "ht_result": outcome, "at_result": opposite,
                "total_corners": _decimal(sum(corners))}

    def _historical_row(self, date, season, round, home, away, home_goals, away_goals, **_):
        number = len(self._rows["historical brasileirão"]) + 1
        winner = ("Mandante" if home_goals > away_goals else "Visitante" if away_goals > home_goals else "Empate")
        return {"ID": f"{season}.{(round or 1):02d}.{number:04d}", "Data": date.strftime("%d/%m/%Y"),
                "Ano": season, "Rodada": round or 1, "Equipe_mandante": home, "Equipe_visitante": away,
                "Gols_mandante": home_goals, "Gols_visitante": away_goals, "Mandante_UF": _state(home),
                "Visitante_UF": _state(away), "Vencedor": winner, "Arena": "Maracanã", "OBS": ""}


def _state(team):
    suffix = team.rsplit("-", 1)[-1].strip() if "-" in team else ""
    return suffix if len(suffix) == 2 and suffix.isupper() else ""


def _goals(goals):
    return "NA" if goals is None else goals


def _decimal(value):
    return "" if value is None else f"{float(value):.1f}"
